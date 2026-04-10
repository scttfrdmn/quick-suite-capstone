# Cross-Tool: Literature Search to Analysis Pipeline

A faculty researcher discovers relevant papers, extracts data from them,
loads comparison datasets, and runs a statistically rigorous analysis —
all from Kiro.

## The question

"Based on recent literature, what sample size do I need for my planned
mentoring intervention RCT, and how does my institution's baseline
retention compare to what other studies have found?"

## Step 1: Search the literature (Data)

```
pubmed_search

query: "peer mentoring first-generation college retention randomized"
max_results: 10
year_start: 2021
```

Returns 8 papers with PMIDs, titles, authors, and quality scores.

## Step 2: Extract effect sizes (Router)

For the top 3 RCTs:

```
extract

prompt: "<abstract of top-ranked paper>"
extraction_types: ["effect_sizes", "methods_profile", "confounds"]
```

Returns structured JSON: Cohen's d = 0.28, controlled for GPA and
financial need, cluster-randomized at the advisor level.

Repeat for the other two papers. You now have three effect sizes:
d = 0.28, d = 0.34, d = 0.22.

## Step 3: Run power analysis (Compute)

```
compute_run

profile_id: "power-analysis"
parameters:
  effect_size: 0.28
  alpha: 0.05
  power: 0.80
  pubmed_ids: ["38921456", "39102345", "38876543"]
```

Returns: n = 202 per group (404 total), power curve, confound checklist.

## Step 4: Get your baseline data (clAWS)

```
discover

query: "student retention first-year cohort"
scope:
  domains: ["institutional"]
```

```
plan

source_id: "glue://registrar_db/student_retention_cohorts"
objective: "First-gen retention rate for Fall 2023 and Fall 2024 cohorts"
```

```
excavate

plan_id: "plan-abc123"
source_id: "glue://registrar_db/student_retention_cohorts"
query: "<the generated SQL>"
query_type: "athena_sql"
```

Returns: your institution's first-gen retention is 68% — below the 74%
weighted average from the literature.

## Step 5: Load peer comparison data (Data)

```
roda_search

query: "IPEDS retention rates"
```

```
compute_run

profile_id: "peer-benchmark"
source_uri: "claws://roda-ipeds-retention"
parameters:
  metric: "retention_rate_first_gen"
  institution_id: "your_unitid"
  peer_group: "carnegie_r1"
```

Returns: your institution ranks at the 35th percentile among R1 peers
for first-gen retention.

## Step 6: Synthesize (Router)

```
research

prompt: "Given a baseline first-gen retention rate of 68% (35th
percentile among R1 peers), literature effect sizes of d=0.22-0.34
for mentoring interventions, and a required sample size of 404: write
a 200-word justification for this RCT for an NSF IUSE proposal."

grounding_mode: "strict"
```

## What you've built

In one Kiro session, you've:
1. Found the evidence base (PubMed)
2. Extracted structured effect sizes (Router)
3. Calculated a defensible sample size (Compute)
4. Established your institution's baseline (clAWS → Athena)
5. Benchmarked against peers (Data → Compute)
6. Drafted the proposal justification (Router)

Six tools across four extensions, all from the same MCP connection.

## The code artifact

Your Kiro project now contains a Jupyter notebook or Python script with
all of this wired together — reproducible, with every data source and
assumption documented by the tool call history.
