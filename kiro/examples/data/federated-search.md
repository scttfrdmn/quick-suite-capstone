# Data: Federated Search

Use `federated_search` to search across all registered source types at
once — RODA, institutional S3, Snowflake, Redshift, IPEDS, NIH Reporter,
NSF Awards, PubMed, bioRxiv, Semantic Scholar, arXiv, Zenodo, Figshare,
and reagent catalogs.

## Scenario

You're starting a new analysis and aren't sure where the relevant data
lives — it could be a public dataset, an institutional table, or a
research database.

## Tool call

```
federated_search

query: "student financial aid Pell grant retention"
max_results: 10
```

## Response includes

```json
{
  "results": [
    {"source_type": "roda", "title": "IPEDS Student Financial Aid", "slug": "ipeds-sfa", "quality_score": 0.88},
    {"source_type": "s3", "label": "financial-aid", "path": "s3://qs-institutional-data/financial-aid/", "quality_score": 0.95},
    {"source_type": "ipeds", "series_slug": "college-university/ipeds/sfa", "year_range": "2000-2023", "quality_score": 0.90},
    {"source_type": "pubmed", "title": "Pell Grant Effects on Persistence: A Regression Discontinuity Design", "pmid": "38921456", "quality_score": 0.85}
  ],
  "skipped_sources": ["reagents"]
}
```

## How this fits your workflow

You get results from four different source types in one call. Now you
know:
- IPEDS has the public benchmark data (use `ipeds_search` for details)
- Your institution has its own financial aid records in S3 (use
  `s3_preview` to inspect)
- There's a relevant RDD paper on PubMed (use `extract` to pull effect
  sizes for your power analysis)

Instead of searching four different systems, you searched once and can
now write targeted follow-up queries.

## Filtering by classification

For sensitive data environments, filter by data classification:

```
federated_search

query: "student retention demographics"
data_classification_filter: "public"
```

This restricts results to publicly available sources only — useful when
you want to find comparison data without touching institutional records.
