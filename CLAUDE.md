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

### quick-suite-router ✅ v0.12.0

GitHub: [scttfrdmn/quick-suite-router](https://github.com/scttfrdmn/quick-suite-router)

Python CDK. Six tool endpoints (`analyze`, `generate`, `research`,
`summarize`, `code`, `extract`). Four providers: Bedrock, Anthropic direct, OpenAI
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
- CORS wildcard replaced with `CORS_ALLOWED_ORIGIN` env var (CDK context `cors_allowed_origin`)
- Spend ledger authorization: `department`/`user_id` extracted from Cognito JWT claims; body fallback for direct invocation
- `query-spend` Lambda: non-admin callers restricted to own department/user by Cognito groups (`finance_admin`, `admin`)
- Content audit logging: SHA-256 hashes of prompt + response when `enable_content_logging=true` CDK context flag is set
- Guardrail version via SSM: all provider Lambdas read `/quick-suite/router/guardrail-version` at cold start
- `guardrail-version-updater` Lambda: updates SSM param without `cdk deploy`
- Full test suite (202 unit tests); cfn-lint + CDK synth in PR-blocking CI job

**v0.11.0 capability routing:**
- Model capability registry: `model_capabilities` + `model_context_windows` top-level dicts in `routing_config.yaml`; keyed by `provider/model_id`; non-breaking alongside existing `preferred` lists
- `select_provider()` now accepts `required_capabilities: list` and `context_budget: int`; skips providers missing any required cap or with insufficient context window; returns 3-tuple `(provider_key, model_id, skip_reason)`
- `estimate_tokens(text)` heuristic: `max(1, len(text) // 4)` applied to prompt + system + context + max_tokens
- Specific 400 error codes: `context_limit_exceeded` and `unsatisfiable_capabilities` with `tokens_in_estimate` in response body
- `tokens_in_estimate` included in every successful response
- Fallback chain respects the same capability + context filters
- 12 new tests in `TestCapabilityAndContextRouting`

**v0.12.0 operational controls:**
- Dry-run mode: `dry_run: true` in any request body returns `{estimated_cost_usd, selected_provider, selected_model, tokens_in_estimate}` without invoking any model or writing spend ledger; capability + context filters still apply (#37)
- Per-user rate limiting: new `lambdas/authorizer/handler.py` Lambda authorizer decodes Cognito JWT, extracts `sub`, returns IAM Allow policy with `usageIdentifierKey = sub`; CDK creates per-user usage plan (`PerUserRateLimitPlan`) when `rate_limit_per_minute` context is set, with `throttle.rate_limit = rpm/60`, `burst_limit = rpm*2`, `quota.limit` from `rate_limit_per_day` (default 1000) (#36)
- 8 new tests: `TestDryRunMode` (5) + `TestPerUserRateLimitingAuthorizer` (3)

**v0.12.0 science literature extraction:**
- `extract` tool (#38): 6th tool endpoint for structured extraction from text; `extraction_types` list (e.g. `effect_sizes`, `confounds`, `methods_profile`, `open_problems`, `citations`); auto-requires `structured_output` capability; providers enable JSON mode (OpenAI: `response_format={"type":"json_object"}`, Gemini: `responseMimeType`); response includes `extracted_fields` dict
- `open_problems` extraction type (#39): extracts `[{gap_statement, domain, confidence}]` objects; optional `store_at_uri: "s3://..."` persists gap list to S3 for clAWS watch use
- `grounding_mode: "strict"` on `research` tool (#40): injects citation directive; response gains `sources_used`, `grounding_coverage`, `low_confidence_claims` parsed from trailing JSON block
- 13 new tests: `TestExtractTool` (5) + `TestGroundingModeStrict` (3) + open_problems variants (5); total 263 unit tests

---

### quick-suite-data ✅ v0.13.0

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
- `snowflake_query` — parameterized read-only SQL via Snowflake SQL API v2; `?` placeholders, positional bindings, mutation detection, max 1000 rows
- `redshift_browse` — list tables in a Redshift Serverless workgroup (Redshift Data API)
- `redshift_preview` — sample rows + schema from a Redshift table
- `redshift_query` — parameterized read-only SQL via Redshift Data API; `?` → `$N` rewriting, async poll, mutation detection, max 1000 rows
- `federated_search` — unified search across all registered source types (roda/s3/snowflake/redshift/ipeds/nih_reporter/nsf_awards/pubmed/biorxiv/semantic_scholar/arxiv/reagents); keyword scoring; `data_classification_filter`; `skipped_sources`
- `ipeds_search` — search IPEDS via Urban Institute Education Data Portal API (public, no auth); `survey`, `year_range`, `max_results` params; returns `series_slug`, `year_range`, `quality_score`
- `nih_reporter_search` — search NIH Reporter v2 API (public, no auth); `fiscal_year`, `institution`, `pi_name` filters; returns `core_project_num`, `pi_names`, `award_amount`, `abstract_text`
- `nsf_awards_search` — search NSF Award Search API (public, no auth); `date_start`, `date_end`, `pi_name` filters; returns `award_id`, `pi_name`, `awardee_name`, `funds_obligated_amt`, `abstract_text`

**Internal Lambdas:**
- `catalog-sync` — syncs RODA NDJSON catalog into DynamoDB daily (+ SNS real-time)
- `catalog-quality-check` — weekly scan; flags stale/unreachable datasets; writes `last_verified` + `quality_score` to catalog items; emits `StaleDatasets`/`UnreachableDatasets` CW metrics
- `claws-resolver` — resolves `claws://` source URIs to Quick Sight dataset IDs via `ClawsLookupTable`
- `register-source` — writes entries to `qs-data-source-registry` DynamoDB table

**ClawsLookupTable:** DynamoDB table (`source_id` PK → `dataset_id`). Written by `roda_load` and `s3_load`. Read by `claws-resolver`. Enables clAWS bridge between Open Data and Compute.

**Source Registry:** `qs-data-source-registry` DynamoDB table. SSM param `/quick-suite/data/source-registry-arn` for clAWS catalog-aware discover integration (v0.10.0).

**v0.9.0:**
- Per-caller credential isolation: all four browse/preview Snowflake/Redshift tools accept optional `caller_secret_arn`; validated against `arn:aws:secretsmanager:` format and `CALLER_SECRETS_ALLOWED_ARNS` prefix allowlist; falls back to shared service account (#40)
- `snowflake_query` AgentCore Lambda target: parameterized SQL, `?` bindings, mutation detection (#35)
- `redshift_query` AgentCore Lambda target: parameterized SQL, `?` → `$N`, Redshift Data API async pattern, mutation detection (#36)

**v0.8.0 security hardening:**
- S3 IAM scoping: RODA loader wildcard read documented; no PutObject on wildcard; institutional tools scoped to configured buckets; `roda_bucket_arns` CDK context for narrowing RODA access (#52)
- SSRF prevention: catalog quality-check validates S3 bucket names from ARNs against naming rules before `head_bucket` (#53)
- QuickSight principal: confirmed env var derivation, not caller event (#54)
- register-source auth: `connection_config` format validated per source type (s3→bucket key, snowflake/redshift→Secrets Manager ARN); CDK resource policy via `register_source_admin_arn` context (#55)
- Redshift workgroup removed from response; error messages sanitized (#56, #59)
- DynamoDB protection: `catalog_table` and `source_registry_table` have `deletion_protection=True`, `point_in_time_recovery=True`; catalog removal policy changed to RETAIN (#57)
- s3_preview file extension allowlist: `.parquet`, `.csv`, `.tsv`, `.json`, `.jsonl`, `.ndjson`, `.gz` variants; extension validated before any S3 read (#58)
- Error sanitization: s3_browse, s3_preview, redshift_browse, snowflake_browse return generic messages; no bucket names, ARNs, account IDs, or exception details in responses (#59)

**v0.10.0 research API integrations:**
- Three new AgentCore Lambda tools: `ipeds_search`, `nih_reporter_search`, `nsf_awards_search` (all public APIs, stdlib `urllib`, no vendor SDKs)
- `federated_search` extended with `_search_ipeds`, `_search_nih_reporter`, `_search_nsf_awards` dispatch functions
- CDK: three new Lambda constructs in `open_data_stack.py`; all added to `tool_arns` CfnOutput
- 25 new tests in `tests/test_research_sources.py`

**v0.11.0 scientific literature + reagent sources:**
- Five new AgentCore Lambda tools: `pubmed_search` (NCBI E-utilities esearch+esummary, optional `NCBI_API_KEY`, recency quality score), `biorxiv_search` (bioRxiv/medRxiv details API, `server=both` dual-call, last-30-days default), `semantic_scholar_search` (Semantic Scholar Graph API, optional `SEMANTIC_SCHOLAR_API_KEY`, citation+recency quality score, client-side `min_citations`/`year_start`/`year_end`/`fields_of_study` filters), `arxiv_search` (Atom/XML via `xml.etree.ElementTree`, `category_filter`), `reagent_search` (Addgene catalog API v2, requires `ADDGENE_API_KEY`, returns informational note when absent)
- `federated_search` extended with 5 new dispatch functions; `_search_fn` dict now covers 12 source types
- CDK: 5 new Lambda constructs; all added to `_new_tool_fns`, KMS grant list, `tool_arns` CfnOutput
- `docs/adding-sources.md`: contributor guide (source interface contract, auth patterns, quality score guidelines, testing skeleton, CDK wiring)
- 38 new tests in `tests/test_literature_sources.py`

**v0.12.0 memory source registration:**
- `register-memory-source` internal Lambda: registers clAWS memory NDJSON as QuickSight dataset; idempotent via `qs-claws-memory-registry` DynamoDB table check; S3 manifest generation + QuickSight CreateDataSource/CreateDataSet/CreateIngestion; `MemoryRegistrarArn` CfnOutput for cross-stack invocation (#60)
- CDK: `qs-claws-memory-registry` DynamoDB table (PK: `user_arn_hash`, SK: `dataset_type`), deletion protection, PITR
- 5 new tests in `tests/test_memory_source.py`

**v0.13.0 quality + sources:**
- `requires_transform` dispatch: non-native formats (.nc, .h5, .pdf, .geojson) return `suggested_profile` pointing to compute ingest profile instead of failing (#37)
- Data quality metrics: `s3_preview`, `snowflake_preview`, `redshift_preview` responses include `quality` block with `null_pct`, `estimated_cardinality`, `duplicate_row_pct` per column (#38)
- `research_search` AgentCore Lambda target: Zenodo + Figshare public API search with 429 exponential backoff; `federated_search` extended with `_search_zenodo` and `_search_figshare` dispatch (#39)
- 15 new tests in `tests/test_quality_sources.py`

Full test suite (372 unit tests; Substrate integration).

---

### quick-suite-claws ✅ v0.18.0

GitHub: [scttfrdmn/quick-suite-claws](https://github.com/scttfrdmn/quick-suite-claws)

Nine AgentCore tool Lambdas + two internal Lambdas + Cedar policies + Bedrock Guardrail configs + CDK stacks.

**Tool Lambdas:**
- `discover` — find data sources in approved domains (Glue catalog search + `registry` domain queries `qs-data-source-registry`)
- `probe` — inspect schema, sample rows, cost estimates; PII scan on samples
- `plan` — translate free-text objective → concrete query (LLM + Guardrails); stores `team_id`, `created_by`, and `status` (`ready` or `pending_approval` when `requires_irb: true`); supports `is_template=True` to create reusable `{{variable}}` templates (status `template`, no LLM invocation)
- `excavate` — execute exact query from plan; blocks `pending_approval` and `template` plan statuses; principal must be owner or in `shared_with`
- `refine` — dedupe, rank, summarize results with grounding guardrail
- `export` — materialize to S3/EventBridge with provenance chain; validates destination URI against `CLAWS_EXPORT_ALLOWED_DESTINATIONS` allowlist; enforces HTTPS on callback destinations
- `team_plans` — list all plans for a given `team_id` (read-only summaries)
- `share_plan` — owner grants read/excavate access to other principals via `shared_with` list
- `instantiate_plan` — create a concrete plan from a template plan by substituting `{{variable}}` placeholders with provided values; calls full plan generation flow with resolved objective

**Internal Lambdas (not AgentCore tools):**
- `approve_plan` — IRB reviewer approves a `pending_approval` plan; checks `CLAWS_IRB_APPROVERS` allowlist; emits `claws.irb / PlanApproved` EventBridge event; blocks self-approval
- `audit_export` — scans CloudWatch Logs for audit records in a date range; writes NDJSON to S3 with SHA-256-hashed inputs/outputs (no PII); fields: `principal`, `tool`, `inputs_hash`, `outputs_hash`, `cost_usd`, `guardrail_trace`, `timestamp`

**v0.11.0 compliance features:**
- IRB workflow: `requires_irb: true` on plan → `status: pending_approval`; `excavate` gates on status; `approve_plan` Lambda + `plan.approve` Cedar action (irb_approver role, no self-approval)
- FERPA Guardrail preset: `guardrails/ferpa/ferpa_guardrail.json`; five denied topic categories; SSN + student ID regex patterns; deploy with CDK context `enable_ferpa_guardrail: true`
- Cedar policy templates: `policies/templates/{read-only,no-pii-export,approved-domains-only,phi-approved}.cedar`

**v0.12.0 security hardening:**
- Column-level access control: `plan` filters schema by principal roles; `excavate` post-filters result columns to `allowed_columns`
- Multi-backend cost estimator: Athena, DynamoDB, MCP pricing models
- HMAC-SHA-256 audit hashing: keyed secret in Secrets Manager; irreversible hashes in audit NDJSON
- MCP source ID validation: `plan` validates server name against MCP registry before query generation
- Mutation detection: `_check_mutation()` in DynamoDB PartiQL and S3 Select executors; INSERT/UPDATE/DELETE/DROP/CREATE/TRUNCATE/ALTER rejected
- Refine summary guardrail: LLM-generated summary text scanned through `ApplyGuardrail` before return
- `requires_irb` enforcement: `approve_plan` checks `plan.requires_irb` before any approval logic
- OpenSearch error sanitization: raw endpoint URLs, index names, and exception details never returned to callers
- DynamoDB PITR + deletion protection on all three tables
- Lambda log retention: 90-day retention on all 12 Lambda log groups
- Athena IAM scoped to `claws-readonly` workgroup ARN (no wildcard)

**Safety layers (two independent):**
- Cedar (AgentCore Policy) — structural/deterministic at Gateway boundary
- Bedrock Guardrails — semantic/content at LLM I/O and data paths via `ApplyGuardrail` API

**Core principle:** LLM reasoning never happens inside a tool. `plan` is the only tool with free-text input; `excavate` takes the concrete plan verbatim.

**v0.13.0 security fixes (p1):**
- Silent guardrail bypass made visible: `scan_payload()` returns `status="bypassed"` + ERROR log when `CLAWS_GUARDRAIL_ID` unconfigured (#77)
- `validate_source_id()` in `shared.py` blocks path traversal, null bytes, control chars, unknown prefixes; called at plan + excavate handler entry (#78)
- OpenSearch DSL script injection blocked: `_check_dsl_scripts()` recursive walk rejects `script`, `scripted_metric`, `scripted_sort` at any nesting depth (#76)
- Cedar `plan.approve` permit requires `resource.requires_irb == true && resource.status == "pending_approval"` (#75)

**v0.14.0 features:**
- Plan templating: `plan` with `is_template=True` stores `{{variable}}` objective as `status="template"` with no LLM invocation; `excavate` blocks template plans (#66)
- `instantiate_plan` tool: resolves `{{var}}` placeholders → values dict, rejects nested `{{` injection, calls plan generation with resolved objective, returns new concrete `plan_id` (#66)
- Export destination allowlist: `CLAWS_EXPORT_ALLOWED_DESTINATIONS` env var (comma-separated URI prefixes); HTTPS enforced on all callback destinations regardless of allowlist (#80)
- Watch runner plan status check: blocks `pending_approval` and `template` plans at execution time (EventBridge Scheduler bypasses Cedar Gateway) (#79)

**v0.15.0 proactive intelligence workflows:**
- `watch_type: "new_award"` (#70) — executes a locked plan against NIH Reporter or NSF Awards source, scores award abstracts for semantic similarity to a lab profile abstract stored in SSM Parameter Store via Router `summarize`; only awards ≥ threshold fired in notification; `semantic_match` config: `lab_profile_ssm_key`, `abstract_similarity_threshold` (default 0.82), `abstract_field`; 16 new tests
- Watch action routing (#68) — `action_routing` field on any watch spec: `{destination_type: sns|eventbridge|bedrock_agent, destination_arn, context_template}`; `{key}` placeholder substitution from `diff_summary`; Router `summarize` call → `draft_text` (fail-open); SNS and EventBridge dispatch; Scheduler CDK: `sns:Publish` on `*` added to runner role
- Accreditation evidence ledger (#67) — `accreditation_config_uri` field on watch spec; `load_config_from_uri()` in `shared.py` loads JSON from `s3://bucket/key` or `ssm:/param/path`; `_evaluate_accreditation()` in runner evaluates `evidence_predicate` per SACSCOC/HLC standard against rows; gaps → `accreditation_gaps` in audit output; Cedar: `claws.accreditation_watch` (accreditation_reviewer role)
- Compliance surface watch (#69) — `compliance_mode: true` + `compliance_ruleset_uri` on watch spec (required together); `_run_compliance_watch()` evaluates 4 rule types (`international_site`, `new_data_source`, `subject_count`, `classification_change`); Router `summarize` drafts amendment text per gap (fail-open → ""); Cedar: `claws.compliance_watch` (irb_monitor role)
- 26 new tests in `tools/tests/test_v15_completion.py`

**v0.16.0 science literature watches:**
- `watch_type: "literature"` (#71) — monitors PubMed/bioRxiv rows for papers matching a lab profile; per-paper relevance scoring via Router `summarize`; `reagent_config_uri` and `protocol_config_uri` classify `relevance_type` (reagent/protocol/methodology) with appropriate `validation_steps`; threshold from `semantic_match.abstract_similarity_threshold` (default 0.75); router failures non-blocking; Cedar: `claws.literature_watch` (lab_director role)
- `watch_type: "cross_discipline"` (#72) — detects adjacent-field papers addressing open problems; loads gap list from `open_problems_uri` (S3 or SSM); per-paper Router `research` call with `grounding_mode="strict"`; qualifies on `cross_field_score >= field_distance` AND `citations_in_primary_field <= threshold`; `call_router()` extended with `grounding_mode` param; Cedar: `claws.cross_discipline_watch` (lab_director role)
- 23 new tests in `tools/tests/test_v16_watches.py`

**v0.17.0 institutional memory + flow trigger:**
- `claws.remember` tool: NDJSON append to S3 with ETag conditional write (3 retries on PreconditionFailed); first write invokes `register-memory-source` Lambda (quick-suite-data v0.12.0) to register as QuickSight dataset; `claws-memory-registry` DynamoDB idempotency check (#88)
- `claws.recall` tool: load NDJSON from S3, filter pipeline (expires_at > now → since_days → severity → tags any-match → query substring); returns `{records, total, filtered}` (#89)
- Watch runner memory integration: `_remember_finding()` helper invokes remember Lambda synchronously (best-effort, non-blocking); default `auto_remember=True` for literature/cross_discipline watches; `last_remembered_at` field on watch updates (#90)
- One-shot flow trigger: `_trigger_flow()` creates EventBridge Scheduler `at()` schedule with `ActionAfterCompletion=DELETE` targeting `quicksight:StartAutomationJob`; configurable `delay_minutes`; best-effort, non-blocking (#91)
- CDK: memory bucket (S3, versioned, RETAIN) + memory registry table (DynamoDB, PITR, deletion protection) in storage stack; `ClawsFlowTriggerRole` IAM role; runner env vars + IAM grants in scheduler stack; `remember` + `recall` Lambda constructs in tools stack (#92)
- Cedar: `claws.remember` (owner-only write) and `claws.recall` (owner or shared_with read) permits
- 20 new tests in `tools/tests/test_v17_memory.py`

**v0.18.0 backend coverage:**
- PostgreSQL executor: `psycopg2` connection from Secrets Manager, read-only sessions, 60s statement timeout, mutation detection; `query_type: "postgres_sql"` (#63)
- Redshift executor: Redshift Data API async execute-and-poll, typed field extraction, `$5/TB` cost model, mutation detection; `query_type: "redshift_sql"` (#64)
- Per-principal budget caps: SSM-based limits (`/quick-suite/claws/budget/{principal_arn}`), DynamoDB `claws-principal-spend` table for monthly spend tracking, 402 on exceeded, fail-open on errors, `enable_principal_budgets` CDK context gate (#65)
- CDK: `PrincipalSpendTable` DynamoDB (PITR, deletion protection), IAM for Secrets Manager + Redshift Data API + SSM budget params
- 18 new tests in `tools/tests/test_v18_backend_coverage.py`

Full test suite (455 tests: Substrate integration + pure unit). MCP executor for extensibility. All four roadmap themes complete.

---

### quick-suite-compute ✅ v0.17.0

GitHub: [scttfrdmn/quick-suite-compute](https://github.com/scttfrdmn/quick-suite-compute)

Seven AgentCore Lambda tools + Step Functions workflow + 41 analysis profiles across 12 categories.

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

**38 Analysis Profiles (Lambda unless noted):**
Statistics: anova, chi-square
Prediction/ML: regression-glm, regression-logistic, classification-random-forest
Forecasting: forecast-prophet, change-detection, seasonality-decompose
Clustering: clustering-kmeans
Text: text-topics, text-sentiment, text-similarity
Anomaly: anomaly-isolation-forest
Higher-Ed: cohort-flow, dfwi-analysis, equity-gap, peer-benchmark, retention-cohort, survival-kaplan-meier, intersectionality-equity, assessment-irt
Geospatial: geo-enrich (Census API), isochrone, spatial-aggregate
Exploration: explore-correlations
Research: grant-portfolio, network-coauthor, causal-iv, causal-rd, causal-did, grant-pipeline, provenance-graph, power-analysis, anomaly-hypothesis, reproducibility-check
Ingest: ingest-netcdf, ingest-pdf-extract, ingest-geojson
Custom: custom-python (RestrictedPython sandbox), custom-generated (LLM-generated code)
Transform: transform-spark (EMR Serverless)

**v0.14.0 security hardening:**
- compute-cancel ownership check: requires `user_arn`; verifies against execution input via `sfn.describe_execution()`; same "not found" message on mismatch (no info leak) (#82)
- Budget conditional write backstop: `record-spend` uses `ConditionExpression` on `spend_usd <= :remaining`; `ConditionalCheckFailedException` fails open with warning log (#79)
- source_uri bucket allowlist: `COMPUTE_ALLOWED_BUCKETS` env var (CDK context `compute_allowed_buckets`); rejects s3:// buckets not in list; empty list = allow all (backward compat) (#75)
- result_label validation: `^[A-Za-z0-9_\-]{1,64}$` enforced in compute-run (400 error) and record-spend (silent skip) (#76)
- `_validate_params` max-length: `MAX_STRING_PARAM_LENGTH = 256` guards on `column`, `column_list` items, `string_list` items (#80)
- DynamoDB protection: all 4 tables (SpendTable, SnapshotsTable, HistoryTable, SchedulesTable) have `deletion_protection=True`, `point_in_time_recovery=True`, `removal_policy=RETAIN` (#81)
- Log retention: `log_retention=logs.RetentionDays.THREE_MONTHS` (90 days) on all 16 Lambda functions (#84)

**v0.13.0 security fixes:**
- Pandas sandbox proxy: `_SafePandasProxy` blocks URL-based `read_*` method calls in RestrictedPython sandbox (#72)
- AST static analysis: `_analyze_generated_code()` gates LLM-generated code before execution (#73)
- Scoped SFN execution role: explicit `qs-compute-sfn-role` with `lambda:InvokeFunction` only on state machine Lambdas (#74)

**v0.13.0 features:**
- Job chaining: `HasChainProfile` Choice + `PrepareChainInput` Pass states after DeliverResults; chain runs second compute+deliver pass with output of first as input (#55)
- `compute_status` SUCCEEDED response includes `summary` dict from `$.compute` (row_count, columns, duration_seconds, metadata_s3_uri) (#57)
- `compute_schedule` AgentCore tool: create/list/delete scheduled jobs via EventBridge Scheduler; `qs-compute-schedules` DynamoDB table; `compute-schedule-trigger` internal Lambda (#56)

**v0.15.0 higher-ed equity + psychometrics profiles:**
- `intersectionality-equity` (#61): cross-tabs outcome metric by 2+ demographic columns; Disparate Impact ratio (80% rule); n<`n_suppress` cell suppression; `group_key`, `n`, `group_mean`, `di_ratio`, `adverse_impact_flag` columns
- `assessment-irt` (#62): 2PL IRT model via `girth` library; returns three tables — `item_parameters` (difficulty, discrimination), `person_abilities` (theta, se), `item_information`; graceful 503 if `girth` not installed; min 5 items / 100 respondents enforced
- 10 new tests: `TestIntersectionalityEquity` (5) + `TestAssessmentIRT` (5)

**v0.16.0 causal inference + research intelligence:**
- Runner plain-dict dispatch fix: coerce dict → diagnostics + empty DataFrame after `_dispatch()`; prevents AttributeError for all plain-dict handlers
- `causal-iv` (#63): 2SLS instrumental variables via `linearmodels`; first-stage F-stat, weak instrument warning (F < 10), compliance rate, 95% CI; optional `peer_benchmark` annotates with peer cohort
- `causal-rd` (#64): numpy-native regression discontinuity; IK bandwidth formula `h = 2.702 * sigma * n^(-1/5)`; 5-point bandwidth sensitivity; McCrary density manipulation test; fuzzy RD via IV approach
- `causal-did` (#65): OLS difference-in-differences; parallel trends pre-period test; event study coefficients per time period; placebo pre-period tests; staggered adoption via `csdid` (503 if absent)
- `grant-pipeline` (#66): PI health scores (active*0.4 + continuity*0.4 + diversity*0.2); NCE risk flagging (end_date ≤60 days + no overlap); sponsor timing analysis
- `provenance-graph` (#67): W3C PROV-DM JSON-LD lineage from HistoryTable DynamoDB scan; Markdown summary; gap detection for broken input/output chains; `min_rows: 0` (queries DynamoDB, not input DataFrame)
- `peer_cohort` module (#68): Carnegie class + enrollment ±20% + control type + Pell ±10pt filtering; weighted scoring; 30-day DynamoDB cache in `qs-compute-peer-cohort-cache` table
- CDK: `PeerCohortCacheTable` DynamoDB (PAY_PER_REQUEST, PITR, deletion protection, TTL); `COMPUTE_HISTORY_TABLE` env var; `linearmodels==6.1` in Docker image
- 28 new tests: `TestRunnerDispatchPlainDict` (1), `TestPeerCohort` (4), `TestCausalIV` (5), `TestCausalRD` (5), `TestCausalDiD` (5), `TestGrantPipeline` (4), `TestProvenanceGraph` (4)

**v0.17.0 science research profiles:**
- `power-analysis` (#69): literature-informed sample size calculation via Router `extract` cross-reference on PubMed IDs; Cohen's d from pilot data or manual input; scipy power curves (n=2 to 100); confound checklists; graceful degradation when Router unavailable
- `anomaly-hypothesis` (#70): IsolationForest + Router `research` grounding for per-anomaly classification (`instrument_error | known_noise | reported_effect | novel_candidate`); domain z-thresholds (genomics 3.5, proteomics 3.0, behavioral 2.5, geospatial 3.0); Router unavailable → all `novel_candidate`
- `reproducibility-check` (#71): re-execute analysis script in RestrictedPython sandbox against deposited data; compare outputs to `manuscript_results` with configurable tolerance; provenance-graph integration for script version lookup
- CDK: `ROUTER_API_URL` env var from CDK context
- 18 new tests in `tests/test_research_science.py`

**Dashboard:** Per-profile Cost (USD/24h), Duration (p99), and Cumulative Cost (30d SUM) graph widgets generated from `config/profiles/*.json`.

Full test suite (616 unit tests); Substrate integration in CI.

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
