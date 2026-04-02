# Quick Suite Extensions

Extensions for [Amazon Quick Suite](https://aws.amazon.com/quick-suite/) via [Bedrock AgentCore Gateway](https://aws.amazon.com/bedrock/agentcore/).

Three independent CDK stacks that register as MCP tools in AgentCore Gateway, giving Quick Suite users natural language access to multi-provider LLMs, 500+ public datasets, institutional S3 data, and ephemeral analytics compute — all from the Quick Suite chat interface.

## Components

| Component | Repo | What It Does | Version |
|-----------|------|-------------|---------|
| **Model Router** | [quick-suite-router](https://github.com/scttfrdmn/quick-suite-router) | Multi-provider LLM routing (Bedrock, Anthropic, OpenAI, Gemini) with Bedrock Guardrails governance, multi-turn conversation history, and response caching | v0.5.0 |
| **Open Data** | [quick-suite-data](https://github.com/scttfrdmn/quick-suite-data) | Search + load 500+ public datasets from the Registry of Open Data on AWS; browse, preview, and register institutional S3 data as Quick Sight datasets | v0.5.0 |
| **Compute** | [quick-suite-compute](https://github.com/scttfrdmn/quick-suite-compute) | Ephemeral analytics — 10 profiles (clustering, regression, forecasting, topic modeling, and more) — results land back as Quick Sight datasets | v0.5.0 |

Each component deploys independently. Together they compose through AgentCore Gateway — Quick Suite's agent sees all tools from all deployed components and orchestrates them in conversation.

## How It Works

```
Quick Suite (Chat Agent / Quick Research / Quick Flows)
    │  MCP Actions Integration
    ▼
AgentCore Gateway (MCP)
    ├── analyze, generate, summarize, code, research  →  Model Router
    ├── roda_search, roda_load                         →  Open Data (public datasets)
    ├── s3_browse, s3_preview, s3_load                 →  Open Data (institutional S3)
    └── compute_profiles, compute_run, compute_status  →  Compute (ephemeral analytics)
```

The clAWS bridge connects Open Data and Compute: a `claws://roda-noaa-ghcn`
URI in a compute job resolves to the registered Quick Sight dataset, letting
Quick Suite orchestrate a full research-to-analysis workflow in a single
conversation.

## Cost

| Component | Monthly Idle | Per-Request |
|-----------|-------------|-------------|
| Model Router | ~$5 | LLM tokens (your existing provider spend) |
| Open Data | ~$1 | < $0.01 per search/load |
| Compute | ~$5 | $0.001–$0.50 per job |

## Project Tracking

| Component | Issues | Milestone | Project Board |
|-----------|--------|-----------|---------------|
| Model Router | [quick-suite-router/issues](https://github.com/scttfrdmn/quick-suite-router/issues) | [v0.5.0](https://github.com/scttfrdmn/quick-suite-router/milestone/1) | [Board](https://github.com/users/scttfrdmn/projects/44) |
| Open Data | [quick-suite-data/issues](https://github.com/scttfrdmn/quick-suite-data/issues) | [v0.5.0](https://github.com/scttfrdmn/quick-suite-data/milestone/1) | [Board](https://github.com/users/scttfrdmn/projects/45) |
| Compute | [quick-suite-compute/issues](https://github.com/scttfrdmn/quick-suite-compute/issues) | [v0.5.0](https://github.com/scttfrdmn/quick-suite-compute/milestone/1) | [Board](https://github.com/users/scttfrdmn/projects/46) |

## License

Apache-2.0 — Copyright 2026 Scott Friedman
