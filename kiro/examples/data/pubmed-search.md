# Data: Search PubMed

Use `pubmed_search` to search the PubMed biomedical literature database
via NCBI E-utilities — directly from Kiro while writing your analysis
code or grant narrative.

## Scenario

You're writing the literature review section of a grant application and
need to find recent papers on CRISPR delivery mechanisms.

## Tool call

```
pubmed_search

query: "CRISPR delivery lipid nanoparticle in vivo"
max_results: 10
year_start: 2023
```

## Response includes

```json
{
  "count": 10,
  "results": [
    {
      "pmid": "39102345",
      "title": "Ionizable lipid nanoparticles for tissue-selective CRISPR-Cas9 delivery",
      "authors": ["Chen Y", "Martinez A", "Park S"],
      "journal": "Nature Biotechnology",
      "pub_date": "2025-08",
      "quality_score": 0.94
    },
    {
      "pmid": "38876543",
      "title": "Biodegradable polymer-lipid hybrid nanoparticles for lung-targeted gene editing",
      "authors": ["Williams R", "Zhang L"],
      "journal": "ACS Nano",
      "pub_date": "2025-03",
      "quality_score": 0.91
    }
  ]
}
```

## How this fits your workflow

You're drafting in Kiro. Search PubMed without leaving the editor, then
chain into other tools:

**For a grant narrative:** Use Router `extract` to pull methods and effect
sizes from the top results, then Router `research` with
`grounding_mode: "strict"` to synthesize a cited background section.

**For a power analysis:** Extract effect sizes from relevant RCTs, then
feed them into Compute's `power-analysis` profile:

```python
# 1. Search PubMed for relevant RCTs
papers = pubmed_search(query="proactive advising RCT retention", max_results=5)

# 2. Extract effect sizes from abstracts
for paper in papers["results"]:
    effects = extract(
        prompt=paper["abstract"],
        extraction_types=["effect_sizes"]
    )

# 3. Run power analysis with literature-informed effect sizes
result = compute_run(
    profile_id="power-analysis",
    parameters={
        "effect_size": 0.31,  # Cohen's d from literature
        "alpha": 0.05,
        "power": 0.80,
        "pubmed_ids": ["39102345", "38876543"]
    }
)
```

## Other literature tools

PubMed is one of seven literature search tools available:

| Tool | Database | Best for |
|------|----------|----------|
| `pubmed_search` | PubMed / MEDLINE | Biomedical, clinical |
| `biorxiv_search` | bioRxiv / medRxiv | Preprints, cutting-edge |
| `semantic_scholar_search` | Semantic Scholar | Citation-aware search, cross-discipline |
| `arxiv_search` | arXiv | Physics, CS, math, quantitative bio |
| `reagent_search` | Addgene | Plasmids, viral vectors, CRISPR tools |
| `nih_reporter_search` | NIH Reporter | Funded grants, PI lookup |
| `nsf_awards_search` | NSF Awards | NSF-funded research |
