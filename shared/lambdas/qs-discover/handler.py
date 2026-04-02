"""
qs-discover — unified discovery Lambda.

Fans out to all three Quick Suite discovery surfaces in parallel,
merges results, deduplicates by ID, and returns a ranked list.

Input:
  {
    "query": str,          # search terms
    "limit": int           # max results to return (default 20, max 50)
  }

Output:
  {
    "count": int,
    "query": str,
    "sources": [
      {
        "source_type": "roda" | "s3" | "claws",
        "id": str,
        "name": str,
        "description": str,
        "score": float,
        "load_tool": str,   # tool name to load this source
        "probe_tool": str,  # tool name to preview/probe this source
        "metadata": dict
      },
      ...
    ]
  }

Target Lambda ARNs are read from SSM at module load time (cached).
"""

import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

lambda_client = boto3.client("lambda")
ssm_client = boto3.client("ssm")

# SSM paths written by sub-project stacks at deploy time
_SSM_RODA_SEARCH = "/quick-suite/lambdas/roda-search-arn"
_SSM_S3_BROWSE = "/quick-suite/lambdas/s3-browse-arn"
_SSM_CLAWS_DISCOVER = "/quick-suite/lambdas/claws-discover-arn"

# Module-level cache: resolved at first invocation, never re-fetched
_arns: dict = {}


def _get_arns() -> dict:
    global _arns
    if _arns:
        return _arns

    resolved = {}
    for key, path in [
        ("roda_search", _SSM_RODA_SEARCH),
        ("s3_browse", _SSM_S3_BROWSE),
        ("claws_discover", _SSM_CLAWS_DISCOVER),
    ]:
        try:
            resp = ssm_client.get_parameter(Name=path)
            resolved[key] = resp["Parameter"]["Value"]
        except Exception as e:
            logger.warning(json.dumps({"ssm_miss": path, "error": str(e)}))

    _arns = resolved
    return resolved


# ---------------------------------------------------------------------------
# Per-source invoke helpers
# ---------------------------------------------------------------------------

def _invoke(arn: str, payload: dict) -> dict:
    """Invoke a Lambda and return its parsed response dict."""
    resp = lambda_client.invoke(
        FunctionName=arn,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload),
    )
    return json.loads(resp["Payload"].read())


def _invoke_roda_search(query: str, limit: int) -> list:
    arns = _get_arns()
    arn = arns.get("roda_search")
    if not arn:
        return []
    result = _invoke(arn, {"query": query, "limit": limit})
    datasets = result.get("datasets", [])
    normalized = []
    for ds in datasets:
        normalized.append({
            "source_type": "roda",
            "id": f"roda-{ds.get('slug', '')}",
            "name": ds.get("name", ""),
            "description": ds.get("description", ""),
            "score": float(ds.get("score", 0)),
            "load_tool": "roda_load",
            "probe_tool": "roda_search",
            "metadata": {
                "slug": ds.get("slug"),
                "tags": ds.get("tags", []),
                "formats": ds.get("formats", []),
                "managed_by": ds.get("managedBy", ""),
            },
        })
    return normalized


def _invoke_s3_browse(query: str) -> list:
    arns = _get_arns()
    arn = arns.get("s3_browse")
    if not arn:
        return []
    result = _invoke(arn, {"query": query})
    entries = result.get("entries", [])
    normalized = []
    for entry in entries:
        path = entry.get("path", "")
        entry_id = f"s3-{path.replace('/', '-').replace(':', '-')}"
        normalized.append({
            "source_type": "s3",
            "id": entry_id,
            "name": entry.get("label", path),
            "description": entry.get("description", f"S3 path: {path}"),
            "score": 0.5,  # s3_browse doesn't return relevance scores
            "load_tool": "s3_load",
            "probe_tool": "s3_preview",
            "metadata": {
                "path": path,
                "source_label": entry.get("source_label", ""),
                "size_bytes": entry.get("size_bytes"),
                "last_modified": entry.get("last_modified"),
            },
        })
    return normalized


def _invoke_claws_discover(query: str, limit: int) -> list:
    arns = _get_arns()
    arn = arns.get("claws_discover")
    if not arn:
        return []
    result = _invoke(arn, {"query": query, "limit": limit})
    items = result.get("items", [])
    normalized = []
    for item in items:
        normalized.append({
            "source_type": "claws",
            "id": item.get("source_id", ""),
            "name": item.get("name", ""),
            "description": item.get("description", ""),
            "score": float(item.get("score", 0)),
            "load_tool": item.get("load_tool", ""),
            "probe_tool": item.get("probe_tool", ""),
            "metadata": item.get("metadata", {}),
        })
    return normalized


# ---------------------------------------------------------------------------
# Ranking and deduplication
# ---------------------------------------------------------------------------

def _score_item(item: dict, query: str) -> float:
    """Score an item by term overlap with query (name weighted 3×)."""
    terms = set(query.lower().split())
    if not terms:
        return item.get("score", 0.0)

    name_terms = set(item.get("name", "").lower().split())
    desc_terms = set(item.get("description", "").lower().split())

    name_hits = len(terms & name_terms)
    desc_hits = len(terms & desc_terms)

    base_score = (name_hits * 3 + desc_hits) / (len(terms) * 4)
    return base_score + item.get("score", 0.0) * 0.1


def _rank_and_dedupe(items: list, query: str) -> list:
    """Score, deduplicate by id, and sort descending."""
    seen = {}
    for item in items:
        item_id = item.get("id", "")
        score = _score_item(item, query)
        item["score"] = score
        if item_id not in seen or score > seen[item_id]["score"]:
            seen[item_id] = item

    return sorted(seen.values(), key=lambda x: x["score"], reverse=True)


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

def handler(event: dict, context) -> dict:
    query = str(event.get("query", "")).strip()
    limit = min(int(event.get("limit", 20)), 50)

    logger.info(json.dumps({"query": query, "limit": limit}))

    results = []
    errors = {}

    tasks = {
        "roda": lambda: _invoke_roda_search(query, limit),
        "s3": lambda: _invoke_s3_browse(query),
        "claws": lambda: _invoke_claws_discover(query, limit),
    }

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(fn): source for source, fn in tasks.items()}
        for future in as_completed(futures):
            source = futures[future]
            try:
                items = future.result(timeout=10)
                results.extend(items)
                logger.info(json.dumps({"source": source, "count": len(items)}))
            except Exception as e:
                errors[source] = str(e)
                logger.warning(json.dumps({"source": source, "error": str(e)}))

    ranked = _rank_and_dedupe(results, query)[:limit]

    response = {"count": len(ranked), "query": query, "sources": ranked}
    if errors:
        response["errors"] = errors

    return response
