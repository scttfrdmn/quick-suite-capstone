# Compute: Literature-Informed Power Analysis

Use `compute_run` with the `power-analysis` profile to calculate sample
sizes using effect sizes extracted from published literature.

## Scenario

You're designing an RCT for a new mentoring intervention and need to
determine sample size. Rather than guessing at an effect size, you
want to base it on what similar studies have found.

## Tool calls

This is a multi-tool workflow. Start by finding relevant studies:

```
pubmed_search

query: "peer mentoring first-generation college student retention RCT"
max_results: 5
year_start: 2020
```

Extract effect sizes from the top results:

```
extract

prompt: "<abstract text from top result>"
extraction_types: ["effect_sizes"]
```

Returns: `Cohen's d = 0.28` from one study, `OR = 1.35` from another.

Now run the power analysis with literature cross-referencing:

```
compute_run

profile_id: "power-analysis"
parameters:
  effect_size: 0.28
  alpha: 0.05
  power: 0.80
  test_type: "two_sample_t"
  pubmed_ids: ["38921456", "39102345", "38876543"]
```

## Response

```json
{
  "status": "SUCCEEDED",
  "summary": {
    "metadata": {
      "required_n_per_group": 202,
      "required_n_total": 404,
      "literature_effect_sizes": [
        {"pmid": "38921456", "measure": "Cohen's d", "value": 0.28},
        {"pmid": "39102345", "measure": "Cohen's d", "value": 0.34},
        {"pmid": "38876543", "measure": "OR", "value": 1.35, "converted_d": 0.19}
      ],
      "power_curve": [
        {"n": 50, "power": 0.28},
        {"n": 100, "power": 0.52},
        {"n": 150, "power": 0.71},
        {"n": 200, "power": 0.83},
        {"n": 250, "power": 0.90}
      ],
      "confound_checklist": [
        "Prior GPA (controlled in 2/3 studies)",
        "Financial need / Pell status (controlled in 1/3 studies)",
        "First-generation status (selection criterion, not covariate)",
        "Mentor training intensity (varied across studies)"
      ]
    }
  }
}
```

## How this fits your workflow

You're writing an IRB protocol in Kiro. The power analysis gives you:

1. **A defensible sample size** (n=404 total) based on literature, not
   a guess
2. **A power curve** showing the sensitivity tradeoff if you can only
   recruit fewer participants
3. **A confound checklist** drawn from the methods sections of the cited
   papers — reminding you what to control for in your design

```markdown
## Sample Size Justification

Based on a meta-analytic review of three RCTs examining peer mentoring
interventions for first-generation students (PMIDs: 38921456, 39102345,
38876543), the median reported effect size is Cohen's d = 0.28. A
two-sample t-test with alpha = 0.05 and power = 0.80 requires 202
participants per arm (N = 404 total). We will control for prior GPA,
Pell status, and mentor training intensity based on the confound
profiles of the cited studies.
```

## When the Router is unavailable

If the Router can't reach the PubMed papers (network issue, API down),
`power-analysis` falls back to using the manually specified
`effect_size` without literature cross-referencing. You still get the
power curve and sample size — just without the PubMed-informed confound
checklist.
