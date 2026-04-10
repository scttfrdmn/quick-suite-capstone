# Quick Suite Extensions

Most universities already pay for Amazon Quick Suite — the $20–40/user/month
agentic AI workspace that bundles Quick Sight (BI), Quick Research (deep
research), Quick Flows (workflow automation), Quick Automate (process
optimization), and Quick Index (data discovery). It's a capable platform out
of the box: it can chat with your documents, build dashboards from data already
in Quick Sight, run deep research across the web, and automate workflows.

**But there are things it cannot do alone.** It can't reach into a raw Athena
database, can't pull from 500+ public research datasets on demand, can't run a
clustering analysis on 300,000 student records, can't query Snowflake or
Redshift natively, and has no way to enforce fine-grained data access policies
at the query level.

**These extensions close those gaps.** They turn an institution's existing
Quick Suite subscription into a full research and analytics platform — without
requiring a data engineer in the room every time someone has a question. For
universities evaluating AWS, the extensions make Quick Suite the anchor: a
single subscription that covers BI, deep research, workflow automation, *and*
the statistical analysis and governed data access that higher ed actually needs.

---

## What Changes With These Extensions

| Without extensions | With them |
|--------------------|-----------|
| Only sees data already loaded into Quick Sight | Searches and loads any of 500+ public research datasets, plus Snowflake, Redshift, and institutional S3 — on demand |
| No access to research literature or grant databases | Searches PubMed, bioRxiv, arXiv, Semantic Scholar, NIH Reporter, NSF Awards, IPEDS, Zenodo, and Figshare from the chat interface |
| Can't query a raw Athena table or execute analytical SQL | Plans and executes policy-gated queries against any approved data source, with Cedar + Guardrails enforcement |
| No statistical compute — charts only | Runs 42 analysis profiles across 12 categories: clustering, regression, forecasting, causal inference, IRT, survival analysis, and more |
| Uses one built-in LLM | Routes to the best available model (Bedrock, Anthropic, OpenAI, Gemini) per task, with automatic fallback and capability matching |
| No per-query access control beyond IAM | Cedar policies enforce who can query what at the query level; column-level filtering; IRB approval workflows |
| No chain-of-custody for exported data | Every export carries a provenance chain: who queried what, when, under which policy |
| Reactive only — answers what you ask | Proactive watches monitor for new grants, literature, compliance gaps, and accreditation evidence automatically |

The extensions work through **Amazon Bedrock AgentCore Gateway**, which acts as
a bridge between Quick Suite and these new capabilities. Quick Suite's agent
sees all the new tools the same way it sees its built-in ones — through
natural conversation.

---

## The Four Extensions

### Router — Multi-Provider LLM Routing
[github.com/scttfrdmn/quick-suite-router](https://github.com/scttfrdmn/quick-suite-router)

Quick Suite has one built-in language model. The Router gives it access to four
providers — Amazon Bedrock, Anthropic (Claude), OpenAI (GPT), and Google
(Gemini) — and intelligently routes each request to the best option based on
task type, required capabilities, context window needs, and provider
availability.

**Six tool endpoints:** `analyze`, `generate`, `research`, `summarize`, `code`,
and `extract` — each with provider-specific optimizations and automatic
fallback.

**Key capabilities:**
- **Capability routing** — match tasks to models by required capabilities
  (structured output, long context, vision) and context window budget
- **Structured extraction** — the `extract` tool pulls effect sizes, methods,
  confounds, open problems, and citations from scientific text; providers use
  native JSON mode
- **Grounding mode** — `research` with `grounding_mode: "strict"` returns
  sources, grounding coverage, and low-confidence claims for verifiable answers
- **PHI routing** — requests tagged `data_classification: "phi"` are silently
  restricted to Bedrock only; non-Bedrock providers never see PHI
- **Spend tracking** — per-department budget caps with a DynamoDB spend ledger;
  `query_spend` tool for finance teams; Cognito JWT-based authorization
- **Streaming** — SSE streaming for `generate` and `research` with guardrails
  applied to assembled output
- **Dry-run mode** — preview estimated cost, selected provider, and model
  before invoking
- **Per-user rate limiting** — Cognito JWT-based usage plans with configurable
  RPM and daily quotas
- **VPC isolation** — optional private deployment with no internet egress for
  regulated environments
- **Content audit logging** — SHA-256 hashes of prompts and responses for
  compliance review

All responses pass through Bedrock Guardrails regardless of which model
answered. Guardrail version is managed via SSM Parameter Store — update without
redeployment.

**What it adds to Quick Suite:** Choice of model without changing the
interface. Governance that follows the result regardless of where it came from.
Cost controls that prevent runaway spend.

---

### Data — Public, Institutional, and Research Data Access
[github.com/scttfrdmn/quick-suite-data](https://github.com/scttfrdmn/quick-suite-data)

Quick Suite only knows about data already loaded into Quick Sight. The Data
extension connects it to everything else.

**15 tool Lambdas across five source categories:**

| Category | Tools | What they access |
|----------|-------|-----------------|
| Public datasets | `roda_search`, `roda_load` | 500+ curated datasets from the Registry of Open Data on AWS (IPEDS, CDC, Census, NOAA, NIH, etc.) |
| Institutional | `s3_browse`, `s3_preview`, `s3_load` | Your S3 buckets — SIS exports, financial aid files, grant databases, alumni records |
| Data warehouses | `snowflake_browse`, `snowflake_preview`, `snowflake_query`, `redshift_browse`, `redshift_preview`, `redshift_query` | Parameterized read-only SQL against Snowflake and Redshift with mutation detection |
| Research literature | `pubmed_search`, `biorxiv_search`, `semantic_scholar_search`, `arxiv_search`, `reagent_search` | PubMed, bioRxiv/medRxiv, Semantic Scholar, arXiv, Addgene reagent catalog |
| Research funding | `ipeds_search`, `nih_reporter_search`, `nsf_awards_search`, `research_search` | IPEDS via Urban Institute API, NIH Reporter v2, NSF Award Search, Zenodo, Figshare |
| Cross-source | `federated_search` | Unified search across all 12+ registered source types with keyword scoring and data classification filtering |

**Data quality:** Preview responses include per-column quality metrics (null
percentage, estimated cardinality, duplicate row percentage). Non-native
formats (.nc, .h5, .pdf, .geojson) return a `suggested_profile` pointing to
the appropriate Compute ingest profile.

**Source registry:** A DynamoDB-backed registry of approved data sources.
clAWS `discover` queries it; Compute results write back to it. Data loaded
once is discoverable everywhere.

**Per-caller credentials:** Snowflake and Redshift tools accept per-caller
Secrets Manager ARNs, validated against a prefix allowlist — no shared service
account required.

**What it adds to Quick Suite:** On-demand access to public research datasets,
institutional data warehouses, and scientific literature — all from the chat
interface. No data engineer required.

---

### Compute — Ephemeral Analytics
[github.com/scttfrdmn/quick-suite-compute](https://github.com/scttfrdmn/quick-suite-compute)

Quick Suite can visualize data and generate text summaries, but it cannot run
statistics. The Compute extension brings **42 analysis profiles across 12
categories** to Quick Suite's chat interface:

| Category | Profiles | Examples |
|----------|---------|---------|
| Statistics | anova, chi-square | Grade disparity by section; FAFSA completion by demographic |
| Prediction/ML | regression-glm, regression-logistic, classification-random-forest | Graduation probability; donor lapse risk |
| Forecasting | forecast-prophet, change-detection, seasonality-decompose | Enrollment 3 years forward; trend breaks |
| Clustering | clustering-kmeans | Applicant yield segments; donor prospect groups |
| Text | text-topics, text-sentiment, text-similarity | Course evaluation themes; policy document tone |
| Anomaly | anomaly-isolation-forest | Irregular financial transactions; at-risk LMS engagement |
| Higher-Ed | cohort-flow, dfwi-analysis, equity-gap, peer-benchmark, retention-cohort, survival-kaplan-meier, intersectionality-equity, assessment-irt, financial-aid-effectiveness | IPEDS reporting; accreditation equity gaps; IRT psychometrics; aid band persistence analysis |
| Geospatial | geo-enrich, isochrone, spatial-aggregate | Census demographics by address; service area membership |
| Research | grant-portfolio, network-coauthor, causal-iv, causal-rd, causal-did, grant-pipeline, provenance-graph, power-analysis, anomaly-hypothesis, reproducibility-check | NCE risk; co-authorship centrality; 2SLS instrumental variables; regression discontinuity; difference-in-differences; literature-informed sample sizing; anomaly classification; reproducibility pre-flight |
| Ingest | ingest-netcdf, ingest-pdf-extract, ingest-geojson | Convert scientific files to tabular for further analysis |
| Custom | custom-python, custom-generated | Run your own RestrictedPython script or describe what you want in plain language |
| Transform | transform-spark | EMR Serverless for large-scale transforms |

**Seven tool Lambdas:** `compute_profiles` (list available), `compute_run`
(submit), `compute_status` (poll with cost tracking), `compute_history` (recent
jobs), `compute_cancel` (abort), `compute_snapshots` (named result sets),
`compute_compare` (diff two snapshots), `compute_schedule` (recurring jobs via
EventBridge Scheduler).

**Key capabilities:**
- **Profile chaining** — run `ingest-netcdf` → `forecast-prophet` in a single
  job; output of one feeds the next
- **Named snapshots** — save and compare results across time periods (schema
  diff + added/removed/unchanged row counts)
- **CSV/Excel export** — SUCCEEDED jobs include presigned URLs for CSV and XLSX
  downloads (24h TTL)
- **Results write-back** — completed jobs automatically register in the Data
  source registry, making results discoverable via `federated_search` and
  clAWS `discover`
- **Cross-stack budget enforcement** — checks both its own monthly budget and
  the Router spend ledger before submitting jobs
- **Peer cohort matching** — Carnegie class + enrollment + control type + Pell
  filtering with weighted scoring and 30-day cache
- **VPC and KMS** — optional private VPC deployment and customer-managed KMS
  encryption

**What it adds to Quick Suite:** Statistical analysis accessible through
conversation, with built-in budget controls, chained profiles, named snapshots,
scheduled jobs, and automatic results delivery to Quick Sight.

---

### clAWS — Policy-Gated Data Excavation and Proactive Intelligence
[github.com/scttfrdmn/quick-suite-claws](https://github.com/scttfrdmn/quick-suite-claws)

clAWS is for when you need to go deeper: run a precise analytical query against
a restricted Athena table, search an OpenSearch index, query PostgreSQL or
Redshift directly, or extract a specific slice of a large dataset — all with
documented evidence of what was accessed and why it was permitted.

**Two independent safety layers on every query:**
- **Cedar policies** — structural, deterministic rules evaluated at the Gateway
  boundary. "The financial aid team can read the FAFSA completion table but not
  the SSN column." Column-level access control.
- **Bedrock Guardrails** — semantic content scanning on query inputs and
  results. Catches what structural rules miss.

**The core pipeline:** **discover** → **probe** → **plan** → **excavate** →
**refine** → **export**

**Nine tool Lambdas + three internal Lambdas:**
- `discover` — find data sources in approved domains (Glue catalog + Data
  source registry)
- `probe` — inspect schema, sample rows, cost estimates with PII scanning
- `plan` — translate free-text objective to concrete query (with Guardrails
  validation); supports plan templates with `{{variable}}` placeholders
- `excavate` — execute the approved query; supports Athena, DynamoDB PartiQL,
  S3 Select, OpenSearch, PostgreSQL, and Redshift backends
- `refine` — deduplicate, rank, and summarize results with grounding guardrail
- `export` — materialize to S3/EventBridge with provenance chain and
  destination allowlist
- `team_plans` / `share_plan` — collaborative plan sharing within teams
- `instantiate_plan` — create concrete plans from templates by substituting
  variables

**Compliance and governance:**
- **IRB approval workflow** — plans can require explicit reviewer sign-off;
  self-approval blocked; EventBridge audit events on approval
- **FERPA Guardrail preset** — blocks five student-data categories + SSN/ID
  regex patterns
- **Cedar policy templates** — read-only, no-PII-export, approved-domains-only,
  PHI-approved (clearance + IRB + HITL)
- **HMAC-SHA-256 audit hashing** — keyed hashes in NDJSON audit records; no PII
  in exports
- **Per-principal budget caps** — SSM-based limits with monthly spend tracking
  and 402 enforcement

**Proactive intelligence watches:**
- `new_award` — monitors NIH Reporter or NSF Awards for grants matching a lab
  profile; semantic similarity scoring against a stored lab abstract
- `literature` — monitors PubMed/bioRxiv for papers matching a lab profile;
  per-paper relevance scoring with reagent/protocol classification
- `cross_discipline` — detects adjacent-field papers addressing open problems;
  loads gap lists from S3/SSM; qualifies on cross-field score and citation
  patterns
- `compliance` — evaluates rules for international sites, new data sources,
  subject counts, classification changes
- `accreditation` — evaluates evidence predicates against SACSCOC/HLC standards;
  surfaces gaps automatically

**Institutional memory:**
- `claws.remember` — append findings to versioned S3 NDJSON with ETag
  conditional writes; auto-registers as QuickSight dataset via Data extension
- `claws.recall` — filter stored records by date, severity, tags, or keyword
- Watch runners auto-remember findings by default; one-shot flow triggers
  create EventBridge schedules for Quick Flows automation

**What it adds to Quick Suite:** Safe, auditable, policy-controlled queries
against raw institutional and research databases. Proactive monitoring that
surfaces findings before anyone asks. The provenance chain every compliance
office needs.

---

## How the Pieces Work Together

The four extensions aren't independent add-ons — they form an integrated
platform where the whole is greater than the sum of the parts.

```
Quick Suite conversation
        │
        ▼
AgentCore Gateway  ←  all tools register here
        │
        ├── Router   routes to best model; tracks spend; enforces PHI boundaries
        │     │
        │     │  spend ledger ──→ Compute reads before submitting jobs
        │     │  extract/summarize ──→ clAWS watches call for scoring + drafting
        │     │
        ├── Data     finds and loads data from any source
        │     │
        │     │  source registry ──→ clAWS discover queries it
        │     │  claws:// URIs ──→ Compute resolves them to datasets
        │     │  memory registration ──→ clAWS memory appears in Quick Sight
        │     │
        ├── clAWS    queries data under policy; remembers findings; watches for changes
        │     │
        │     │  excavation results ──→ Compute analyzes them
        │     │  memory ──→ Data registers as QuickSight dataset
        │     │  watch findings ──→ Router summarizes; flow triggers automate response
        │     │
        └── Compute  runs analysis; writes results back to registry
              │
              results ──→ Data source registry ──→ discoverable via federated_search
              provenance graph ──→ reads from own history table
```

**Concrete cross-stack flows:**

1. **Data → clAWS → Compute:** Load IPEDS enrollment data → clAWS discovers it
   in the registry → Compute runs survival analysis on the loaded dataset

2. **clAWS → Router → Memory → Quick Flows:** A literature watch fires → Router
   `summarize` drafts a briefing → `remember` stores the finding → flow trigger
   sends it to the PI's inbox next morning

3. **Compute → Data Registry → clAWS:** A grant-portfolio analysis completes →
   results auto-register in the Data source registry → clAWS `discover` finds
   them for a follow-up compliance query

4. **Router → Compute:** Router's spend ledger tracks department costs →
   Compute checks the ledger before submitting expensive jobs → prevents
   budget overruns across both model inference and compute

---

## Institutional Academic Analysis

For provosts, deans, enrollment managers, and academic affairs teams — analysis
that supports academic program decisions, student success, and accreditation.

**What's available:** Nine higher-ed compute profiles purpose-built for
academic analysis, plus clAWS data excavation for institutional data sources
and the Data extension for IPEDS benchmarking.

### Retention and Student Success

A retention analyst asks: *"Show me first-to-second year retention rates for
the last five cohorts, broken out by Pell status and first-generation status."*

> clAWS discovers the student cohort table in Glue, probes the schema, plans a
> query scoped by Cedar policy (the analyst can see retention data but not
> financial details), excavates the records, and hands them to Compute's
> `retention-cohort` profile. The results land as a Quick Sight dataset with
> cohort-by-cohort rates. The analyst then runs `survival-kaplan-meier` on the
> same data to see time-to-degree curves by subgroup.

### Equity and Accreditation

An IR director preparing for SACSCOC review asks: *"Run an equity gap analysis
on our grade distributions by race/ethnicity, Pell, and first-gen — and flag
any courses with DFWI rates above 30%."*

> Compute runs `equity-gap` on grade data (with institutional benchmarks) and
> `dfwi-analysis` on the same dataset. The `intersectionality-equity` profile
> cross-tabs outcomes by two demographic dimensions simultaneously with
> Disparate Impact ratios and cell suppression for small n. clAWS's
> accreditation watch can be configured to run these automatically each term
> and surface gaps before the self-study deadline.

### Enrollment Planning

An enrollment VP asks: *"What does our enrollment look like through 2029, and
how do transfer students compare to first-time freshmen?"*

> Data loads IPEDS enrollment history from RODA. Compute runs
> `forecast-prophet` with appropriate seasonality. The Router's `research` tool
> with `grounding_mode: "strict"` synthesizes findings with source citations
> suitable for a board presentation. `peer-benchmark` compares your trajectory
> against Carnegie peers.

### Assessment and Psychometrics

An assessment director asks: *"Run IRT analysis on our general education exam
to identify which items discriminate well and which need revision."*

> Compute's `assessment-irt` profile fits a 2PL model, returning item
> difficulty and discrimination parameters, person ability estimates, and item
> information curves. Minimum thresholds (5 items, 100 respondents) are
> enforced automatically.

---

## Institutional Research Administration

For research offices, sponsored programs, compliance teams, and grants
managers — analysis that supports the research enterprise infrastructure.

**What's available:** Ten research compute profiles, clAWS proactive watches,
per-principal budget controls, and integration with NIH Reporter, NSF Awards,
and institutional data warehouses.

### Grant Portfolio Management

A sponsored programs director asks: *"Show me all active awards with burn rates
that suggest we'll need a no-cost extension, and flag any with unusual spending
patterns."*

> clAWS discovers the sponsored program expenditure table, excavates award-level
> spending data, and Compute runs `grant-portfolio` (burn rate analysis + NCE
> risk flagging) followed by `anomaly-isolation-forest` on the same data. The
> `grant-pipeline` profile adds PI health scores (active grants, continuity,
> sponsor diversity) and NCE timing risk (awards ending within 60 days with no
> overlap).

### Compliance Monitoring

A compliance officer asks: *"Set up continuous monitoring for our IRB-approved
studies — alert me if any study adds international sites, changes data
classification, or exceeds the approved subject count."*

> clAWS's `compliance` watch evaluates four rule types (international site,
> new data source, subject count, classification change) against the configured
> ruleset. When a rule triggers, the Router `summarize` drafts amendment
> language, `remember` stores the finding, and a flow trigger sends it to the
> compliance inbox. The HMAC-SHA-256 audit trail provides evidence for federal
> auditors.

### Accreditation Evidence

An accreditation coordinator asks: *"Are we meeting our SACSCOC standards for
student achievement? Check retention, completion, and equity metrics against our
stated thresholds."*

> clAWS's `accreditation` watch evaluates evidence predicates per
> SACSCOC/HLC standard against current data. Gaps surface automatically with
> the specific standard, the threshold, and the current value. Results
> auto-remember for longitudinal tracking. The provost sees a Quick Sight
> dashboard backed by the memory dataset.

### Research Network Intelligence

A VP for Research asks: *"Map our co-authorship network and identify which
departments are isolated — I want to target seed funding for cross-disciplinary
collaboration."*

> clAWS excavates the publications table. Compute's `network-coauthor` profile
> builds the graph with degree centrality, betweenness centrality, and Louvain
> community detection. The results show which faculty are bridges between
> clusters and which departments have no co-authorship ties outside their unit.

---

## Faculty Domain Research

For faculty, postdocs, and graduate students doing actual science — hypothesis
generation, experimental design, literature monitoring, and data analysis
workflows that support the research cycle.

**What's available:** Science-specific compute profiles (causal inference, power
analysis, reproducibility checking, anomaly-to-hypothesis), literature search
across seven databases, proactive watches for new publications and grants, and
structured extraction from scientific text.

### Literature Monitoring

A PI asks: *"Watch PubMed and bioRxiv for papers relevant to my CRISPR
delivery work — especially anything that mentions our reagents or protocols —
and brief me weekly."*

> clAWS's `literature` watch monitors PubMed and bioRxiv rows, scoring each
> paper for relevance against the PI's lab profile via Router `summarize`.
> Papers that reference specific reagents or protocols are classified by
> `relevance_type` (reagent/protocol/methodology) with appropriate validation
> steps. Findings auto-remember to the PI's memory store and trigger a weekly
> digest flow.

### Cross-Discipline Discovery

A computational biologist asks: *"Are there papers in materials science or
chemical engineering that address the protein folding stability problems on my
open problems list?"*

> clAWS's `cross_discipline` watch loads the PI's gap list from S3 (generated
> by Router `extract` with `open_problems` type), searches for papers in
> adjacent fields via Router `research` with `grounding_mode: "strict"`, and
> qualifies on cross-field score and citation patterns. Papers from outside the
> primary field that cite into it — but aren't yet cited back — surface as
> novel connections.

### Experimental Design

A graduate student starting a clinical trial asks: *"Based on the effect sizes
reported in these three PubMed papers, what sample size do I need for 80% power
to detect a treatment effect?"*

> Compute's `power-analysis` profile cross-references the cited PubMed IDs
> via Router `extract` to pull reported effect sizes, computes Cohen's d, and
> runs scipy power curves from n=2 to n=100. The output includes a confound
> checklist drawn from the cited papers' methods sections. If the Router is
> unavailable, it falls back to manually specified effect sizes.

### Causal Inference

A health policy researcher asks: *"Did the Medicaid expansion actually improve
health outcomes in expansion states, controlling for pre-existing trends?"*

> Compute's `causal-did` profile runs OLS difference-in-differences with
> parallel trends testing in the pre-period, event study coefficients per time
> period, and placebo pre-period tests. For studies with a sharp eligibility
> cutoff, `causal-rd` provides regression discontinuity with IK optimal
> bandwidth and McCrary manipulation testing. For instrumental variables
> designs, `causal-iv` runs 2SLS with first-stage F-statistics and weak
> instrument warnings.

### Grant Discovery

A junior faculty member asks: *"Alert me when NIH or NSF posts new awards in
computational genomics — especially anything at institutions similar to ours."*

> clAWS's `new_award` watch executes a locked plan against NIH Reporter and
> NSF Awards, scores award abstracts for semantic similarity against the
> faculty member's lab profile abstract stored in SSM, and only fires
> notifications for awards above the similarity threshold. Findings include
> PI names, award amounts, and abstract text.

### Reproducibility

A methods-focused PI asks: *"Re-run the analysis script from our 2024 paper
against the deposited dataset and tell me if the results still match within
tolerance."*

> Compute's `reproducibility-check` profile re-executes the analysis script in
> a RestrictedPython sandbox against the deposited data, compares outputs to the
> manuscript's reported results with configurable tolerance, and integrates with
> `provenance-graph` to verify the exact script version. The output flags any
> values outside tolerance with the expected vs. observed difference.

---

## Scenario Library

End-to-end scenario YAMLs in `examples/` document complete workflows with real
tool calls, assertions, and poll intervals. Each can be run against deployed
stacks via the E2E test suite.

**Institutional Analytics:**

| Scenario | Stacks | Description |
|----------|--------|-------------|
| `grant-portfolio` | claws + compute | Excavate sponsored program expenditures → burn rate + NCE risk |
| `network-coauthor` | claws + compute | Excavate publications → co-authorship centrality + community detection |
| `course-eval-topics` | claws + compute | Excavate evaluation text → LDA topic modeling by department |
| `student-retention` | claws + compute | Excavate cohort data → Kaplan-Meier survival analysis |
| `donor-segmentation` | claws + compute | Excavate giving history → K-Means donor segments |
| `grant-anomaly-detection` | claws + compute | Excavate expenditures → isolation forest for irregular burn rates |
| `equity-gap` | compute | Equity gap analysis by demographic on grade distributions |
| `dfwi-analysis` | compute | DFWI rate computation for accreditation + equity review |
| `cohort-flow` | compute | Admissions funnel conversion rates by stage |
| `enrollment-forecast` | compute | Prophet enrollment forecast from IPEDS data |
| `peer-benchmarking` | compute | Linear regression benchmark against Carnegie peers |

**Academic Research:**

| Scenario | Stacks | Description |
|----------|--------|-------------|
| `noaa-climate-trends` | data + compute | RODA NOAA temperature data → Prophet 24-month forecast |
| `netcdf-prophet-pipeline` | compute | Ingest NetCDF → chain into Prophet forecast |
| `pdf-sentiment-pipeline` | compute | Ingest PDF → chain into VADER sentiment scoring per page |
| `gbif-species-range-shift` | data + compute | RODA GBIF occurrence data → Spearman correlation for latitude shift |
| `openaq-pollution-spikes` | data + compute | RODA OpenAQ data → isolation forest for pollution spike events |
| `1000genomes-population-structure` | data + compute | RODA 1000 Genomes → K-means clustering on population metadata |
| `cdc-health-disparities` | data + compute + router | RODA CDC PLACES → logistic regression + Router narrative for grant application |

Run any scenario:
```bash
AWS_PROFILE=aws python3 -m pytest tests/scenarios/test_scenarios.py -v -k "grant-portfolio"
```

---

## Deployment Model

These extensions are deployed **once at the institutional level** by a cloud or
IT team, then made available to users and groups through Quick Suite's standard
sharing mechanism. Individual users don't install anything — the tools appear
in their Quick Suite chat interface once an administrator shares the
integration.

**1. Deploy the CDK stacks** — one time, into your institution's AWS account.
The four extensions share a single AgentCore Gateway.

**2. Configure MCP Actions** — in the Quick Suite admin console, create an MCP
Action pointing to the Gateway endpoint.

**3. Share with users and groups** — assign via Quick Suite's standard sharing
controls. An IR analyst, a faculty researcher, and a financial aid officer all
use the same integration with different data access permissions — controlled by
Cedar policies in clAWS, not separate stacks.

Access control for sensitive data is a policy update, not a redeployment.

See [`docs/deployment-guide.md`](docs/deployment-guide.md) for the complete
walkthrough.

## Getting Started

- [quick-suite-router](https://github.com/scttfrdmn/quick-suite-router) — deploy first; provides the shared Gateway ID
- [quick-suite-data](https://github.com/scttfrdmn/quick-suite-data)
- [quick-suite-compute](https://github.com/scttfrdmn/quick-suite-compute)
- [quick-suite-claws](https://github.com/scttfrdmn/quick-suite-claws)

## Documentation

| Document | What it covers |
|----------|---------------|
| [`docs/kiro-integration.md`](docs/kiro-integration.md) | Using Quick Suite Extensions in AWS Kiro (MCP setup, per-tool and cross-tool examples) |
| [`docs/deployment-guide.md`](docs/deployment-guide.md) | CDK deploy order, AgentCore Gateway config, MCP Actions setup, user/group sharing |
| [`docs/quick-research-integration.md`](docs/quick-research-integration.md) | Using Quick Research with compute and clAWS results |
| [`docs/institutional-memory.md`](docs/institutional-memory.md) | Persistent memory layer — S3 + QuickSight, the T+x push pattern, setup |
| [`docs/proactive-intelligence-roadmap.md`](docs/proactive-intelligence-roadmap.md) | Strategic roadmap — reactive to proactive platform shift |
| [`docs/proactive-intelligence-science.md`](docs/proactive-intelligence-science.md) | Roadmap extension — proactive tools for experimental science |
| [`docs/prompts/ir-analyst.md`](docs/prompts/ir-analyst.md) | Example prompts for IR analysts |
| [`docs/prompts/faculty-researcher.md`](docs/prompts/faculty-researcher.md) | Example prompts for faculty researchers |
| [`docs/prompts/research-computing.md`](docs/prompts/research-computing.md) | Example prompts for research computing staff |
| [`docs/prompts/compliance-officer.md`](docs/prompts/compliance-officer.md) | Example prompts for compliance officers |
| [`docs/prompts/advancement-officer.md`](docs/prompts/advancement-officer.md) | Example prompts for advancement officers |

## Platform Roadmap

**[Proactive Intelligence Roadmap](docs/proactive-intelligence-roadmap.md)** —
The strategic shift from reactive tools to proactive intelligence. Eight
high-leverage ideas across higher-ed administration and research administration.

**[Proactive Intelligence: The Science Itself](docs/proactive-intelligence-science.md)** —
Extends the roadmap into experimental science: Anomaly-to-Hypothesis Engine,
Experimental Design Critic, Reproducibility Pre-flight, Living Literature
Review, and Cross-Discipline Signal Detector.

## Cost

At idle, all four extensions cost roughly $10–15/month. Compute jobs run
$0.01–$0.50 depending on profile and dataset size. Athena queries at standard
$5/TB pricing with partition pruning typically reducing scans to pennies.

## License

Apache-2.0 — Copyright 2026 Scott Friedman
