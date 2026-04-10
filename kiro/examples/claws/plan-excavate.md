# clAWS: Plan and Excavate

Use `plan` to translate a free-text objective into a concrete,
Cedar-validated query, then `excavate` to execute it.

## Scenario

You need specific data from an institutional Athena table for your
analysis, but the table is governed — you can't just run arbitrary SQL.

## Tool calls

### Step 1: Plan

```
plan

source_id: "glue://registrar_db/student_retention_cohorts"
objective: "Count students retained to term 2 vs not retained, grouped
by Pell recipient status and first-generation status, for Fall 2023
and Fall 2024 cohorts only"
```

Response:
```json
{
  "plan_id": "plan-8f2a1b3c",
  "status": "ready",
  "query": "SELECT cohort_term, pell_recipient, first_generation, retained_term_2, COUNT(*) as student_count FROM student_retention_cohorts WHERE cohort_term IN ('202310', '202410') GROUP BY cohort_term, pell_recipient, first_generation, retained_term_2",
  "query_type": "athena_sql",
  "cost_estimate_usd": 0.005,
  "output_schema": [
    {"name": "cohort_term", "type": "string"},
    {"name": "pell_recipient", "type": "boolean"},
    {"name": "first_generation", "type": "boolean"},
    {"name": "retained_term_2", "type": "boolean"},
    {"name": "student_count", "type": "integer"}
  ]
}
```

The plan shows you the exact SQL that will run. Cedar has already
validated that your principal is permitted to query this table with
these columns. The cost estimate tells you this is a $0.005 query.

### Step 2: Excavate

```
excavate

plan_id: "plan-8f2a1b3c"
source_id: "glue://registrar_db/student_retention_cohorts"
query: "SELECT cohort_term, pell_recipient, first_generation, retained_term_2, COUNT(*) as student_count FROM student_retention_cohorts WHERE cohort_term IN ('202310', '202410') GROUP BY cohort_term, pell_recipient, first_generation, retained_term_2"
query_type: "athena_sql"
```

Response:
```json
{
  "run_id": "run-4e5f6a7b",
  "rows": [
    {"cohort_term": "202310", "pell_recipient": true, "first_generation": true, "retained_term_2": true, "student_count": 312},
    {"cohort_term": "202310", "pell_recipient": true, "first_generation": true, "retained_term_2": false, "student_count": 148},
    {"cohort_term": "202310", "pell_recipient": true, "first_generation": false, "retained_term_2": true, "student_count": 587},
    {"cohort_term": "202310", "pell_recipient": false, "first_generation": false, "retained_term_2": true, "student_count": 1423}
  ],
  "row_count": 16,
  "cost_usd": 0.004
}
```

## How this fits your workflow

You now have the exact retention counts in structured JSON. Use them
directly in your analysis code:

```python
import pandas as pd

# From excavation results
rows = excavate_response["rows"]
df = pd.DataFrame(rows)

# Compute retention rates by subgroup
retention = (
    df.groupby(["cohort_term", "pell_recipient", "first_generation"])
    .apply(lambda g: g[g["retained_term_2"]]["student_count"].sum()
                   / g["student_count"].sum())
    .reset_index(name="retention_rate")
)

print(retention)
```

## Plan templates

If you run the same query structure repeatedly with different
parameters, create a template:

```
plan

source_id: "glue://registrar_db/student_retention_cohorts"
objective: "Retention counts by Pell and first-gen for cohort {{cohort_term}}"
is_template: true
```

Then instantiate it for each cohort:

```
instantiate_plan

plan_id: "plan-template-id"
values:
  cohort_term: "202510"
```

## IRB-gated plans

For sensitive research data, add `requires_irb: true`:

```
plan

source_id: "glue://research_db/clinical_outcomes"
objective: "De-identified outcome measures by treatment arm"
requires_irb: true
```

The plan status will be `pending_approval`. Excavation is blocked until
an authorized IRB reviewer approves it via the `approve_plan` Lambda.
