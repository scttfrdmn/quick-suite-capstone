# Capstone

Extensions for [Amazon Quick Suite](https://aws.amazon.com/quick-suite/) via [Bedrock AgentCore Gateway](https://aws.amazon.com/bedrock/agentcore/).

Three independent CDK stacks that register as MCP tools in AgentCore Gateway, giving Quick Suite users natural language access to multi-provider LLMs, 500+ public datasets, institutional S3 data, and ephemeral analytics compute — all from the Quick Suite chat interface.

## Components

| Component | Repo | What It Does | Status |
|-----------|------|-------------|--------|
| **Model Router** | [quick-suite-model-router](https://github.com/scttfrdmn/quick-suite-model-router) | Multi-provider LLM routing (Bedrock, Anthropic, OpenAI, Gemini) with Bedrock Guardrails governance on every call | Implemented |
| **Open Data** | [quick-suite-open-data](https://github.com/scttfrdmn/quick-suite-open-data) | Browse + load public datasets from the Registry of Open Data on AWS, plus institutional S3 data | Implemented |
| **Compute** | [quick-suite-compute](https://github.com/scttfrdmn/quick-suite-compute) | Ephemeral analytics — clustering, regression, forecasting, and more — results land back as Quick Sight datasets | Implemented |

Each component deploys independently. Together they compose through AgentCore Gateway — Quick Suite's agent sees all tools from all deployed components and orchestrates them in conversation.

## How It Works

```
Quick Suite (Chat Agent / Quick Research / Quick Flows)
    │  MCP Actions Integration
    ▼
AgentCore Gateway (MCP)
    ├── analyze, generate, summarize, code  →  Model Router (LLM providers)
    ├── roda_search, roda_load              →  Open Data (public datasets)
    ├── s3_browse, s3_preview, s3_load      →  Open Data (institutional S3)
    └── compute_run, compute_status         →  Compute (ephemeral analytics)
```

## Cost

| Component | Monthly Idle | Per-Request |
|-----------|-------------|-------------|
| Model Router | ~$5 | LLM tokens (your existing provider spend) |
| Open Data | ~$1 | < $0.01 per search/load |
| Compute | ~$5 | $0.001–$0.50 per job |

## Project Tracking

Each component has its own GitHub Issues, milestones, and project board. See the individual component repos above.

## License

Apache-2.0 — Copyright 2026 Scott Friedman
