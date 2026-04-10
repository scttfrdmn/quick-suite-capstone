# Router: Analyze

Use the Router's `analyze` tool to get a governed LLM analysis of data,
text, or a problem — routed to the best available model.

## Scenario

You're reviewing a dataset's summary statistics and want an LLM to
interpret the patterns before you write your analysis code.

## Tool call

```
analyze

prompt: "I have a dataset of 12,000 first-year students with the
following summary statistics: mean GPA 2.74 (SD 0.82), mean credits
attempted 14.2 (SD 3.1), Pell recipient rate 42%, first-generation
rate 38%, retention rate 71%. The correlation between first-semester
GPA and retention is 0.64. What patterns should I investigate first,
and what confounders should I control for?"

tool: analyze
```

## What happens

1. Router selects the best available model based on your routing config
   (e.g., Claude on Bedrock first, GPT-4o fallback)
2. Bedrock Guardrails scan the prompt
3. Model generates analysis
4. Guardrails scan the response
5. Spend ledger records the cost against your department

## Response includes

- `content` — the analysis text
- `provider` — which model answered (e.g., `bedrock/anthropic.claude-sonnet-4-20250514-v1:0`)
- `tokens_in_estimate` — token count for budgeting
- `fallback_used` — whether the primary provider was unavailable

## How this fits your workflow

You're writing an analysis script. Before choosing which compute profile
to run or which columns to include, you ask the Router to interpret the
summary stats. The response tells you that GPA-retention correlation
is strong but Pell and first-gen status are likely confounders — so you
add those as controls in your regression model.

```python
# Based on Router analysis: control for Pell + first-gen
result = compute_run(
    profile_id="regression-logistic",
    source_uri="claws://s3-first-year-cohort-2025",
    parameters={
        "target": "retained",
        "features": ["gpa_first_semester", "credits_attempted",
                     "pell_recipient", "first_generation"],
    }
)
```
