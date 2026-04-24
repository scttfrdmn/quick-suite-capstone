# Using Quick Suite Extensions in AWS Kiro

AWS Kiro is an agentic IDE that supports MCP servers natively. Since
Campus AgentCore registers all their tools through a single Bedrock
AgentCore Gateway — which is an MCP server — Kiro can use the same tools
that Quick Suite's chat agent uses. Same infrastructure, same Cedar
policies, same Guardrails, same audit trail.

This means a researcher writing analysis code in Kiro can search
datasets, query institutional data, run statistical profiles, and monitor
literature — all without leaving the editor.

## What Works

All tools from all four extensions are available through the single
Gateway connection:

| Extension | Tools available in Kiro | Best for |
|-----------|----------------------|----------|
| Router | analyze, generate, research, summarize, code, extract | LLM tasks with governance: summarize a paper, extract structured data, generate code with guardrails |
| Data | roda_search, federated_search, snowflake_query, pubmed_search, and 12 more | Find datasets, search literature, query warehouses — all from the IDE |
| Compute | compute_run, compute_status, compute_profiles, and 5 more | Run statistical analysis: clustering, regression, causal inference, IRT, power analysis |
| clAWS | discover, probe, plan, excavate, refine, export, remember, recall, watch, and 4 more | Policy-gated queries against institutional databases; proactive watches; memory |

## What's Different From Quick Suite

Quick Suite is a BI and chat workspace. Kiro is a code editor. The tools
are the same, but the context is different:

- **No Quick Sight rendering.** Compute results land as Quick Sight
  datasets, but you view them in Quick Sight, not in Kiro. CSV/XLSX
  export URLs are returned in `compute_status` responses — download and
  open locally.
- **No Quick Flows.** Flow triggers from watches still fire, but you
  configure them from clAWS tools, not a Quick Flows UI.
- **Code-first workflows.** The `custom-python` and `custom-generated`
  compute profiles are especially natural here — write a script in Kiro,
  submit it as a compute job, iterate.
- **Schema-aware coding.** Use `probe` and `s3_preview` to inspect a
  dataset's schema, then write pandas/polars/SQL code against it with
  the actual column names and types in front of you.

## Setup

### Prerequisites

- AWS Kiro installed
- Quick Suite Extensions deployed (all four CDK stacks)
- AgentCore Gateway endpoint URL (from Router stack outputs)
- Cognito OAuth client credentials (client_id + client_secret from the Router's Cognito User Pool)

### 1. Get the Gateway endpoint

```bash
aws cloudformation describe-stacks \
  --stack-name QuickSuiteRouterStack \
  --query 'Stacks[0].Outputs[?OutputKey==`GatewayEndpointUrl`].OutputValue' \
  --output text
```

### 2. Get a Cognito access token

The Router stack creates a Cognito User Pool with an app client configured
for `client_credentials` grant. Get the token endpoint:

```bash
aws cloudformation describe-stacks \
  --stack-name QuickSuiteRouterStack \
  --query 'Stacks[0].Outputs[?OutputKey==`CognitoTokenEndpoint`].OutputValue' \
  --output text
```

Request a token:

```bash
curl -X POST "${TOKEN_ENDPOINT}" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=${CLIENT_ID}&client_secret=${CLIENT_SECRET}"
```

For development, you can set this as an environment variable. For
production use, configure Kiro's credential provider to refresh tokens
automatically.

### 3. Configure the MCP server in Kiro

Copy `kiro/mcp.json` to your project's `.kiro/mcp.json` (or your global
Kiro MCP config), replacing the placeholder values:

```json
{
  "mcpServers": {
    "quick-suite": {
      "type": "sse",
      "url": "https://agr-abc123.execute-api.us-east-1.amazonaws.com",
      "headers": {
        "Authorization": "Bearer eyJhbGciOi..."
      }
    }
  }
}
```

### 4. Verify

Open a new Kiro conversation and ask: "What compute profiles are
available?" Kiro should call `compute_profiles` and return the list
of 42 analysis profiles.

## Examples

The `kiro/examples/` directory contains worked examples organized by
extension and by cross-tool workflows:

**Per-tool examples** — focused demonstrations of individual tools:
- `router/` — analyze, extract, grounded research
- `data/` — dataset search, federated search, warehouse queries, literature
- `compute/` — clustering, causal inference, power analysis, custom scripts
- `claws/` — discover + probe, plan + excavate, memory, watches

**Cross-tool examples** — multi-step workflows spanning extensions:
- `cross-tool/research-data-pipeline.md` — literature search to analysis
- `cross-tool/institutional-query.md` — discover to compute
- `cross-tool/grant-monitoring.md` — watch setup to automated response

Each example shows the developer's intent, the tool calls that fire, and
how the results feed back into the coding workflow.

## Security Notes

- The same Cedar policies apply. A developer in Kiro has the same data
  access permissions as they would in Quick Suite — controlled by their
  Cognito identity and Cedar policy assignments.
- Bedrock Guardrails scan all inputs and outputs, same as Quick Suite.
- The audit trail is identical. Compliance teams see the same records
  regardless of whether a tool was invoked from Quick Suite or Kiro.
- PHI routing restrictions apply: `data_classification: "phi"` requests
  route to Bedrock only, even from Kiro.
