# Quick Suite Examples

This directory contains end-to-end workflow examples for Amazon Quick Suite,
organized by use-case category. Each example is a self-contained subdirectory
with a `README.md` describing the scenario and a `scenario.yaml` that can be
executed by the scenario test runner.

## Categories

### [academic-research/](academic-research/)

Five cross-stack workflows built around public RODA datasets, targeting
faculty, graduate students, and research computing teams. Examples span
climate science, genomics, public health, ecology, and environmental science.
All workflows use quick-suite-data for open data discovery and loading plus
quick-suite-compute for analysis; one example also uses quick-suite-router to
generate a grant narrative.

| Scenario | Description |
|----------|-------------|
| [noaa-climate-trends](academic-research/noaa-climate-trends/) | Prophet 24-month forecast of NOAA GHCN daily max temperatures |
| [1000genomes-population-structure](academic-research/1000genomes-population-structure/) | K-means clustering on 1000 Genomes PCA components to recover super-populations |
| [cdc-health-disparities](academic-research/cdc-health-disparities/) | Logistic regression of social determinants on diabetes prevalence + grant narrative |
| [gbif-species-range-shift](academic-research/gbif-species-range-shift/) | Geo-enrichment + Spearman correlation to detect northward species range shifts |
| [openaq-pollution-spikes](academic-research/openaq-pollution-spikes/) | Isolation forest anomaly detection on OpenAQ air quality measurements |

### institutional-analytics/

Workflows for institutional research offices, data governance teams, and
administrative analytics use cases. Coming in a future release.

## Running Scenarios

Each `scenario.yaml` follows a common schema: named steps with a `tool`,
`stack`, `input`, and `assert` block. Steps reference prior step outputs
using `{step_id.field}` interpolation. Poll-based steps (typically
`compute_status`) include a `poll` block with `interval_seconds` and
`max_attempts`.

Execute any scenario against deployed stacks using the scenario test runner:

```bash
# Run a specific scenario by name
python3 -m pytest tests/scenarios/ -v -m scenario -k noaa-climate-trends

# Run all scenarios in a category
python3 -m pytest tests/scenarios/ -v -m scenario -k "academic-research"

# Run the full scenario suite
python3 -m pytest tests/scenarios/ -v -m scenario
```

Scenarios require AWS credentials and the relevant stacks deployed in the
same region as the RODA datasets (`us-east-1` recommended). Each scenario's
README lists which stacks are required under **Prerequisites**.
