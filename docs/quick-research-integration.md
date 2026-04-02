# Using Quick Research with Quick Suite Extensions

Quick Research is Amazon Quick Suite's deep-research capability. On its own it's
excellent at synthesizing information from documents and the web. But many university
research questions aren't answered by documents — they live in databases, spreadsheets,
Athena tables, and S3 buckets full of institutional records.

When you connect the Quick Suite extensions to Quick Research through AgentCore Gateway,
it gains the ability to go find that data, run statistics on it, and weave the results
into a research narrative — all from a single conversation.

This guide explains how that works, gives you concrete examples organized by use case
type, and tells you how to configure Quick Research to make the most of these capabilities.

---

## The Basic Idea

When a user sends a research request to Quick Research, the agent can now call out to
real data tools mid-conversation — the same way a human researcher might pause to pull
up a spreadsheet or query a database. The difference is that the agent does this
automatically, choosing the right tool for each step, and brings the results back into
the conversation as context for its next move.

A typical data-grounded research flow looks like this:

1. **Find the data** — search public datasets or browse institutional S3
2. **Load it** — register it as a Quick Sight dataset
3. **Inspect it** — look at the schema and a few sample rows before writing any queries
4. **Query it** — translate the research question into SQL (policy-checked first)
5. **Analyze it** — run the right statistical profile on the results
6. **Synthesize** — pull everything together into a narrative with citations and context

Each step produces structured output that flows into the next step. Quick Research
handles the sequencing; the extensions handle the data work.

---

## How Tools Pass Results to Each Other

Each tool returns a JSON response. Quick Research uses fields from one tool's response as
inputs to the next. Here are the key connections to understand:

**After loading a dataset (`roda_load` or `s3_load`):** You get a `source_id` — something
like `roda-ipeds-fall-enrollment` or `s3-alumni-giving-2024`. This can be passed to
Compute as a `claws://source_id` URI. The system looks up the actual Quick Sight dataset
automatically — no manual ID hunting required.

**After planning a query (`claws.plan`):** You get a `plan_id`. This is the only thing
`claws.excavate` needs. The plan holds the approved SQL; excavate verifies it matches
before running anything. This prevents the query from being quietly changed between
approval and execution.

**After excavating data (`claws.excavate`):** You get a `run_id`. Pass this to
`claws.refine` (to deduplicate and summarize) or `claws.export` (to save it with a
provenance chain).

**After starting a Compute job (`compute_run`):** You get a `job_id`. Quick Research
should poll `compute_status` with this ID at regular intervals and tell the user
something like "the clustering job is running — I'll check back in a moment" rather
than going silent or re-submitting the job.

---

## Worked Examples: Academic Research

These examples show how faculty, graduate researchers, and research centers can use
the extensions to run data-driven analyses that would otherwise require a dedicated data
engineering pipeline or manual database work.

---

### Genomics: Mutation Co-Occurrence Across Cancer Subtypes

**The question:** *"What are the most common co-occurring mutation pairs in our TCGA
breast cancer samples, and do the frequencies differ significantly between the
ER-positive and ER-negative subtypes?"*

**Why Quick Suite alone can't answer this:** This requires querying a structured Athena
table with row-level security. The query needs to be approved against a Cedar policy
governing access to genomics data, and the results need to be scanned for PHI before
they leave the database.

**What happens:**

| Step | Tool | What it does |
|------|------|--------------|
| 1 | `claws.discover` | Finds the genomics data source in the approved `genomics-shared` domain |
| 2 | `claws.probe` | Inspects the schema and sample rows; ApplyGuardrail scans for PHI before returning samples |
| 3 | `claws.plan` | Translates the research question into SQL; Cedar validates that this principal can query this space |
| 4 | `claws.excavate` | Runs the approved query against Athena; results scanned by ApplyGuardrail |
| 5 | `claws.refine` | Deduplicates results and generates a grounded summary |
| 6 | `router.research` | Synthesizes clinical context and statistical significance into a research narrative |

**What the researcher gets:** A ranked table of mutation pairs with counts by subtype,
a chi-square or Fisher's exact test summary for group comparisons, and a narrative
suitable for a manuscript methods section — along with a provenance file documenting
exactly what was queried, when, and under which Cedar policy.

**Key safety note:** Cedar policies must permit the `genomics` domain for the requesting
principal. Bedrock Guardrails will block the pipeline if any result row contains a
patient identifier that shouldn't be surfaced at the query level.

---

### Climate Science: Decadal Temperature Trends at High-Altitude Stations

**The question:** *"We're studying how warming rates differ with elevation. Pull NOAA
GHCN daily temperature data for weather stations above 2,000 meters, compute the
mean annual anomaly for each station since 1980, and tell me how strongly elevation
and latitude predict the magnitude of warming."*

**Why Quick Suite alone can't answer this:** NOAA GHCN data isn't pre-loaded into
Quick Sight — it needs to be found in RODA and loaded on demand. The correlation
analysis between continuous variables (elevation, latitude, warming anomaly) requires
a statistical model, not just a chart.

**What happens:**

| Step | Tool | What it does |
|------|------|--------------|
| 1 | `roda_search` | Finds the NOAA Global Historical Climatology Network daily dataset in RODA |
| 2 | `roda_load` | Loads it into Quick Sight; returns `source_id: roda-noaa-ghcn-daily` |
| 3 | `claws.discover` | Confirms the dataset is also available in the Glue catalog for SQL queries |
| 4 | `claws.plan` | Generates SQL to filter stations above 2000m, compute annual mean anomalies relative to the 1951–1980 baseline, and join with station metadata (elevation, latitude) |
| 5 | `claws.excavate` | Runs the aggregation query; returns one row per station per year |
| 6 | `compute_run` | Runs `regression-glm` using elevation and latitude as predictors of the mean warming anomaly; `model_type=linear` |
| 7 | `compute_status` | Waits for results (typically 20–40 seconds) |
| 8 | `router.research` | Synthesizes coefficient estimates, R², and a plain-language interpretation of the elevation gradient |

**What the researcher gets:** Station-level warming anomaly data in Quick Sight (ready
to map). A regression summary with coefficients, standard errors, and model fit statistics.
A narrative explaining the relationship between elevation and warming rate in terms
suitable for a journal abstract or grant report.

**Extending this example:** Add `geo-enrich` after step 5 to append Census region codes
to each station, then re-run the regression with region as a categorical predictor
to test whether elevation effects differ by geographic area.

---

### Public Health: Social Determinants of Chronic Disease Prevalence

**The question:** *"For our NIH R01 application, I need to know which Census
tract-level social determinants most strongly predict diabetes prevalence across
urban counties. Use CDC PLACES data and ACS 5-year estimates."*

**Why Quick Suite alone can't answer this:** This requires loading two separate public
datasets, joining them on a geographic key (Census tract FIPS code), and running a
feature importance analysis. Quick Suite can show a scatterplot of two variables but
cannot orchestrate a multi-dataset join and regression.

**What happens:**

| Step | Tool | What it does |
|------|------|--------------|
| 1 | `roda_search` | Finds CDC PLACES (local area health measures) in RODA |
| 2 | `roda_load` | Loads CDC PLACES; returns `source_id: roda-cdc-places-2024` |
| 3 | `roda_search` | Finds Census ACS 5-year tract-level estimates in RODA |
| 4 | `roda_load` | Loads ACS data; returns `source_id: roda-census-acs5-tracts` |
| 5 | `claws.plan` | Generates SQL to join the two datasets on FIPS code, filter to urban counties (RUCC codes 1–3), and select the diabetes prevalence column plus social determinant variables |
| 6 | `claws.excavate` | Runs the join and returns the combined dataset |
| 7 | `compute_run` | Runs `regression-glm` with diabetes prevalence as the target and 15+ social determinant variables as features; `model_type=linear`, `include_interactions=false` |
| 8 | `compute_status` | Waits for results |
| 9 | `router.research` | Synthesizes ranked predictor importance, coefficient table, and language for the Specific Aims section |

**What the researcher gets:** A feature importance ranking showing which social
determinants (poverty rate, lack of health insurance, food access index, etc.) are
the strongest predictors of diabetes prevalence in the study area. A coefficient
table with confidence intervals. A Quick Sight dataset ready for the mapping figures
in the grant application.

---

### Ecology: Species Range Shifts and Biodiversity Monitoring

**The question:** *"We're tracking potential range shifts in three focal migratory bird
species over the past two decades. Can you pull GBIF occurrence records, flag stations
that show anomalous absence patterns compared to their historical baseline, and tell
me which species shows the strongest evidence of northward range shift?"*

**Why Quick Suite alone can't answer this:** GBIF occurrence data lives in RODA but
isn't pre-loaded. Detecting anomalous absences requires a statistical model trained
on the historical distribution — not a threshold or a chart.

**What happens:**

| Step | Tool | What it does |
|------|------|--------------|
| 1 | `roda_search` | Finds the GBIF Global Biodiversity Information Facility dataset in RODA |
| 2 | `roda_load` | Loads GBIF occurrence records; returns `source_id: roda-gbif-occurrences` |
| 3 | `claws.plan` | Generates SQL to filter the three focal species, compute per-station occurrence counts by decade, and flag stations with zero records in the 2015–2024 decade that had records in the 1995–2004 baseline |
| 4 | `claws.excavate` | Returns the filtered, per-station, per-decade occurrence table |
| 5 | `compute_run` | Runs `anomaly-isolation-forest` on the per-station occurrence features (latitude, longitude, historical mean count, recent count, trend slope) to score each station's departure from its historical pattern |
| 6 | `compute_status` | Waits for results |
| 7 | `compute_run` | Runs `regression-glm` with latitude as the target and year as the predictor, separately for each species, to estimate the northward shift rate in degrees per decade |
| 8 | `compute_status` | Waits for the regression results |
| 9 | `router.research` | Compares shift rates across the three species, places them in the context of published range-shift literature, and drafts a results paragraph |

**What the ecologist gets:** A station-level anomaly score dataset, ready to overlay on
a map in Quick Sight. A per-species regression summary showing the estimated rate of
northward movement in km/decade. A narrative results paragraph with the key finding and
statistical support, suitable for a conservation biology manuscript.

---

### Economics: Regional Labor Market Response to Industry Shocks

**The question:** *"We're studying how regional labor markets recover from manufacturing
plant closures. Can you pull BLS Quarterly Census of Employment and Wages data for the
affected counties, compare pre- and post-closure employment trajectories, and run a
difference-in-differences against matched control counties?"*

**Why Quick Suite alone can't answer this:** BLS QCEW data is a large public dataset
in RODA, but the comparison between treated and control counties requires joining tables,
computing lagged differences, and running a regression with interaction terms — none of
which Quick Suite can do without the extensions.

**What happens:**

| Step | Tool | What it does |
|------|------|--------------|
| 1 | `roda_search` | Finds BLS Quarterly Census of Employment and Wages in RODA |
| 2 | `roda_load` | Loads QCEW county-level data; returns `source_id: roda-bls-qcew` |
| 3 | `claws.plan` | Generates SQL to select treated counties (those with a plant closure in the study window), compute quarterly employment indices relative to the closure quarter, and join with a pre-built control county list from institutional S3 |
| 4 | `claws.excavate` | Returns the panel dataset with county-quarter observations |
| 5 | `compute_run` | Runs `regression-glm` with a difference-in-differences specification: employment index as the target, `post_closure` and `treated` indicators and their interaction as predictors, county and quarter fixed effects as categorical variables |
| 6 | `compute_status` | Waits for results |
| 7 | `router.research` | Interprets the interaction coefficient (the DiD estimate), discusses parallel trends assumptions, and drafts a results section with appropriate econometric language |

**What the economist gets:** The DiD coefficient estimate with standard error, t-statistic,
and confidence interval. A coefficients table for the full model. A narrative results
section that correctly describes the identifying assumption and interprets the magnitude
of the employment effect in percentage-point terms.

---

## Worked Examples: Administrative Analytics

These examples are drawn from institutional research, enrollment management, student
affairs, advancement, sponsored programs, and compliance — the operational offices that
keep a university running and reported accurately.

---

### Enrollment Forecasting for Budget Planning

**The question:** *"What will our fall enrollment look like over the next three years,
broken down by college? Use IPEDS data and assume current trends continue."*

**Why Quick Suite alone can't answer this:** Quick Suite can show a chart of enrollment
data already in Quick Sight. It can't find the IPEDS dataset, load it on demand, or run
a time series forecast.

**What happens:**

| Step | Tool | What it does |
|------|------|--------------|
| 1 | `roda_search` | Finds IPEDS enrollment datasets in the Registry of Open Data |
| 2 | `roda_load` | Loads the dataset into Quick Sight; returns `source_id: roda-ipeds-fall-enrollment` |
| 3 | `compute_run` | Starts a Prophet forecast job using `claws://roda-ipeds-fall-enrollment`, with `forecast_horizon=6` semesters and `seasonality_mode=multiplicative` |
| 4 | `compute_status` | Polls until the job completes (usually 30–60 seconds) |
| 5 | `router.research` | Synthesizes a narrative with year-over-year projections and risk scenarios |

**What the budget office gets:** A Quick Sight dataset with forecast values, confidence
intervals, and trend decomposition — plus a plain-language narrative suitable for a
provost's budget briefing.

---

### Identifying At-Risk Students Early in the Semester

**The question:** *"Based on the first four weeks of LMS activity, which students are
showing patterns similar to those who withdrew last year? Flag them so advising can
reach out."*

**Why Quick Suite alone can't answer this:** Requires running an anomaly detection model
on live LMS data. Quick Suite can visualize results but cannot perform the analysis.

**What happens:**

| Step | Tool | What it does |
|------|------|--------------|
| 1 | `s3_browse` | Finds the LMS activity export in institutional S3 |
| 2 | `s3_preview` | Samples 50 rows to confirm schema (login counts, assignments submitted, discussion posts, etc.) |
| 3 | `s3_load` | Registers the file as a Quick Sight data source; returns `source_id: s3-lms-week4-current` |
| 4 | `compute_run` | Runs `anomaly-isolation-forest` on engagement features with `contamination=0.05` (flag the 5% most anomalous) |
| 5 | `compute_status` | Waits for results |
| 6 | `router.summarize` | Summarizes flagged students' common engagement patterns in plain language |

**What advising gets:** The original dataset with two new columns — `is_anomaly` (true/false)
and `anomaly_score` (0–1). Filter on `is_anomaly = true` in Quick Sight to build the
outreach list. Cedar policies restrict this data space to authorized advising staff;
Guardrails redacts student identifiers from the summarized output.

---

### Making Sense of Course Evaluation Comments at Scale

**The question:** *"We have 40,000 open-ended course evaluation responses from this
semester. What are the main themes? Which themes are most associated with high and low
ratings?"*

**Why Quick Suite alone can't answer this:** Reading and categorizing 40,000 open-ended
responses requires a topic model — Quick Research's synthesis capability is designed to
work with structured outputs, not to manually read 40K free-text responses.

**What happens:**

| Step | Tool | What it does |
|------|------|--------------|
| 1 | `s3_browse` | Finds the course evaluation export |
| 2 | `s3_load` | Registers it; returns `source_id: s3-eval-fall-2025` |
| 3 | `compute_run` | Runs `text-topics` with `num_topics=12`, `method=LDA`, targeting the open-ended response column |
| 4 | `compute_status` | Waits (2–4 minutes on 40K records) |
| 5 | `router.research` | Synthesizes each topic's top terms and the distribution of topics by course rating quartile |

**What the provost's office gets:** Every response labeled with its dominant topic and
probability. A summary of which themes appear most often in high-rated versus low-rated
courses — across all 40,000 responses, with no sampling and no manual coding.

---

### Donor Segmentation for Major Gift Strategy

**The question:** *"Segment our alumni donor pool by giving history and engagement
patterns, and tell me which cluster has the highest major gift potential."*

**Why Quick Suite alone can't answer this:** Donor segmentation requires loading
institutional giving records (not a public dataset) and running clustering — neither
possible in stock Quick Suite.

**What happens:**

| Step | Tool | What it does |
|------|------|--------------|
| 1 | `s3_browse` | Finds alumni giving records in the advancement office's S3 bucket |
| 2 | `s3_preview` | Samples the schema (cumulative giving, last gift date, event attendance, engagement score, etc.) |
| 3 | `s3_load` | Registers the data; returns `source_id: s3-alumni-giving-2025` |
| 4 | `compute_run` | Runs `clustering-kmeans` with k=5 on giving and engagement features |
| 5 | `compute_status` | Waits for results |
| 6 | `router.analyze` | Interprets each cluster's mean features and labels them meaningfully (e.g., "lapsed mid-level", "consistent annual fund", "event-engaged not yet giving") |

**What advancement gets:** Every donor record with a `cluster_id` and `cluster_distance`.
A narrative summary of each cluster's characteristics. The analysis is repeatable — run
it quarterly to track how donors move between segments over time.

---

### Equity Reporting: Time-to-Degree Analysis

**The question:** *"For our accreditation self-study, we need a Kaplan-Meier survival
analysis comparing time-to-degree between first-generation and continuing-generation
students, by Pell eligibility, and by race/ethnicity."*

**Why Quick Suite alone can't answer this:** Survival analysis is a specific statistical
technique. Quick Suite can display an output chart, but it cannot run the analysis.

**What happens:**

| Step | Tool | What it does |
|------|------|--------------|
| 1 | `s3_load` | Loads the cohort tracking file (entry term, graduation or withdrawal date, demographic flags) |
| 2 | `compute_run` | Runs `survival-kaplan-meier` with `duration_column=semesters_enrolled`, `event_column=graduated`, `group_column=first_gen_flag` |
| 3 | `compute_status` | Waits for results |
| 4 | (Repeat steps 2–3 for Pell status and race/ethnicity) | |
| 5 | `router.research` | Synthesizes a comparative narrative with median survival times, log-rank test results, and accreditation-appropriate language |

**What IR gets:** Survival curves with confidence bands for each group. Median time-to-degree
per group. Log-rank test p-values. All in a Quick Sight dataset that feeds directly into
the accreditation dashboard.

---

### Grant Burn Rate Monitoring for Sponsored Programs

**The question:** *"Which active grants are at risk of under-spending before the fiscal
year ends? Flag any awards that are more than 20% behind their expected burn rate."*

**Why Quick Suite alone can't answer this:** This requires querying a financial database
(a restricted data source), computing expected versus actual expenditure ratios, and
flagging outliers — none of which Quick Suite can do on its own.

**What happens:**

| Step | Tool | What it does |
|------|------|--------------|
| 1 | `claws.discover` | Finds the sponsored awards expenditure data in the approved `finance` domain |
| 2 | `claws.probe` | Previews the schema (award_id, sponsor, total_budget, expenditures_to_date, end_date, PI name, etc.) |
| 3 | `claws.plan` | Translates the objective into SQL: compute actual burn rate as expenditures_to_date / total_budget, compare against expected burn rate based on days elapsed, flag where the ratio is below 0.8; Cedar confirms the sponsored programs team has access |
| 4 | `claws.excavate` | Runs the query |
| 5 | `claws.export` | Saves results to S3 with a provenance chain (required for federal reporting documentation) |
| 6 | `router.summarize` | Produces a ranked list of at-risk awards with PI names, sponsors, budgets, and recommended actions |

**What the grants office gets:** A ranked list of at-risk awards with specific numbers —
amount spent, amount expected by this date, days remaining, and a risk flag. The provenance
file documents that the analysis ran on today's expenditure data, supporting any audit of
the flagging methodology.

---

### Financial Aid Compliance Audit

**The question:** *"Which financial aid records in the 2024 cohort are missing FAFSA
completion dates? Break the gap down by demographic category for the Title IV report."*

**Why Quick Suite alone can't answer this:** Financial aid records sit in a restricted
Athena table. The query requires Cedar permission for the financial aid team's data space,
and the export needs a documented provenance chain for FERPA compliance.

**What happens:**

| Step | Tool | What it does |
|------|------|--------------|
| 1 | `claws.discover` | Finds the financial aid records in the `institutional` domain |
| 2 | `claws.probe` | Previews schema and confirms the FAFSA completion date column exists; Guardrails scans sample rows for SSN exposure |
| 3 | `claws.plan` | Generates SQL to find records where `fafsa_completion_date IS NULL`, grouped by demographic category; Cedar validates the financial aid team's access |
| 4 | `claws.excavate` | Executes the query |
| 5 | `claws.refine` | Deduplicates and produces a category-level summary count |
| 6 | `claws.export` | Exports with provenance chain to the compliance S3 bucket |
| 7 | `router.summarize` | Drafts a plain-language summary for the Title IV coordinator |

**What compliance gets:** The row-level export with a `.provenance.json` sidecar recording
the principal, timestamp, policy that permitted the query, and destination. This is the
audit trail FERPA and Title IV oversight require — generated automatically, not assembled
by hand.

---

## Configuring Quick Research

When setting up Quick Research with these extensions via AgentCore Gateway, add the
following to the system prompt. This tells Quick Research how to use the tools
correctly and avoids common sequencing mistakes.

```
You have access to university research and analytics tools through AgentCore Gateway:

Tool groups:
- qs-data: Find and load public and institutional data (roda_search, roda_load, s3_browse, s3_preview, s3_load)
- qs-claws: Policy-gated queries against raw databases (discover, probe, plan, excavate, refine, export)
- qs-compute: Statistical analysis profiles (compute_profiles, compute_run, compute_status)
- qs-router: Multi-provider language model routing (analyze, generate, research, summarize, code)

Rules for sequencing:
1. Always call s3_preview or claws.probe before writing any query — confirm the schema first.
2. Always call claws.plan before claws.excavate — never construct SQL yourself.
3. After compute_run returns a job_id, poll compute_status at 15-second intervals.
   Tell the user the job is in progress; do not re-submit it.
4. When claws.plan returns cedar_decision: "deny", explain that the user's current
   permissions don't allow that query and suggest they contact their data steward.
5. For research synthesis at the end of a data pipeline, use qs-router___research
   rather than answering directly — it applies Bedrock Guardrails and routes to the
   strongest available model.
6. Always include provenance_uri in responses that involve compliance exports.

Data URI format: claws://{source_id}
- After roda_load: source_id is "roda-{slug}"
- After s3_load: source_id is "s3-{label}"
- Pass as source_uri to compute_run
```

### Prompts That Work Well

Different user communities phrase questions differently. Here are prompts that reliably
trigger the right tool sequences:

**Academic research:** *"Pull [dataset name] from RODA and run a [method] analysis
comparing [group A] to [group B] on [outcome]."*

**Institutional research:** *"I need an IPEDS-based [metric] for our [report type],
broken down by [dimension]."*

**Student success:** *"Flag [anomaly/pattern/outlier] in [data source] and summarize
what you find for [audience]."*

**Compliance:** *"Audit [data source] for [condition] and export the results with a
provenance chain for [regulatory purpose]."*

**Advancement:** *"Segment [donor/prospect pool] by [features] and identify
[strategic group] for [purpose]."*

In general, prompts that mention a specific dataset name, a statistical method, or a
report type (accreditation, Title IV, NIH, IPEDS) are the ones most likely to trigger
the full data pipeline rather than a web-only research response.

---

## Quick Index Integration

Quick Index is Quick Suite's data discovery layer. It catalogs datasets already in
Quick Sight so users can find them by name or topic. The extensions and Quick Index
work together in a few useful ways.

**Newly loaded datasets appear in Quick Index automatically.** When `roda_load` or
`s3_load` registers a new Quick Sight dataset, Quick Index picks it up on its next
crawl. After that, users can find it through Quick Index's discovery interface in
addition to the chat tools.

**The ClawsLookupTable bridges Quick Index and the compute pipeline.** When any loading
tool registers a dataset, it writes an entry to ClawsLookupTable with the `source_id`
as a key. The Compute extension's extract step uses this table to resolve `claws://` URIs —
so a user can load data through Quick Index's UI and a subsequent chat request to analyze
that data via Compute will find it automatically.

**Three-tier data discovery.** When Quick Research needs to find data for a research
question, it follows this fallback sequence:

1. `claws.discover` — finds sources already cataloged in Glue (Athena/raw data)
2. `roda_search` — finds sources in the Registry of Open Data
3. `s3_browse` — finds sources in configured institutional S3 buckets

This means that regardless of where data lives — a Glue-cataloged Athena table, a public
open dataset, or an institutional S3 file — Quick Research can find and use it through a
single conversation.
