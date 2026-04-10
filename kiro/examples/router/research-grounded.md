# Router: Grounded Research

Use the Router's `research` tool with `grounding_mode: "strict"` to get
answers with source citations, coverage metrics, and flagged
low-confidence claims.

## Scenario

You're writing the background section of a grant proposal and need
verifiable claims about current state-of-the-art, not LLM confabulation.

## Tool call

```
research

prompt: "What is the current evidence on the effectiveness of
proactive advising interventions for improving first-generation
student retention at R1 universities? Focus on randomized or
quasi-experimental studies from 2020-2025."

grounding_mode: "strict"
```

## Response includes

```json
{
  "content": "Several quasi-experimental studies have examined proactive
  advising interventions...",
  "sources_used": [
    "Venit et al. (2021) — Proactive advising RCT at 3 public R1s",
    "Kalamkarian & Karp (2023) — MDRC quasi-experimental evaluation"
  ],
  "grounding_coverage": 0.87,
  "low_confidence_claims": [
    {
      "claim": "Effect sizes range from 0.15 to 0.35 SD",
      "reason": "Aggregated across heterogeneous interventions"
    }
  ]
}
```

## How this fits your workflow

You're drafting in Kiro. The grounded response gives you citable claims
with an explicit coverage score — 87% of statements are grounded in
named sources. The `low_confidence_claims` list tells you exactly which
sentences to double-check before submitting. You paste the content into
your draft and follow up on the flagged claims:

```markdown
## Background

Several quasi-experimental studies have examined proactive advising
interventions... [Venit et al., 2021; Kalamkarian & Karp, 2023]

<!-- TODO: verify effect size range — flagged as low confidence -->
```

## Combining with extract

For the most rigorous grant narratives, chain `research` (grounded) with
`extract` (structured) — get the narrative first, then extract specific
effect sizes from the cited papers for your power analysis:

1. `research` with `grounding_mode: "strict"` — get cited sources
2. `pubmed_search` — find the actual papers
3. `extract` with `extraction_types: ["effect_sizes"]` — pull numbers
4. `compute_run` with `power-analysis` — calculate sample size
