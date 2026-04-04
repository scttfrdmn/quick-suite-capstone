# CLAUDE.md — Quick Suite Extensions Monorepo

## What Is This

Four independent CDK projects that extend Amazon Quick Suite through
Bedrock AgentCore Gateway. All tools surface as MCP tools in AgentCore
Gateway. Quick Suite's built-in agent orchestration decides which tools
to call — the individual projects don't orchestrate each other.

**Product terminology (get this right):**

- **Amazon Quick Suite** — the umbrella agentic AI workspace. Combines
  Quick Sight (BI), Quick Research (deep research), Quick Flows (workflow
  automation), Quick Automate (process optimization), and Quick Index
  (data discovery). NOT just QuickSight renamed — a broader agentic
  platform. $20/user/month (Professional) and $40/user/month (Enterprise).

- **Quick Sight** — the BI and visualization capability WITHIN Quick Suite
  (formerly standalone "Amazon QuickSight"). Dashboards, SPICE, datasets,
  analyses. The boto3 client is still `boto3.client('quicksight')` and API
  actions are still `quicksight:CreateDataSet` etc. Use "Quick Sight" in
  user-facing text for the BI capability; "Quick Suite" for the platform.

- **Amazon Bedrock AgentCore** — the agentic platform for building,
  deploying, and operating agents. NOT called "AgentCore API."

- **AgentCore Gateway** — component within Bedrock AgentCore that serves
  as the MCP tool server. Converts APIs and Lambda functions into
  MCP-compatible tools. Handles auth, routing, semantic search.

- **MCP Actions** — how Quick Suite connects to external tools.
  Quick Suite → MCP Actions → AgentCore Gateway → Targets.

```
~/src/quick-suite-capstone/
├── CLAUDE.md                        ← you are here
├── README.md
├── quick-suite-router/              # LLM multi-provider routing — GitHub: quick-suite-router
├── quick-suite-data/                # Public + institutional data access — GitHub: quick-suite-data
├── quick-suite-compute/             # Ephemeral analytics compute — GitHub: quick-suite-compute
└── quick-suite-claws/               # Policy-gated data excavation tool plane — GitHub: quick-suite-claws
```

## Target Architecture

```
Amazon Quick Suite (Chat Agent / Quick Research / Quick Flows)
    │
    │  MCP Actions
    ▼
Bedrock AgentCore Gateway (MCP server, single Gateway, OAuth via Cognito)
    │
    │  Discovers tools from registered targets
    │  Handles auth, tool routing, semantic search
    │
    ├── OpenAPI Target: Model Router (API Gateway backend)
    │   └── /tools/{analyze,generate,research,summarize,code}
    │       → Router Lambda → Provider Lambdas (Bedrock/Anthropic/OpenAI/Gemini)
    │
    ├── Lambda Targets: Open Data
    │   ├── roda_search      — search 500+ public datasets from RODA
    │   ├── roda_load        — load public dataset into Quick Sight
    │   ├── s3_browse        — browse configured institutional S3 buckets
    │   ├── s3_preview       — sample rows + schema from S3 path
    │   └── s3_load          — register S3 data as Quick Sight data source
    │
    ├── Lambda Targets: Compute
    │   ├── compute_profiles — list available analysis types
    │   ├── compute_run      — match intent to profile, execute analysis
    │   └── compute_status   — check job progress, surface cost/duration
    │
    └── OpenAPI Target: clAWS (API Gateway backend)
        └── /tools/{discover,probe,plan,excavate,refine,export}
            → Policy-gated data excavation (Athena/OpenSearch/S3/MCP)
            Cedar policies + Bedrock Guardrails enforcement
```

**AgentCore Gateway is the orchestration layer, not the model router.**
The Gateway discovers all tools, Quick Suite's agent picks which to call,
and the Gateway dispatches to the correct backend. The model router is
one peer among several tool sets.

**All data and compute Lambdas are AgentCore Gateway Lambda targets.**
- No API Gateway needed — AgentCore Gateway invokes Lambdas directly via
  IAM execution role
- Lambda handlers receive tool arguments as the event dict
- Lambda handlers return plain JSON dicts
- Tool name arrives prefixed: `${target_name}___${tool_name}`
  (strip using `___` delimiter from `context.client_context.custom['bedrockAgentCoreToolName']`)
- The model router is the exception: OpenAPI target with its own API Gateway

## AgentCore Lambda Target Handler Pattern

From the Bedrock AgentCore docs:

```python
def handler(event, context):
    """
    AgentCore Gateway Lambda target handler.

    event: dict — tool arguments passed directly (NOT API Gateway envelope)
    context.client_context.custom contains:
      - bedrockAgentCoreToolName: "${target_name}___${tool_name}"
      - bedrockAgentCoreGatewayId
      - bedrockAgentCoreTargetId
      - bedrockAgentCoreAwsRequestId
      - bedrockAgentCoreMcpMessageId
    """
    delimiter = "___"
    raw_name = context.client_context.custom['bedrockAgentCoreToolName']
    tool_name = raw_name[raw_name.index(delimiter) + len(delimiter):]

    query = event.get('query', '')
    return {'count': 3, 'datasets': [...]}
```

## Project Status

### quick-suite-router ✅ v0.8.0

GitHub: [scttfrdmn/quick-suite-router](https://github.com/scttfrdmn/quick-suite-router)

Python CDK. Five tool endpoints (`analyze`, `generate`, `research`,
`summarize`, `code`). Four providers: Bedrock, Anthropic direct, OpenAI
direct, Google Gemini direct.

**What's built:**
- Provider routing + fallback (config-driven preference lists per tool)
- `apply_guardrail_safe()` — fail-closed Bedrock Guardrails wrapper on all external provider calls; emits `GuardrailError` CW metric on failure
- `GuardrailApplied` CloudWatch metric; Guardrail Coverage dashboard widget
- Multi-turn conversation history: JSON list in `context` field prepended as native messages (Anthropic/OpenAI) or `contents` array with role mapping (Gemini)
- Department overrides: per-department provider preference lists in routing config
- DynamoDB response cache (configurable TTL, temperature ≤ 0.3 only)
- Cognito OAuth client_credentials for AgentCore Gateway
- CloudWatch dashboard with per-provider token/latency/guardrail metrics
- SSE streaming for `generate` and `research` tools (`stream: true` flag); buffered-streaming pattern returns `chunks` list + assembled `content`; all four providers supported; guardrails applied to assembled text
- Spend ledger DynamoDB table + `query_spend` AgentCore Lambda target; per-department budget cap enforcement (HTTP 402 on breach); `compute_cost_usd()` price table
- VPC isolation: `enable_vpc` CDK context flag places all Lambdas in a private VPC with no internet egress; Gateway endpoints for S3/DynamoDB; Interface endpoints for Secrets Manager, Lambda, CloudWatch, X-Ray, Bedrock
- PHI routing: `data_classification: "phi"` on any request silently restricts the provider candidate set to Bedrock only; non-Bedrock providers never receive PHI; returns 503 if no Bedrock available
- `docs/compliance.md`: HIPAA-ready deployment guide (VPC walkthrough, PHI tagging, CloudTrail, Guardrail hardening for healthcare)
- Full test suite (166 unit tests); cfn-lint + CDK synth in PR-blocking CI job

---

### quick-suite-data ✅ v0.7.0

GitHub: [scttfrdmn/quick-suite-data](https://github.com/scttfrdmn/quick-suite-data)

Five original AgentCore Lambda tools + five new v0.6.0 tools + internal Lambdas.

**Tool Lambdas:**
- `roda_search` — tag-based GSI query + keyword ranking + `exclude_deprecated` filter + pagination; `quality_score` (freshness/schema_completeness/last_verified) on every result
- `roda_load` (dataset-loader) — load RODA public dataset → Quick Sight dataset; writes `ClawsLookupTable`
- `s3_browse` — browse configured institutional S3 sources; reads from `qs-data-source-registry` when `use_source_registry=true`
- `s3_preview` — sample rows + schema inference from S3 file
- `s3_load` — register S3 path as Quick Sight data source; multi-prefix support; writes `ClawsLookupTable`
- `snowflake_browse` — list tables in a Snowflake data source (SQL API v2, no vendor SDK)
- `snowflake_preview` — sample rows + schema from a Snowflake table
- `redshift_browse` — list tables in a Redshift Serverless workgroup (Redshift Data API)
- `redshift_preview` — sample rows + schema from a Redshift table
- `federated_search` — unified search across all registered source types (roda/s3/snowflake/redshift); keyword scoring; `data_classification_filter`; `skipped_sources`

**Internal Lambdas:**
- `catalog-sync` — syncs RODA NDJSON catalog into DynamoDB daily (+ SNS real-time)
- `catalog-quality-check` — weekly scan; flags stale/unreachable datasets; writes `last_verified` + `quality_score` to catalog items; emits `StaleDatasets`/`UnreachableDatasets` CW metrics
- `claws-resolver` — resolves `claws://` source URIs to Quick Sight dataset IDs via `ClawsLookupTable`
- `register-source` — writes entries to `qs-data-source-registry` DynamoDB table

**ClawsLookupTable:** DynamoDB table (`source_id` PK → `dataset_id`). Written by `roda_load` and `s3_load`. Read by `claws-resolver`. Enables clAWS bridge between Open Data and Compute.

**Source Registry:** `qs-data-source-registry` DynamoDB table. SSM param `/quick-suite/data/source-registry-arn` for clAWS catalog-aware discover integration (v0.10.0).

Full test suite (192 unit tests; moto + Substrate).

---

### quick-suite-claws ✅ v0.11.0

GitHub: [scttfrdmn/quick-suite-claws](https://github.com/scttfrdmn/quick-suite-claws)

Eight AgentCore tool Lambdas + two internal Lambdas + Cedar policies + Bedrock Guardrail configs + CDK stacks.

**Tool Lambdas:**
- `discover` — find data sources in approved domains (Glue catalog search + `registry` domain queries `qs-data-source-registry`)
- `probe` — inspect schema, sample rows, cost estimates; PII scan on samples
- `plan` — translate free-text objective → concrete query (LLM + Guardrails); stores `team_id`, `created_by`, and `status` (`ready` or `pending_approval` when `requires_irb: true`)
- `excavate` — execute exact query from plan; blocks with `pending_approval` response when plan requires IRB; principal must be owner or in `shared_with`
- `refine` — dedupe, rank, summarize results with grounding guardrail
- `export` — materialize to S3/EventBridge with provenance chain
- `team_plans` — list all plans for a given `team_id` (read-only summaries)
- `share_plan` — owner grants read/excavate access to other principals via `shared_with` list

**Internal Lambdas (not AgentCore tools):**
- `approve_plan` — IRB reviewer approves a `pending_approval` plan; checks `CLAWS_IRB_APPROVERS` allowlist; emits `claws.irb / PlanApproved` EventBridge event; blocks self-approval
- `audit_export` — scans CloudWatch Logs for audit records in a date range; writes NDJSON to S3 with SHA-256-hashed inputs/outputs (no PII); fields: `principal`, `tool`, `inputs_hash`, `outputs_hash`, `cost_usd`, `guardrail_trace`, `timestamp`

**v0.11.0 compliance features:**
- IRB workflow: `requires_irb: true` on plan → `status: pending_approval`; `excavate` gates on status; `approve_plan` Lambda + `plan.approve` Cedar action (irb_approver role, no self-approval)
- FERPA Guardrail preset: `guardrails/ferpa/ferpa_guardrail.json`; five denied topic categories; SSN + student ID regex patterns; deploy with CDK context `enable_ferpa_guardrail: true`
- Cedar policy templates: `policies/templates/{read-only,no-pii-export,approved-domains-only,phi-approved}.cedar`

**Safety layers (two independent):**
- Cedar (AgentCore Policy) — structural/deterministic at Gateway boundary
- Bedrock Guardrails — semantic/content at LLM I/O and data paths via `ApplyGuardrail` API

**Core principle:** LLM reasoning never happens inside a tool. `plan` is the only tool with free-text input; `excavate` takes the concrete plan verbatim.

Full test suite (247 tests: Substrate integration + pure unit). MCP executor for extensibility. All four roadmap themes complete.

---

### quick-suite-compute ✅ v0.12.0

GitHub: [scttfrdmn/quick-suite-compute](https://github.com/scttfrdmn/quick-suite-compute)

Seven AgentCore Lambda tools + Step Functions workflow + 31 analysis profiles across 11 categories.

**Tool Lambdas:**
- `compute_profiles` — list available profiles with parameters, cost, and duration estimates
- `compute_run` — validate params against profile schema, check monthly budget, start Step Functions execution; returns `estimated_cost_usd` + `estimated_duration_seconds` pre-submission; accepts `result_label` (snapshot) and `chain_profile_id` (profile composition); pre-checks cross-stack `qs-router-spend` table for department budget cap (Issue #23)
- `compute_status` — poll status; SUCCEEDED response enriched with `actual_cost_usd`, `duration_seconds`, `profile_id`; RUNNING response includes `cost_usd_so_far` from HistoryTable (Issue #24); shows `step: "profile_2"` for chained jobs
- `compute_history` — list recent jobs for a user
- `compute_cancel` — abort a running job
- `compute_snapshots` — list a user's named result snapshots sorted by completion time
- `compute_compare` — diff two named snapshots: added/removed/unchanged row counts + schema diff

**Step Functions workflow:** CheckBudget → ExtractDataset → RouteCompute (Lambda or EMR Serverless) → DeliverResults → RecordSpend → NotifyUser → AuditLog

**Audit log (Issue #28):** Every terminal path (SUCCEEDED, FAILED) ends with `audit-log` Lambda writing `s3://compute-results/audit/{year}/{month}/{job_id}.json`. Fields: `job_id`, `profile_id`, `user_arn`, `dataset_uri`, `params`, `result_uri`, `cost_usd`, `duration_seconds`, `status`, `timestamp`. URIs only — no PII.

**VPC support (Issue #26):** `enable_vpc=true` CDK context flag places all SFN Lambda steps in an isolated-subnet VPC with S3 Gateway endpoint.

**KMS encryption (Issue #27):** `enable_kms=true` CDK context flag encrypts HistoryTable and compute-results bucket with customer-managed KMS keys.

**clAWS URI support in extract Lambda:** `claws://roda-noaa-ghcn` → invoke `CLAWS_RESOLVER_ARN` Lambda → get `dataset_id` → extract via Quick Sight path. Wired via `claws_resolver_arn` CDK context var.

**Snapshots table:** `qs-compute-snapshots` DynamoDB table (PK: `user_arn`, SK: `label`). Written by `record-spend` when `result_label` is set. Read by `compute_snapshots` and `compute_compare`.

**Router spend integration (Issue #23):** `compute_run` reads `qs-router-spend` (the quick-suite-router's spend ledger) via `ROUTER_SPEND_TABLE` env var (set from `router_spend_table_arn` CDK context); blocks jobs if department cumulative spend + estimated cost exceeds `MONTHLY_BUDGET_USD`; fails open on AWS errors.

**31 Analysis Profiles (Lambda unless noted):**
Statistics: anova, chi-square
Prediction/ML: regression-glm, regression-logistic, classification-random-forest
Forecasting: forecast-prophet, change-detection, seasonality-decompose
Clustering: clustering-kmeans
Text: text-topics, text-sentiment, text-similarity
Anomaly: anomaly-isolation-forest
Higher-Ed: cohort-flow, dfwi-analysis, equity-gap, peer-benchmark, retention-cohort, survival-kaplan-meier
Geospatial: geo-enrich (Census API), isochrone, spatial-aggregate
Exploration: explore-correlations
Research: grant-portfolio, network-coauthor
Ingest: ingest-netcdf, ingest-pdf-extract, ingest-geojson
Custom: custom-python (RestrictedPython sandbox), custom-generated (LLM-generated code)
Transform: transform-spark (EMR Serverless)

**Dashboard:** Per-profile Cost (USD/24h), Duration (p99), and Cumulative Cost (30d SUM) graph widgets generated from `config/profiles/*.json`.

Full test suite (421 unit tests); Substrate integration in CI.

---

## Conventions

- **Python CDK.** Entry point: `app.py`.
- **Python 3.12 Lambdas.** `boto3` + stdlib. No vendor SDKs.
- **AgentCore Lambda targets return plain dicts.**
- **Quick Sight API calls** use `boto3.client('quicksight')` — API namespace.
  User-facing text: "Quick Sight" (BI) or "Quick Suite" (platform).
- **Structured JSON logging** at INFO level.
- **Apache 2.0.**

### Naming

Repos/local dirs: `quick-suite-{router,data,compute,claws}` (GitHub and local match)
CDK stacks: `QuickSuiteRouter`, `QuickSuiteData`, `QuickSuiteCompute`, `QuickSuiteClaws`
Lambda prefix: `qs-router-`, `qs-data-`, `qs-compute-`, `qs-claws-`
DynamoDB prefix: `qs-`
SSM prefix: `/quick-suite/`

## Project Tracking

Work is tracked in GitHub — not in local files. Do not add TODO lists or task
tracking to CLAUDE.md files or create TODO.md files.

- **Capstone (suite):** https://github.com/scttfrdmn/quick-suite-capstone/issues
- **Model Router:** https://github.com/scttfrdmn/quick-suite-router/issues
- **Open Data:** https://github.com/scttfrdmn/quick-suite-data/issues
- **Compute:** https://github.com/scttfrdmn/quick-suite-compute/issues
- **clAWS:** https://github.com/scttfrdmn/quick-suite-claws/issues

Each sub-project has its own milestones, labels, and project board.
All release planning happens via milestones. Changelogs follow keepachangelog,
versions follow semver 2.0.

## Scenario Tests (`tests/scenarios/`)

Cross-stack E2E tests driven by `examples/**/scenario.yaml` files. Each scenario
invokes real deployed Lambda functions and asserts on the responses.

**Run:**
```bash
AWS_PROFILE=aws python3 -m pytest tests/scenarios/test_scenarios.py -v
```

**Region:** `QS_SCENARIO_REGION` defaults to `us-west-2` (where data/compute stacks
live). Router and claws always resolve to `us-east-1` via per-stack overrides in the
runner — do not change this.

**Skips vs failures:** A skip means a required stack is not deployed (expected in CI
without full infra). A failure means the pipeline itself is broken.

**Scenario authoring rules:**

1. **Never use `roda_load` as a pipeline step.** It creates persistent QuickSight
   resources that need cleanup. Use `source_uri: "s3://..."` directly in `compute_run`.

2. **Probe before plan.** `plan` reads from a schema cache populated by `probe`.
   Without probe, plan generates SQL with no column context.

3. **Compute profile enums are lowercase:** `method: lda` not `method: LDA`.
   The compute Lambda validates strictly and returns an error immediately on mismatch.

4. **clAWS field names are exact — wrong names silently produce empty results:**
   - discover input: `query:` (not `keywords:`), `scope: {domains: [...]}` (not top-level)
   - discover output: `sources[].id` (not `sources[].source_id`)
   - excavate needs all four fields: `plan_id`, `source_id`, `query`, `query_type`
   - Plan query path: `plan.steps.0.input.query` (nested under `input`, not `plan.steps.0.query`)
   - refine input: `run_id:` (not `result_uri:`)
   - export input: `destination: {type: s3, uri: "..."}`, `include_provenance: true`
   - export output: `destination_uri` (not `s3_uri`)
   - compute input: `source_uri:` (not `dataset_uri:`), `parameters:` (not `params:`)

5. **clAWS demo data is infrastructure.** The four `claws_demo.*` Glue tables
   (`course_evaluations`, `student_retention_cohorts`, `donor_giving_history`,
   `sponsored_program_expenditures`) must be pre-seeded in us-east-1 before
   institutional-analytics scenarios will pass. They're not created by the test suite.
   See `tests/scenarios/README.md` for the S3 locations.

## Substrate (Test Infrastructure)

Integration tests across all sub-projects run against
[Substrate](https://github.com/scttfrdmn/substrate) — a local AWS emulator
built and cloned in CI from that repo.

**Do NOT modify Substrate source directly when working in this monorepo.**
If you encounter a bug or missing feature in Substrate (e.g. a service not
emulated, wrong response format, missing operation), file an issue at
https://github.com/scttfrdmn/substrate/issues with a clear description of
the expected vs actual behavior. Do not apply fixes to `~/src/substrate/`
as a workaround.

## Important Notes

- **Model router does NOT need tool-use.** AgentCore handles it.
- **"Quick Suite" = platform. "Quick Sight" = BI capability. `quicksight` = API only.**
- **clAWS bridge:** `claws://` URIs connect Open Data → Compute; requires `CLAWS_RESOLVER_ARN` set on the compute extract Lambda (CDK context var `claws_resolver_arn`).
