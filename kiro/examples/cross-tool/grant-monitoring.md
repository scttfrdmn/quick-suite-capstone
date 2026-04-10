# Cross-Tool: Grant Monitoring Pipeline

A research office sets up continuous monitoring for grant activity —
portfolio health, new awards in the field, and compliance — then
automates the response.

## The question

"Monitor our active grants for burn rate risk, watch for new NIH awards
in our research areas, and alert compliance when any study's conditions
change."

## Part 1: Grant Portfolio Health (clAWS + Compute)

### Discover and query spending data

```
discover

query: "sponsored program expenditure awards"
scope:
  domains: ["institutional"]
```

```
plan

source_id: "glue://finance_db/sponsored_program_expenditures"
objective: "All active awards with cumulative and monthly expenditures,
PI name, award amount, start and end dates"
```

```
excavate

plan_id: "plan-grant-portfolio"
source_id: "glue://finance_db/sponsored_program_expenditures"
query: "<generated SQL>"
query_type: "athena_sql"
```

### Run portfolio analysis

```
compute_run

profile_id: "grant-portfolio"
source_uri: "s3://qs-compute-inputs/grant-portfolio/data.parquet"
parameters:
  award_id: "award_number"
  pi: "pi_name"
  amount: "award_amount"
  spent: "cumulative_expenditure"
  start_date: "award_start"
  end_date: "award_end"
result_label: "grant-portfolio-2026-q2"
```

Returns: per-award burn rates, NCE risk flags (awards ending within
60 days with no overlap), PI health scores.

### Run anomaly detection on spending

```
compute_run

profile_id: "anomaly-isolation-forest"
source_uri: "s3://qs-compute-inputs/grant-portfolio/data.parquet"
parameters:
  features: ["monthly_spend_rate", "burn_rate_pct", "months_remaining"]
  contamination: 0.05
result_label: "grant-anomalies-2026-q2"
```

Returns: flagged awards with unusual spending patterns.

### Remember the findings

```
remember

record:
  type: "grant_risk"
  severity: "high"
  finding: "3 awards flagged for NCE risk: NIH-R01-2023-045 (PI: Chen, 42 days remaining, 67% spent), NSF-2022-103 (PI: Williams, 58 days, 45% spent), DOE-2024-011 (PI: Park, 31 days, 88% spent)"
  tags: ["grants", "nce-risk", "portfolio", "q2-2026"]
```

## Part 2: New Award Monitoring (clAWS Watch)

### Set up watches for each research area

```
watch

plan_id: "plan-nih-genomics"
schedule: "rate(7 days)"
watch_type: "new_award"
semantic_match:
  lab_profile_ssm_key: "/quick-suite/research/genomics-profile"
  abstract_similarity_threshold: 0.80
action_routing:
  destination_type: "sns"
  destination_arn: "arn:aws:sns:us-east-1:123456789012:research-office-alerts"
  context_template: "New {source_type} award in genomics: {title} (PI: {pi_name} at {institution}, ${award_amount}). Match score: {similarity_score}."
```

Repeat for other research areas (materials science, public health, etc.).

### What happens weekly

1. Watch runner queries NIH Reporter for new awards
2. Each abstract is scored against your research profile
3. High-similarity awards trigger SNS notifications
4. Findings auto-remember for future reference

## Part 3: Compliance Monitoring (clAWS Watch)

### Set up compliance watch

```
watch

plan_id: "plan-study-conditions"
schedule: "rate(1 day)"
watch_type: "compliance"
compliance_mode: true
compliance_ruleset_uri: "s3://qs-claws-config/compliance-rules.json"
action_routing:
  destination_type: "sns"
  destination_arn: "arn:aws:sns:us-east-1:123456789012:irb-compliance-alerts"
  context_template: "Compliance alert: {rule_type} triggered for study {study_id}. {draft_text}"
```

The ruleset defines four rule types:
- `international_site` — new international collaborator added
- `new_data_source` — study accessing a data source not in the original protocol
- `subject_count` — enrolled subjects exceeding approved count
- `classification_change` — data sensitivity classification changed

### What happens daily

1. Watch runner evaluates each rule against current data
2. Violations trigger SNS alerts to the compliance inbox
3. Router `summarize` drafts amendment language for each gap
4. Findings remember with `severity: "critical"`

## Part 4: Recall and Report

A month later, compile everything for the quarterly research report:

```
recall

tags: ["grants", "nce-risk"]
since_days: 90
```

```
recall

tags: ["new_award"]
since_days: 90
```

```
recall

tags: ["compliance"]
since_days: 90
severity: "critical"
```

### Synthesize the report

```
research

prompt: "Based on these findings, write a 500-word quarterly research
office report covering: (1) portfolio health and NCE risks,
(2) new awards in our research areas and strategic implications,
(3) compliance alerts and actions taken. Include specific numbers."

grounding_mode: "strict"
```

## What you've built

A continuous monitoring pipeline that:
- Runs portfolio analysis quarterly (manual via Kiro)
- Watches for new awards weekly (automated via watch)
- Monitors compliance daily (automated via watch)
- Accumulates findings in institutional memory
- Produces quarterly reports from recalled findings

All governed by Cedar policies, scanned by Guardrails, and auditable
end to end. The research office goes from reactive ("someone told me
about this grant") to proactive ("the system surfaced it three weeks
ago").
