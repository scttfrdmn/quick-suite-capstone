# OpenAQ Air Quality Anomaly Detection

**Who runs this:** Environmental scientists, air quality researchers, and
public health analysts studying pollution episodes. Also useful for data
quality monitoring — distinguishing genuine pollution spikes from sensor faults
requires the same statistical approach.

**What it does:** Discovers and loads OpenAQ air quality measurement records
from RODA, then applies an isolation forest model to flag the 5% most extreme
readings — episodes consistent with wildfire smoke intrusions, industrial
incidents, or sensor malfunctions. A researcher might ask: *"Look at the
OpenAQ data for this city and flag the anomalous air quality readings."*
Quick Suite loads the measurements and returns a ranked list of anomaly events
with continuous scores, ready for follow-on temporal or spatial investigation.

**Data:** OpenAQ on RODA (`s3://openaq-fetches/`). OpenAQ aggregates
continuous air quality measurements from government monitoring networks in
over 90 countries. The primary measurement column is `value` (pollutant
concentration in units specified by `unit`); other relevant columns include
`parameter` (PM2.5, O3, NO2, etc.), `location`, `city`, `country`, `utc`
(timestamp), and `latitude`/`longitude`.

Filter to a consistent monitoring station, city, or pollutant parameter before
loading — mixing units or pollutant types without normalization will confound
the isolation forest model. For example, loading only `parameter=pm25` for a
specific city produces a well-conditioned anomaly score across all observations
at that location.

**Output:** A Parquet file at `result_uri` with all original columns plus
`anomaly_score` (continuous; lower is more anomalous), `is_anomaly` (boolean
flag at the 5% contamination threshold), and `anomaly_rank` (integer rank
within the dataset). The `return_scores: true` parameter includes the
continuous score column, enabling custom thresholds in downstream analysis.
The named snapshot `openaq-pollution-spikes` is stored in
`qs-compute-snapshots` for comparison across time windows or monitoring
locations.

**Prerequisites:** None. OpenAQ is fully public on RODA. Stacks required:
`data`, `compute`.
