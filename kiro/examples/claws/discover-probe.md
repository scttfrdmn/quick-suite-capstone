# clAWS: Discover and Probe Data Sources

Use `discover` to find data sources in approved domains, then `probe`
to inspect their schema and sample data before writing any queries.

## Scenario

You're writing a retention analysis and need to find the right
institutional data tables. You know the data exists somewhere in your
institution's Glue catalog and data registry, but you don't know the
exact table names or schemas.

## Tool calls

### Step 1: Discover

```
discover

query: "student retention cohort first-year"
scope:
  domains: ["institutional", "registry"]
```

Response:
```json
{
  "sources": [
    {
      "id": "glue://registrar_db/student_retention_cohorts",
      "type": "athena",
      "domain": "institutional",
      "description": "First-year cohort retention tracking, Fall 2018-present",
      "tags": ["retention", "cohort", "ipeds"]
    },
    {
      "id": "registry://s3-student-outcomes-retention",
      "type": "s3",
      "domain": "registry",
      "description": "Student outcomes retention file (CSV, updated monthly)"
    }
  ]
}
```

### Step 2: Probe

```
probe

source_id: "glue://registrar_db/student_retention_cohorts"
```

Response:
```json
{
  "schema": [
    {"name": "student_id", "type": "string", "pii": true},
    {"name": "cohort_term", "type": "string"},
    {"name": "entry_type", "type": "string"},
    {"name": "pell_recipient", "type": "boolean"},
    {"name": "first_generation", "type": "boolean"},
    {"name": "race_ethnicity", "type": "string"},
    {"name": "retained_term_2", "type": "boolean"},
    {"name": "retained_term_4", "type": "boolean"},
    {"name": "cumulative_gpa", "type": "decimal"}
  ],
  "sample_rows": 5,
  "row_count_estimate": 45000,
  "cost_estimate": {
    "full_scan_usd": 0.02,
    "partitions": ["cohort_term"]
  },
  "guardrail_scan": {
    "status": "passed",
    "pii_detected": ["student_id"]
  }
}
```

## How this fits your workflow

Now you know the exact column names and types. Write your analysis code
against the real schema:

```python
# You know the exact columns from probe
COHORT_COLS = ["cohort_term", "entry_type", "pell_recipient",
               "first_generation", "race_ethnicity"]
OUTCOME_COLS = ["retained_term_2", "retained_term_4", "cumulative_gpa"]

# Plan a query via clAWS (Cedar-gated)
plan = plan(
    source_id="glue://registrar_db/student_retention_cohorts",
    objective="Retention rates by cohort term, Pell status, and "
              "first-generation status for Fall 2020-2025 cohorts"
)

# Or submit directly to Compute
result = compute_run(
    profile_id="retention-cohort",
    source_uri="claws://glue-student-retention-cohorts",
    parameters={
        "student_id": "student_id",
        "cohort": "cohort_term",
        "event_date": "retained_term_2"
    }
)
```

## What Cedar controls

Your `discover` and `probe` results are filtered by your Cedar policy.
If your policy only allows access to the `enrollment` space, you won't
see tables in the `financial-aid` space. The `pii: true` flag on
`student_id` means your policy might allow you to query the table but
not return that column — column-level access control kicks in at
`excavate` time.
