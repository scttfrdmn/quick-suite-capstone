# Quick Suite Extensions

Amazon Quick Suite is a powerful agentic AI workspace — it can chat with your documents,
build dashboards from data already in Quick Sight, run deep research across the web, and
automate workflows. But there are things it simply cannot do out of the box: it can't reach
into a raw Athena database, it can't pull from 500 public research datasets on demand, it
can't run a clustering analysis on 300,000 student records, and it has no way to enforce
fine-grained data access policies at the query level.

**These extensions close those gaps.** Together they turn Quick Suite into a full research
and analytics platform for university teams — without requiring a data engineer in the room
every time someone has a question.

---

## What Quick Suite Can and Can't Do Alone

Think of stock Quick Suite like a brilliant research assistant who has read the entire
internet, can make beautiful charts from data you hand them, and can automate repetitive
tasks. What they can't do on their own:

| Without these extensions | With them |
|--------------------------|-----------|
| Only sees data already loaded into Quick Sight | Can search and load any of 500+ public research datasets on demand |
| Can't reach institutional S3 data (financial aid records, SIS exports, etc.) | Can browse, preview, and load institutional data by name |
| Can't query a raw Athena table or execute analytical SQL | Can plan and execute policy-gated queries against any approved data source |
| No statistical compute — charts only | Can run clustering, regression, forecasting, topic modeling, and more |
| Uses one built-in LLM | Can route to the best available model (Bedrock, Anthropic, OpenAI, Gemini) for each task |
| No per-query access control beyond IAM | Cedar policies enforce exactly who can query what, at the query level |
| No chain-of-custody for exported data | Every export carries a provenance chain: who queried what, when, under which policy |

The extensions work through **Amazon Bedrock AgentCore Gateway**, which acts as a bridge
between Quick Suite and these new capabilities. Quick Suite's agent sees all the new tools
the same way it sees its built-in ones — through natural conversation.

---

## The Four Extensions

### Router — Multi-Provider LLM Routing
[github.com/scttfrdmn/quick-suite-router](https://github.com/scttfrdmn/quick-suite-router)

Quick Suite has one built-in language model. The Router gives it access to four providers —
Amazon Bedrock, Anthropic (Claude), OpenAI (GPT), and Google (Gemini) — and intelligently
routes each request to the best option based on the task, your team's preferences, and
current availability. If one provider is down or slow, it falls back automatically. All
responses go through Bedrock Guardrails regardless of which model answered.

This matters for university teams because different tasks call for different models: a
dense federal policy document might be best handled by Claude, while a quick data
summary might not need the most expensive model at all. The Router makes those tradeoffs
automatically.

**What it adds to Quick Suite:** Choice of model without changing the interface.
Governance that follows the result regardless of where it came from.

---

### Data — Public and Institutional Data Access
[github.com/scttfrdmn/quick-suite-data](https://github.com/scttfrdmn/quick-suite-data)

Quick Suite only knows about data that's already been loaded into Quick Sight. The Data
extension adds two new ways to get data in:

**Public datasets** — The [Registry of Open Data on AWS](https://registry.opendata.aws/)
hosts 500+ curated public datasets: IPEDS enrollment statistics, CDC health data, Census
demographics, NOAA climate records, NIH genomics data, and dozens more relevant to
university research and institutional analytics. Ask for a dataset by name or topic, and
`roda_load` pulls it straight into a Quick Sight dataset in minutes.

**Institutional data** — `s3_browse` and `s3_load` let authorized users reach into
configured S3 buckets containing your own institutional data — SIS exports, financial
aid files, grant databases, alumni records — preview the schema before committing, and
register them as Quick Sight datasets for analysis.

Once loaded, these datasets are accessible from Compute jobs and clAWS queries using
a simple `claws://` URI — no hunting for dataset IDs required.

**What it adds to Quick Suite:** On-demand access to 500+ public research datasets,
plus a governed pathway for institutional data. Neither requires a data engineer or
a manual Quick Sight workflow.

---

### Compute — Ephemeral Analytics
[github.com/scttfrdmn/quick-suite-compute](https://github.com/scttfrdmn/quick-suite-compute)

Quick Suite can visualize data and generate text summaries, but it cannot run statistics.
The Compute extension brings 31 pre-built analysis profiles to Quick Suite's chat interface,
organized into 11 categories:

| Category | Profiles | Examples |
|----------|---------|---------|
| Statistics | anova, chi-square | Grade disparity by section; FAFSA completion rate by demographic |
| Prediction/ML | regression-glm, regression-logistic, classification-random-forest | Graduation probability; donor lapse risk |
| Forecasting | forecast-prophet, change-detection, seasonality-decompose | Enrollment 3 years forward; trend breaks |
| Clustering | clustering-kmeans | Applicant yield segments; donor prospect groups |
| Text | text-topics, text-sentiment, text-similarity | Course evaluation themes; policy document tone |
| Higher-Ed | cohort-flow, dfwi-analysis, equity-gap, peer-benchmark, retention-cohort | IPEDS reporting; accreditation equity gaps |
| Geospatial | geo-enrich, isochrone, spatial-aggregate | Census demographics by address; service area membership |
| Anomaly | anomaly-isolation-forest | Irregular financial transactions; at-risk LMS engagement |
| Research | grant-portfolio, network-coauthor | NCE risk flagging; co-authorship centrality |
| Ingest | ingest-netcdf, ingest-pdf-extract, ingest-geojson | Convert scientific files to tabular for further analysis |
| Custom | custom-python, custom-generated | Run your own script or describe what you want in plain language |

Compute also supports **chained profiles** — run `ingest-netcdf` and `forecast-prophet`
in a single job, with the NetCDF output feeding directly into the forecast — and
**named snapshots** for comparing results across time periods.

A user asks: *"Cluster this year's incoming class by application attributes and show me
the groups."* Compute validates the request against the profile's schema, checks that
the monthly budget allows it, runs the job in the background, and returns a new Quick
Sight dataset when it's done — usually in under a minute.

**What it adds to Quick Suite:** Statistical analysis accessible through conversation,
with built-in budget controls, named snapshots, chained profiles, and automatic results
delivery to Quick Sight.

---

### clAWS — Policy-Gated Data Excavation
[github.com/scttfrdmn/quick-suite-claws](https://github.com/scttfrdmn/quick-suite-claws)

clAWS is for when you need to go deeper: run a precise analytical query against a
restricted Athena table, search an OpenSearch index, or extract a specific slice of a
large dataset — all with documented evidence of what was accessed and why it was permitted.

It enforces two independent safety layers on every query:

- **Cedar policies** decide structurally whether a given principal can query a given
  data space. A Cedar policy might say: "The financial aid team can read the FAFSA
  completion table but not the SSN column. The IR team can aggregate but not export
  row-level records." These rules are evaluated before any query runs.
- **Bedrock Guardrails** scan query inputs and results for PII, injection attempts,
  and content policy violations — catching things that structural rules can miss.

The pipeline: **discover** a data source → **probe** its schema → **plan** a query in
plain language → **excavate** the exact approved query → **refine** the results →
**export** with provenance.

**Compliance features (v0.8.0–v0.11.0):**
- **IRB approval workflow** — plans can require explicit reviewer sign-off before any
  query executes; self-approval is blocked; EventBridge event fires on approval for audit
- **Team sharing** — `share_plan` lets plan owners grant colleagues access; `team_plans`
  lists all plans for a team ID
- **FERPA Guardrail preset** — blocks five student-data topic categories and SSN/student-ID
  regex patterns; enabled via `enable_ferpa_guardrail: true` CDK context
- **Cedar policy templates** — four pre-built templates: read-only, no-PII-export,
  approved-domains-only, and PHI-approved (with clearance + IRB + HITL requirements)
- **Compliance audit export** — SHA-256-hashed NDJSON audit records to S3 on demand;
  no raw data or PII in the export

**What it adds to Quick Suite:** Safe, auditable, policy-controlled queries against
raw institutional and research databases. The provenance chain every compliance office
needs. IRB and FERPA governance for sensitive research data.

---

## Scenario Library

End-to-end scenario YAMLs in `examples/` document complete workflows with real tool calls,
assertions, and poll intervals. Each can be run against deployed stacks via the E2E test suite.

| Scenario | Category | Stacks | Description |
|----------|----------|--------|-------------|
| `grant-portfolio` | institutional-analytics | claws + compute | Excavate sponsored program expenditures → burn rate analysis + NCE risk flagging |
| `network-coauthor` | institutional-analytics | claws + compute | Excavate publications table → co-authorship centrality + community detection |
| `course-evaluation-topics` | institutional-analytics | claws + compute | Excavate course evaluation text → LDA topic modeling |
| `student-retention-analysis` | institutional-analytics | claws + compute | Excavate cohort data → Kaplan-Meier survival analysis |
| `donor-giving-patterns` | institutional-analytics | claws + compute | Excavate giving history → K-Means donor segmentation |
| `netcdf-prophet-pipeline` | academic-research | compute | Ingest NetCDF climate data → Prophet 24-month forecast (chained profiles) |
| `pdf-sentiment-pipeline` | academic-research | compute | Ingest PDF text page by page → VADER sentiment scoring (chained profiles) |
| `enrollment-forecast` | compute-only | compute | Prophet enrollment forecast from IPEDS data |
| `donor-clustering` | compute-only | compute | K-Means clustering on alumni giving history |
| `grade-equity-analysis` | compute-only | compute | Equity gap analysis by demographic on grade distribution |

Run any scenario against deployed stacks:

```bash
AWS_PROFILE=aws python3 -m pytest tests/scenarios/test_scenarios.py -v -k "grant-portfolio"
```

---

## How the Pieces Connect

The four extensions aren't just independent add-ons — they form a pipeline:

```
Quick Suite conversation
        │
        ▼
AgentCore Gateway  ←  all tools register here
        │
        ├── qs-router  (which model should answer this?)
        │
        ├── qs-data    (where does the data live?)
        │       │  writes claws:// URI to ClawsLookupTable
        │       ▼
        ├── qs-claws   (query the data, enforce policies)
        │       │  produces run_id
        │       ▼
        └── qs-compute (analyze the results statistically)
```

The **claws:// URI** is the connector. When the Data extension loads a public RODA dataset,
it registers a `claws://roda-{slug}` entry. When Compute needs to analyze that data, it
uses that URI directly — no manual handoff, no copy-paste of dataset IDs. A full workflow
from "find data" to "run analysis" to "build dashboard" can happen in a single conversation.

---

## Example Conversations

These are the kinds of things a Quick Suite user can ask once these extensions are deployed.
None of these are possible with stock Quick Suite alone.

**"Pull the latest IPEDS graduation rate data and run a survival analysis comparing
time-to-degree across first-generation and continuing-generation students."**

> Quick Suite uses the Data extension to find and load the IPEDS dataset from RODA,
> then hands the `claws://` URI to Compute, which runs a Kaplan-Meier survival analysis
> and delivers the results as a new Quick Sight dataset. The whole thing takes about
> two minutes.

**"Look at our financial aid records for the 2024 cohort and flag any students with
missing FAFSA completion dates, broken out by demographic category."**

> clAWS checks the requesting user's Cedar policy (the financial aid team can query
> that table), generates SQL, has it validated, executes it against Athena, scans the
> results through Bedrock Guardrails for PII exposure, and exports the results with
> a full provenance chain. The compliance office gets a documented audit trail of every
> step.

**"I need to segment our alumni donor pool by giving history and identify which cluster
has the highest major gift potential."**

> The Data extension loads alumni giving history from institutional S3, Compute runs
> K-Means clustering, and the Router synthesizes a narrative summary of each cluster
> for the advancement office — using whatever LLM provider produces the best output
> for that type of analysis.

**"What are the enrollment trends for community college transfer students over the
last five years, and what does the forecast look like through 2029?"**

> IPEDS transfer enrollment data is pulled from RODA, Compute runs a Prophet time
> series forecast with the appropriate seasonality settings, and Quick Research
> synthesizes the findings into a narrative suitable for a provost's briefing.

---

## Deployment Model

These extensions are deployed **once at the institutional level** by a cloud or IT team,
then made available to users and groups through Quick Suite's standard sharing mechanism.
Individual users don't install anything — the tools simply appear in their Quick Suite
chat interface once an administrator has shared the integration with them.

The setup has three phases:

**1. Deploy the CDK stacks** — one time, into your institution's AWS account. This
creates the Lambda functions, the AgentCore Gateway, and all supporting infrastructure.
The four extensions share a single Gateway, so users see one coherent set of tools rather
than four separate integrations.

**2. Configure the MCP Actions** — in the Quick Suite admin console, create
an MCP Actions pointing to the AgentCore Gateway endpoint. This is the same
process as any other Quick Suite integration you've set up.

**3. Share with users and groups** — assign the integration to individuals, departments,
or your entire institution using Quick Suite's standard sharing controls. An IR analyst,
a faculty researcher, and a financial aid officer can all use the same integration with
different data access permissions — controlled by Cedar policies on the clAWS side, not
by deploying separate stacks.

Access control for sensitive data is handled by Cedar policies in clAWS, not by creating
separate deployments per group. You write one policy per department (IR can query
enrollment tables; financial aid can query aid records; advancement can load alumni data
from S3) and deploy them alongside the rest of the stack. Changing who can access what
is a policy update, not a redeployment.

See [`docs/deployment-guide.md`](docs/deployment-guide.md) for the complete walkthrough
from first CDK deploy to users seeing tools in their Quick Suite workspace.

## Getting Started

For the complete institutional setup walkthrough — including CDK deployment order,
AgentCore Gateway configuration, MCP Actions setup, and user/group sharing —
see **[`docs/deployment-guide.md`](docs/deployment-guide.md)**.

For component-specific configuration and developer documentation, see the individual repos:

- [quick-suite-router](https://github.com/scttfrdmn/quick-suite-router) — deploy first; provides the shared Gateway ID
- [quick-suite-data](https://github.com/scttfrdmn/quick-suite-data)
- [quick-suite-compute](https://github.com/scttfrdmn/quick-suite-compute)
- [quick-suite-claws](https://github.com/scttfrdmn/quick-suite-claws)

For pre-built Quick Flows workflow templates and the Quick Research integration guide,
see the rest of [`docs/`](docs/).

## Cost

At idle (no jobs running), all four extensions together cost roughly $10–15 per month in
AWS infrastructure. Costs scale with usage — a typical Compute job runs $0.01–$0.50
depending on profile and dataset size. clAWS Athena queries run at standard Athena pricing
($5 per TB scanned, with partition pruning typically reducing actual scans to pennies).

## License

Apache-2.0 — Copyright 2026 Scott Friedman
