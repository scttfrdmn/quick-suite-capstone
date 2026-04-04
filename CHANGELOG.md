# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.6.0] - 2026-04-03

### Added
- New scenario category `examples/academic-research/` for science and research computing workflows (distinct from `institutional-analytics` which covers IR/admin use cases)
- `examples/academic-research/netcdf-prophet-pipeline/scenario.yaml` — NetCDF climate data ingest → Prophet 24-month forecast pipeline using `ingest-netcdf` + `forecast-prophet` chain
- `examples/academic-research/pdf-sentiment-pipeline/scenario.yaml` — PDF document ingest → VADER sentiment analysis pipeline using `ingest-pdf-extract` + `text-sentiment` chain
- `examples/institutional-analytics/grant-portfolio/scenario.yaml` — clAWS + compute end-to-end: excavate sponsored program expenditures → grant-portfolio burn rate analysis
- `examples/institutional-analytics/network-coauthor/scenario.yaml` — clAWS + compute end-to-end: excavate publications table → co-authorship network centrality and community detection
- `docs/prompts/research-computing.md` — seven example prompts for research computing director, research office analyst, and faculty researcher personas

## [0.5.0] - 2026-04-03

### Added
- `docs/workflows/` — four Quick Flows workflow templates: enrollment-funnel-monitor, grant-burn-rate-alert, student-risk-weekly, donor-engagement-quarterly
- `docs/prompts/clinical-research.md` — clinical research coordinator persona with IRB, REDCap, and survivorship analysis examples
- `docs/prompts/finance-and-budget.md` — finance analyst persona with budget variance, encumbrance, and grant F&A examples
- `docs/prompts/student-success.md` — student success advisor persona with early alert, DFWI, and cohort flow examples
- `docs/prompts/institutional-research.md` — institutional research director persona with IPEDS, accreditation, and benchmarking examples

## [0.4.0] - 2026-04-02

### Added
- Three institutional-analytics scenarios using the full clAWS pipeline: `course-evaluation-topics`, `student-retention-analysis`, `donor-giving-patterns`
- `tests/scenarios/test_scenarios.py` updated to run all six scenarios
- `tests/scenarios/README.md` — demo data setup instructions for clAWS scenarios (Glue tables, S3 locations)

## [0.3.0] - 2026-04-02

### Added
- Three compute-only scenarios (no clAWS required): `enrollment-forecast`, `donor-clustering`, `grade-equity-analysis`
- Scenario E2E test runner: `tests/scenarios/test_scenarios.py` with poll-until-done logic and assert engine
- `scenario.yaml` schema documentation in `tests/scenarios/README.md`

## [0.2.0] - 2026-04-01

### Added
- `examples/` directory structure with `institutional-analytics/` category
- Scenario YAML schema: `name`, `display_name`, `description`, `category`, `requires.stacks`, `steps[].tool`, `steps[].input`, `steps[].assert`, `steps[].poll`
- Deployment guide: `docs/deployment-guide.md` — CDK deploy order, AgentCore Gateway configuration, MCP Actions setup, user and group sharing

## [0.1.0] - 2026-04-01

### Added
- Model Router — multi-provider LLM routing with Bedrock Guardrails governance
- Open Data — public dataset search/load and institutional S3 data access
- Compute — ephemeral analytics compute with ten analysis profiles

[unreleased]: https://github.com/scttfrdmn/quick-suite-capstone/compare/v0.6.0...HEAD
[0.6.0]: https://github.com/scttfrdmn/quick-suite-capstone/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/scttfrdmn/quick-suite-capstone/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/scttfrdmn/quick-suite-capstone/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/scttfrdmn/quick-suite-capstone/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/scttfrdmn/quick-suite-capstone/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/scttfrdmn/quick-suite-capstone/releases/tag/v0.1.0
