# Router: Extract Structured Data

Use the Router's `extract` tool to pull structured fields from
scientific text — effect sizes, methods, confounds, open problems,
and citations.

## Scenario

You're writing a meta-analysis script and need to extract reported
effect sizes from several papers' abstracts and results sections.

## Tool call

```
extract

prompt: "From the following text, extract all reported effect sizes,
sample sizes, and statistical tests used:

Treatment group showed significant improvement in persistence rates
(OR = 1.43, 95% CI [1.12, 1.82], p = 0.004, n = 847) compared to
control (n = 912). A secondary analysis using propensity score matching
(Cohen's d = 0.31, p = 0.02) confirmed the treatment effect after
controlling for prior GPA and financial need."

extraction_types: ["effect_sizes", "methods_profile"]
```

## Response includes

```json
{
  "extracted_fields": {
    "effect_sizes": [
      {"measure": "OR", "value": 1.43, "ci_lower": 1.12, "ci_upper": 1.82,
       "p_value": 0.004, "n_treatment": 847, "n_control": 912},
      {"measure": "Cohen's d", "value": 0.31, "p_value": 0.02}
    ],
    "methods_profile": {
      "primary": "logistic regression (odds ratio)",
      "secondary": "propensity score matching",
      "covariates": ["prior GPA", "financial need"]
    }
  },
  "provider": "openai/gpt-4o"
}
```

## How this fits your workflow

You're building a forest plot for a meta-analysis. Instead of manually
reading each paper and transcribing effect sizes into a spreadsheet,
you feed abstracts through `extract` and get structured JSON back. Your
script consumes the JSON directly:

```python
import json

# Feed each abstract through Router extract
effects = []
for abstract in abstracts:
    result = extract(prompt=abstract, extraction_types=["effect_sizes"])
    effects.extend(result["extracted_fields"]["effect_sizes"])

# Now you have structured data for your forest plot
df = pd.DataFrame(effects)
```

## Open problems extraction

The `open_problems` extraction type is especially useful for literature
monitoring. It extracts `[{gap_statement, domain, confidence}]` objects
and can optionally persist the gap list to S3 for clAWS's
`cross_discipline` watch to consume:

```
extract

prompt: "<paper text>"
extraction_types: ["open_problems"]
store_at_uri: "s3://my-bucket/gap-lists/crispr-delivery.json"
```
