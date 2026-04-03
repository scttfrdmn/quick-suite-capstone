# Academic Research Examples

These examples show how faculty, graduate students, and research computing
teams can use Amazon Quick Suite to run end-to-end research workflows — from
open data discovery through statistical analysis — without managing local
compute or data pipelines. Every example uses public datasets from the
Registry of Open Data on AWS (RODA); no data transfer fees or proprietary
data agreements are required to run them.

Each workflow uses the quick-suite-data stack for dataset discovery and
loading (`roda_search`, `roda_load`) and the quick-suite-compute stack for
analysis (`compute_run`, `compute_status`). The CDC Health Disparities example
also uses quick-suite-router to generate a grant narrative from the regression
results. All tools surface as MCP tools in Bedrock AgentCore Gateway; Quick
Suite's agent orchestration selects and sequences them automatically when
invoked from the chat interface.

## Examples

| Example | Stacks | Question |
|---------|--------|----------|
| [noaa-climate-trends](noaa-climate-trends/) | data, compute | What does a 24-month Prophet forecast of NOAA GHCN daily maximum temperatures look like? |
| [1000genomes-population-structure](1000genomes-population-structure/) | data, compute | Do k-means clusters on PCA components recover the five 1000 Genomes super-population groups? |
| [cdc-health-disparities](cdc-health-disparities/) | data, compute, router | Which social determinants best predict diabetes prevalence variation across census tracts? |
| [gbif-species-range-shift](gbif-species-range-shift/) | data, compute | Is observed latitude shifting northward over time in GBIF occurrence records? |
| [openaq-pollution-spikes](openaq-pollution-spikes/) | data, compute | Which OpenAQ air quality readings are statistical anomalies consistent with pollution spike events? |

## Running a Scenario

Each subdirectory contains a `scenario.yaml` that describes inputs, step
sequencing, and assertions. To execute a scenario against deployed stacks:

```bash
python3 -m pytest tests/scenarios/ -v -m scenario -k noaa-climate-trends
```

To run all academic-research scenarios:

```bash
python3 -m pytest tests/scenarios/ -v -m scenario -k "academic-research"
```

Scenarios require the relevant stacks to be deployed and AWS credentials
configured for the target account. RODA datasets are in `us-east-1`; deploy
stacks to that region for lowest latency and no cross-region data transfer
costs.
