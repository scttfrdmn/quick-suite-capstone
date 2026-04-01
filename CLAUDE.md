# CLAUDE.md — Quick Suite Monorepo Context

## What Is This

Three independent CDK projects that extend Amazon Quick Suite through
Bedrock AgentCore Gateway. All tools surface as MCP tools in AgentCore
Gateway. Quick Suite's built-in agent orchestration decides which tools
to call — the individual projects don't orchestrate each other.

**Product terminology (get this right):**

- **Amazon Quick Suite** — the umbrella agentic AI workspace. Combines
  Quick Sight (BI), Quick Research (deep research), Quick Flows (workflow
  automation), Quick Automate (process optimization), and Quick Index
  (data discovery). NOT just QuickSight renamed — a broader agentic
  platform. $40/user/month power users.

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

- **MCP Actions Integration** — how Quick Suite connects to external tools.
  Quick Suite → MCP Actions Integration → AgentCore Gateway → Targets.

```
~/src/quick-suite/
├── CLAUDE.md                        ← you are here
├── README.md
├── quick-suite-model-router/        # LLM multi-provider routing (Python CDK, DONE)
├── quick-suite-open-data/           # Public + institutional data access (MOSTLY DONE)
└── quick-suite-compute/             # Ephemeral analytics compute (empty)
```

## Target Architecture

```
Amazon Quick Suite (Chat Agent / Quick Research / Quick Flows)
    │
    │  MCP Actions Integration
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
    └── Lambda Targets: Compute
        ├── compute_run      — match intent to profile, execute analysis
        ├── compute_status   — check job progress
        └── compute_profiles — list available analysis types
```

**AgentCore Gateway is the orchestration layer, not the model router.**
The Gateway discovers all tools, Quick Suite's agent picks which to call,
and the Gateway dispatches to the correct backend. The model router is
one peer among several tool sets.

**All open-data and compute Lambdas are AgentCore Gateway Lambda targets.**
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

When adapting existing roda-search and dataset-loader Lambdas:
- Delete `response(status, body)` helper — return plain dicts
- Delete `parse_body(event)` helper — event IS the arguments
- Add `context.client_context.custom` access for tool name
- All business logic stays exactly the same

## Project Status

### quick-suite-model-router ✅ IMPLEMENTED

Python CDK. 25 files. Has its own CLAUDE.md and TODO.md.

**What works:** Provider routing + fallback, DynamoDB cache, Bedrock
Guardrails (Bedrock provider only), CloudWatch dashboard, Cognito OAuth,
OpenAPI spec, blog post, full GTM suite.

**Outstanding TODOs (from TODO.md):**
1. CRITICAL: Wire `apply_guardrail()` in 3 external providers
2. HIGH: Wire `context` field in all 4 providers
3. HIGH: Add tests (test matrix in TODO §3)
4. HIGH: Add CI (TODO §4)
5. MEDIUM: Agent template, post-deploy script, X-Ray
6. LOW: Known limitations in README
7. Init git, push to GitHub

**No tool-use changes needed.** AgentCore Gateway handles orchestration.

### quick-suite-open-data 🔶 MOSTLY DONE

Three of five Lambdas fully written. Two are in `mnt/` (NOT junk).

**Fully written:**
1. `index.py` — catalog-sync (complete)
2. `mnt/.../roda-search/index.py` — search (~250 lines, complete, needs AgentCore adaptation)
3. `mnt/.../dataset-loader/index.py` — loader (~300 lines, complete, needs AgentCore adaptation)

**CDK:** `roda-integration-stack.ts` (TypeScript, needs Python conversion,
drop API Gateway for AgentCore Lambda targets)

**Other:** `roda-tools.yaml` (tool schemas, complete), `integration-guide.md`, `README.md`

**Missing:** S3 browser Lambdas, CDK conversion, file reorg, tests, CLAUDE.md

### quick-suite-compute ❌ EMPTY

## Conventions

- **Python CDK.** Entry point: `app.py`.
- **Python 3.12 Lambdas.** `boto3` + stdlib. No vendor SDKs.
- **AgentCore Lambda targets return plain dicts.**
- **Quick Sight API calls** use `boto3.client('quicksight')` — API namespace.
  User-facing text: "Quick Sight" (BI) or "Quick Suite" (platform).
- **Structured JSON logging** at INFO level.
- **Apache 2.0.**

### Naming

Repos: `quick-suite-<component>`
CDK stacks: `QuickSuiteModelRouter`, `QuickSuiteOpenData`, `QuickSuiteCompute`
Lambda prefix: `qs-model-router-`, `qs-open-data-`, `qs-compute-`
DynamoDB prefix: `qs-`
SSM prefix: `/quick-suite/`

## Project Tracking

Work is tracked in GitHub — not in local files. Do not add TODO lists or task
tracking to CLAUDE.md files or create TODO.md files.

- **Capstone (suite):** https://github.com/scttfrdmn/capstone/issues
- **Model Router:** https://github.com/scttfrdmn/quick-suite-model-router/issues
- **Open Data:** https://github.com/scttfrdmn/quick-suite-open-data/issues
- **Compute:** https://github.com/scttfrdmn/quick-suite-compute/issues

Each sub-project has its own milestones, labels, and project board.
All release planning happens via milestones. Changelogs follow keepachangelog,
versions follow semver 2.0.

## Important Notes

- **Model router does NOT need tool-use.** AgentCore handles it.
- **"Quick Suite" = platform. "Quick Sight" = BI capability. `quicksight` = API only.**
