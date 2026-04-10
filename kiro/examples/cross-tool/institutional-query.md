# Cross-Tool: Institutional Query to Compute Analysis

An IR analyst discovers institutional data, runs a governed query, and
feeds the results into a statistical analysis — with full audit trail.

## The question

"Which departments have equity gaps in DFWI rates, and is the gap
widening or narrowing over the last four years?"

## Step 1: Find the data (clAWS)

```
discover

query: "course grades enrollment demographics"
scope:
  domains: ["institutional"]
```

Returns two relevant tables: `grade_roster` (grades by student by
section) and `student_demographics` (demographic attributes).

## Step 2: Inspect the schema (clAWS)

```
probe

source_id: "glue://registrar_db/grade_roster"
```

Returns columns: `student_id`, `term_code`, `course_id`, `department`,
`section`, `grade`, `credits`, `instructor_id`. PII scan flags
`student_id` and `instructor_id`.

## Step 3: Plan the query (clAWS)

```
plan

source_id: "glue://registrar_db/grade_roster"
objective: "DFWI counts by department, term, and Pell status for Fall
2022 through Fall 2025. Join with student_demographics on student_id.
Exclude summer terms. Aggregate — no row-level student data."
```

Cedar validates:
- Your principal (IR team) can query both tables
- You can access the `pell_recipient` column
- You cannot return `student_id` in results (column-level control)
- Aggregation means no row-level PII exposure

Returns the concrete SQL, cost estimate ($0.03), and output schema.

## Step 4: Execute the query (clAWS)

```
excavate

plan_id: "plan-def456"
source_id: "glue://registrar_db/grade_roster"
query: "<the generated SQL>"
query_type: "athena_sql"
```

Guardrails scan the results. Returns 480 rows (4 terms x 30
departments x 2 Pell statuses x 2 DFWI/non-DFWI).

## Step 5: Run DFWI analysis (Compute)

Export the excavation results and feed them to Compute:

```
export

run_id: "run-789abc"
destination:
  type: "s3"
  uri: "s3://qs-compute-inputs/dfwi-analysis/"
include_provenance: true
```

```
compute_run

profile_id: "dfwi-analysis"
source_uri: "s3://qs-compute-inputs/dfwi-analysis/data.parquet"
parameters:
  grade_column: "grade"
  group_columns: ["department", "pell_recipient"]
  dfwi_grades: ["D", "F", "W", "I"]
result_label: "dfwi-by-dept-pell-2025"
```

Returns DFWI rates by department and Pell status with flagged courses
above the 30% threshold.

## Step 6: Run equity gap analysis (Compute)

```
compute_run

profile_id: "equity-gap"
source_uri: "s3://qs-compute-inputs/dfwi-analysis/data.parquet"
parameters:
  outcome: "dfwi_rate"
  group: "pell_recipient"
  benchmark: 0.20
  subgroups: ["department"]
result_label: "equity-gap-dfwi-2025"
```

Returns equity gaps with effect sizes per department — which ones are
above the Disparate Impact threshold, and by how much.

## Step 7: Check the trend (Compute)

```
compute_run

profile_id: "change-detection"
source_uri: "s3://qs-compute-inputs/dfwi-analysis/data.parquet"
parameters:
  date_column: "term_code"
  value_column: "dfwi_rate"
  group_column: "department"
```

Returns structural break points — showing which departments have a
worsening trend vs. improving.

## Step 8: Remember the findings (clAWS)

```
remember

record:
  type: "equity_finding"
  severity: "high"
  finding: "Chemistry DFWI gap widening: Pell 34% vs non-Pell 18%, DI ratio 0.53, trend worsening since Fall 2023"
  tags: ["equity", "dfwi", "chemistry", "pell", "accreditation"]
  source_job_ids: ["exec-dfwi", "exec-equity", "exec-trend"]
```

## The audit trail

Every step is auditable:
- **Cedar** recorded which policies permitted the query
- **Guardrails** recorded the content scan results
- **Export** wrote a `.provenance.json` sidecar
- **Compute** wrote an audit record to S3
- **Remember** persisted the finding with source job IDs

A compliance officer can trace from the finding back to the exact query,
the exact policy that permitted it, and the exact Guardrail trace — all
without asking the analyst to recreate anything.
