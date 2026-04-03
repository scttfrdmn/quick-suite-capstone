# OpenAQ Air Quality Anomaly Detection

An environmental scientist uses Quick Suite to detect pollution spike events
in continuous air quality monitoring data from OpenAQ. The workflow discovers
and loads OpenAQ measurement records from RODA, then applies an isolation
forest anomaly detection model targeting the 5% most extreme readings —
episodes consistent with wildfire smoke, industrial incidents, or sensor
faults. The returned anomaly scores and flags enable follow-on temporal and
spatial investigation without any local infrastructure.

**Data source:** OpenAQ on RODA (`s3://openaq-fetches/`). OpenAQ aggregates
air quality measurements from government monitoring networks in over 90
countries, updated continuously. The primary measurement column is `value`
(pollutant concentration in the units specified by `unit`); other useful
columns include `parameter` (PM2.5, O3, NO2, etc.), `location`, `city`,
`country`, `utc` (timestamp), and `latitude`/`longitude`. Filtering to a
single `parameter` (e.g., `pm25`) before loading is recommended to keep the
anomaly model well-conditioned.

**Output:** The `anomaly-isolation-forest` profile returns a Parquet file at
`result_uri` with all original columns plus `anomaly_score` (continuous, lower
is more anomalous), `is_anomaly` (boolean flag), and `anomaly_rank` (integer
rank within the dataset). The top-ranked records by `anomaly_score` represent
the detected pollution spike events. The `return_scores: true` parameter
ensures the continuous score column is included, enabling researchers to
apply custom thresholds in downstream analysis.

**Prerequisites:** None. OpenAQ is a fully public RODA dataset. For
meaningful anomaly detection, filter the dataset to a consistent monitoring
station, city, or pollutant parameter before running the workflow — mixing
units or pollutant types without normalization will confound the isolation
forest. The named snapshot `openaq-pollution-spikes` is stored in
`qs-compute-snapshots` for comparison across time windows or locations.
