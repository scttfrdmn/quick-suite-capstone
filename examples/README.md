# Quick Suite Examples

Most university analytics still requires an intermediary. A faculty member
with a research question waits days for IT to pull a dataset. An IR analyst
submits a ticket to run a regression. A compliance officer emails someone to
check an Athena table, then waits for a report back. Even with Quick Suite's
built-in capabilities, data that isn't already in Quick Sight is invisible to
the agent.

These extensions change that. The examples in this directory show what becomes
possible when the four Quick Suite extensions are deployed together: a user can
start from a plain-language question and arrive at a statistical result, a
provenance-backed export, or a grant-ready narrative — entirely through the
Quick Suite chat interface, without a data engineer in the room.

---

## What These Examples Show

There are two fundamentally different kinds of workflows here, and they reflect
two different problems the extensions solve.

### Reaching Public Data

The [Registry of Open Data on AWS](https://registry.opendata.aws/) hosts over
500 curated public datasets — NOAA climate records, CDC health measures, Census
demographics, NIH genomics data, IPEDS enrollment statistics, GBIF species
observations, OpenAQ air quality readings, and dozens more. Most of these are
directly relevant to university research and institutional analytics. But they
don't exist in Quick Sight. Getting one into a Quick Sight dataset has
historically meant knowing where it lives, downloading it, formatting it,
uploading it, and registering a data source — a process that takes an hour and
requires skills most researchers don't have.

With the Data extension and Compute extension deployed, the process is:
*"Find me NOAA climate data and run a temperature trend forecast."*
That's it. The agent calls `roda_search` to find the dataset, `roda_load` to
register it in Quick Sight, and `compute_run` to start the Prophet forecast —
all in one conversation, in about five minutes.

The **academic-research** examples in this directory all follow this pattern.
They use only public RODA datasets and require no institutional configuration
to run. They're designed for faculty, graduate students, and research computing
teams who want to do real analysis without managing data pipelines.

### Reaching Institutional Data

Public datasets are the easier problem. The harder problem is institutional
data: the student information system, financial aid records, alumni giving
history, sponsored program expenditures, course evaluation responses. This data
lives in institutional databases or S3 buckets. It's sensitive. It has real
compliance obligations — FERPA, Title IV, IRB protocols, audit requirements.
Just being able to access it isn't enough; you need documented evidence of what
was accessed, by whom, under what authorization, and what was done with it.

The clAWS extension handles this. Every query goes through two independent
enforcement layers: Cedar policies (which define structurally what each team
can query) and Bedrock Guardrails (which scan for PII, injection attempts, and
content violations at the content level). Every export carries a provenance
chain. When a retention analyst runs a cohort analysis for an accreditation
self-study, the output includes the query that was run, the plan it came from,
the policy version that authorized it, and the timestamp — everything a
compliance office needs.

The **institutional-analytics** examples follow this pattern. They compose
clAWS (for policy-gated access to institutional databases) with Compute (for
analysis) and sometimes the Router (for narrative generation). Examples that
require institutional Athena tables say so clearly and describe the expected
schema; two of them (enrollment forecast and peer benchmarking) use only public
IPEDS data and run without any institutional setup.

---

## Academic Research

Five scenarios using public RODA datasets. No institutional configuration needed.

| Scenario | Who runs it | What it answers |
|---|---|---|
| [NOAA Climate Trends](academic-research/noaa-climate-trends/) | Climate scientists, atmospheric researchers | 24-month Prophet forecast of NOAA GHCN maximum temperature trends |
| [1000 Genomes Population Structure](academic-research/1000genomes-population-structure/) | Bioinformaticians, population geneticists | Do k-means clusters on PCA components recover the five known super-population groups? |
| [CDC Health Disparities](academic-research/cdc-health-disparities/) | Public health researchers | Which social determinants best predict diabetes prevalence variation across census tracts? |
| [GBIF Species Range Shift](academic-research/gbif-species-range-shift/) | Ecologists, conservation biologists | Is observed latitude shifting northward over time — the primary signal of poleward range movement? |
| [OpenAQ Pollution Spikes](academic-research/openaq-pollution-spikes/) | Environmental scientists, air quality researchers | Which air quality readings are statistical anomalies consistent with pollution spike events? |

A researcher asks: *"Pull NOAA climate data and project maximum temperature
trends for the next two years."* Quick Suite calls `roda_search`, finds the
GHCN dataset, loads it, runs the Prophet forecast, and returns a Parquet file
with the projection and confidence intervals — without the researcher ever
touching a data pipeline or a Jupyter notebook.

---

## Institutional Analytics

Six scenarios for IR offices, enrollment analysts, advancement teams, and
compliance staff. Two use only public RODA data; four require institutional
Athena tables or S3 paths.

| Scenario | Who runs it | Data | What it answers |
|---|---|---|---|
| [Enrollment Forecast](institutional-analytics/enrollment-forecast/) | IR directors, enrollment planning | Public (IPEDS) | 8-semester headcount projection with provost narrative |
| [Peer Benchmarking](institutional-analytics/peer-benchmarking/) | IR directors, CFO's office | Public (IPEDS) | Where does our tuition revenue per FTE land among peer institutions? |
| [Student Retention Cohort](institutional-analytics/student-retention/) | Retention analysts, Student Success | Institutional (SIS) | First-to-second year retention by cohort and Pell status for accreditation reporting |
| [Donor Segmentation](institutional-analytics/donor-segmentation/) | Advancement analytics | Institutional (Alumni DB) | Which donors cluster together by giving behavior, and which cluster has major gift potential? |
| [Course Eval Topics](institutional-analytics/course-eval-topics/) | Academic affairs, Faculty Senate | Institutional (Eval exports) | What are the dominant themes in open-ended course evaluation responses, by department? |
| [Grant Anomaly Detection](institutional-analytics/grant-anomaly-detection/) | Research compliance, Sponsored Programs | Institutional (Awards DB) | Which sponsored awards show burn-rate patterns that warrant closer compliance review? |

An IR analyst asks: *"What does our enrollment look like through 2029, and can
you draft a paragraph for the provost's budget memo?"* Quick Suite finds the
IPEDS dataset, loads it, runs a Prophet forecast with multiplicative
seasonality, and then passes the result URI to the Router, which generates a
polished summary paragraph grounded in the actual forecast numbers.

A retention director asks: *"Show me first-to-second year retention by Pell
status for the last five cohorts."* clAWS checks the analyst's Cedar policy
(the Student Success team can read retention data but not export row-level
records), generates a SQL query against the SIS Athena table, validates it,
executes it, and returns a cohort retention matrix — along with a provenance
file suitable for submission as an accreditation evidence artifact.

---

## How to Run These Scenarios

Each example directory contains a `scenario.yaml` describing the workflow
steps, inputs, and assertions. The capstone scenario runner executes them
against your deployed stacks:

```bash
# Run a single scenario
AWS_PROFILE=aws python3 -m pytest tests/scenarios/ -v -m scenario -k noaa-climate-trends

# Run all academic-research scenarios
AWS_PROFILE=aws python3 -m pytest tests/scenarios/ -v -m scenario -k academic-research

# Run everything
AWS_PROFILE=aws python3 -m pytest tests/scenarios/ -v -m scenario
```

Scenarios skip automatically when a required stack is not deployed. A skip
means "this infrastructure isn't here yet." A failure means "the pipeline is
broken." Both are signals worth acting on.

See [`tests/scenarios/runner.py`](../tests/scenarios/runner.py) for the
runner implementation and [`tests/scenarios/conftest.py`](../tests/scenarios/conftest.py)
for AWS credential and region configuration.
