# Scenario Tests

End-to-end tests that drive the full multi-stack workflows described in `examples/`.
Each `scenario.yaml` is executed against deployed AWS stacks.

## Running

```bash
# All scenarios (default region us-west-2 for data/compute):
AWS_PROFILE=aws python3 -m pytest tests/scenarios/test_scenarios.py -v

# One scenario:
AWS_PROFILE=aws python3 -m pytest tests/scenarios/test_scenarios.py -k noaa-climate -v

# One category:
AWS_PROFILE=aws python3 -m pytest tests/scenarios/test_scenarios.py -k academic-research -v

# Override region (if data/compute stacks are in a different region):
AWS_PROFILE=aws QS_SCENARIO_REGION=us-east-1 python3 -m pytest tests/scenarios/test_scenarios.py -v
```

**Region note:** `QS_SCENARIO_REGION` sets the default region for `data` and `compute` stacks
(default: `us-west-2`). The `router` and `claws` stacks always resolve to `us-east-1`
regardless of this setting — they have per-stack region overrides in the runner.

## Prerequisites

### Stacks

| Stack | CloudFormation name | Region |
|---|---|---|
| data | QuickSuiteOpenData | us-west-2 |
| compute | QuickSuiteCompute | us-west-2 |
| router | QuickSuiteModelRouter | us-east-1 |
| claws | ClawsToolsStack | us-east-1 |

Tests skip (not fail) when a required stack is not deployed. A skip means
missing infrastructure; a failure means a broken pipeline.

### clAWS demo data (required for `institutional-analytics` scenarios)

The four claws-pipeline scenarios require pre-seeded Glue tables in `us-east-1`:

| Glue table | S3 path |
|---|---|
| `claws_demo.course_evaluations` | `s3://claws-runs-942542972736/demo-data/course_evaluations.csv` |
| `claws_demo.student_retention_cohorts` | `s3://claws-runs-942542972736/demo-data/student_retention_cohorts.csv` |
| `claws_demo.donor_giving_history` | `s3://claws-runs-942542972736/demo-data/donor_giving_history.csv` |
| `claws_demo.sponsored_program_expenditures` | `s3://claws-runs-942542972736/demo-data/sponsored_program_expenditures.csv` |

These tables are not created by the test suite. If they're missing, the `discover` step
will return no results and the scenario will fail (not skip).

## Authoring Scenarios

### General rules

- **Don't use `roda_load` as a pipeline step.** It creates persistent QuickSight resources
  that are expensive and require cleanup. Use `source_uri: "s3://..."` directly in
  `compute_run` instead — the compute extract Lambda has `s3:GetObject` on `*`.
- **Probe before plan.** The `probe` step populates the schema cache that `plan` uses.
  Calling `plan` without a prior `probe` will produce a query with no column context.
- **Compute profile enums are lowercase.** `method: lda` not `method: LDA`.
  Wrong values return `{"error": "Parameter validation failed"}` immediately.

### clAWS tool API reference

These are the ground-truth field names from the deployed Lambda handlers.
The scenario YAML must match these exactly — the handlers are strict about unknown fields.

**discover**
```yaml
tool: claws-discover
input:
  query: "keyword string"          # NOT keywords:
  scope:
    domains: ["athena"]            # NOT top-level domains:
assert:
  - path: "sources"
    op: exists
  - path: "sources.0.id"          # NOT sources.0.source_id
    op: exists
```

**probe**
```yaml
tool: claws-probe
input:
  source_id: "{discover.sources.0.id}"
  mode: schema_only
assert:
  - path: "schema"
    op: exists
```

**plan**
```yaml
tool: claws-plan
input:
  source_id: "{discover.sources.0.id}"
  objective: "plain English description"
  output_columns: [col1, col2, ...]
assert:
  - path: "plan_id"
    op: exists
  - path: "status"
    op: in
    value: ["ready", "pending_approval"]
```

**excavate** — requires all four fields; `query` and `query_type` come from the plan response nested under `input`
```yaml
tool: claws-excavate
input:
  plan_id: "{plan.plan_id}"
  source_id: "{discover.sources.0.id}"
  query: "{plan.steps.0.input.query}"        # nested under input, not plan.steps.0.query
  query_type: "{plan.steps.0.input.query_type}"
assert:
  - path: "result_uri"
    op: exists
  - path: "rows_returned"
    op: gte
    value: 1
```

**refine**
```yaml
tool: claws-refine
input:
  run_id: "{excavate.run_id}"      # NOT result_uri
  operations: ["dedupe"]           # or ["dedupe", "rank"]
assert:
  - path: "refined_uri"
    op: exists
```

**export**
```yaml
tool: claws-export
input:
  run_id: "{refine.run_id}"
  destination:
    type: s3
    uri: "s3://claws-runs-942542972736/demo-exports/my-scenario/"
  include_provenance: true         # NOT provenance: true
assert:
  - path: "destination_uri"        # NOT s3_uri
    op: exists
```

**compute_run** (after export)
```yaml
tool: compute_run
stack: compute
input:
  profile_id: "text-topics"
  source_uri: "{export_for_compute.destination_uri}"
  user_arn: "arn:aws:iam::942542972736:user/e2e-test-user"
  parameters:                      # NOT params:
    text_column: response_text
    method: lda                    # lowercase enum values
  result_label: "my-label"
assert:
  - path: "job_id"
    op: exists
```

### skip_if_fail

Use `skip_if_fail: true` on assertions where a miss means missing infrastructure
(not a code bug). The `roda_search` count assertion is a common candidate:

```yaml
assert:
  - path: "count"
    op: gte
    value: 1
    skip_if_fail: true  # catalog not synced yet → skip, not fail
```

Don't use it to hide real correctness assertions.
