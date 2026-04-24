# Institutional Analytics Examples

This directory contains cross-stack Quick Suite workflow examples built for
university institutional analytics use cases. Each example demonstrates how
Quick Suite's constituent capabilities — clAWS for policy-gated institutional
data excavation, campus-data for public RODA/IPEDS datasets, campus-compute
for analytics profiles, and the model router for narrative generation — compose
into end-to-end analytical pipelines that IR offices, advancement teams, and
compliance staff can run directly from the Quick Suite agent interface.

Examples are designed for the roles that actually own these questions at R1
and regional comprehensive universities: IR directors preparing accreditation
evidence, enrollment analysts building budget forecasts, advancement analytics
teams segmenting donor portfolios, academic affairs staff surfacing curriculum
themes, and research compliance officers monitoring sponsored award burn rates.
Some scenarios use only public RODA data and require no institutional
configuration; others query institutional databases via clAWS and require Glue
catalog registration and Cedar policy grants before the first run. Setup
requirements are clearly noted for each example.

Two data paths are represented. Public-data examples (`enrollment-forecast`,
`peer-benchmarking`) use the `data` stack's `roda_search` and `roda_load` tools
to pull IPEDS datasets from the Registry of Open Data on AWS — no institutional
credentials or data access required. Institutional-data examples use the `claws`
stack, which enforces Cedar policy at the Gateway boundary and applies Bedrock
Guardrails at query-plan generation time; these examples require that source
tables are registered in the Glue catalog and that the requesting principal
holds the appropriate clAWS domain access action. See each scenario's
`scenario.yaml` for the precise schema and setup instructions.

## Examples

| Example | Stacks | Data Source | One-Line Description |
|---|---|---|---|
| [enrollment-forecast](enrollment-forecast/) | data, compute, router | Public (IPEDS / RODA) | Prophet 8-semester headcount projection with provost narrative |
| [peer-benchmarking](peer-benchmarking/) | data, compute, router | Public (IPEDS / RODA) | GLM benchmarking of tuition revenue per FTE against national peers |
| [student-retention](student-retention/) | claws, compute | Institutional (SIS / Athena) [setup required] | Cohort retention rates by Pell status for accreditation reporting |
| [donor-segmentation](donor-segmentation/) | claws, compute | Institutional (Advancement / Athena) [setup required] | K-means donor clustering for major gifts portfolio assignment |
| [course-eval-topics](course-eval-topics/) | claws, compute | Institutional (Evals / S3) [setup required] | LDA topic modeling of open-ended course evaluation responses |
| [grant-anomaly-detection](grant-anomaly-detection/) | claws, compute | Institutional (Sponsored Programs / Athena) [setup required] | Isolation Forest burn-rate anomaly flagging for compliance review |

Examples marked **[setup required]** use the `claws` stack and require
institutional Athena tables or S3 paths to be registered in the Glue catalog
and approved-domains configuration before running. See the individual
`scenario.yaml` for schema details and Cedar policy prerequisites.
