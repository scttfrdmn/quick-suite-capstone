# NOAA Climate Trends Forecast

**Who runs this:** Climate scientists, atmospheric researchers, and
environmental science faculty who want to apply time-series forecasting to
NOAA station records without managing local compute or writing a data pipeline.

**What it does:** Searches the Registry of Open Data on AWS for the NOAA
Global Historical Climatology Network (GHCN) daily temperature dataset,
loads it into Quick Sight, and runs a Prophet time-series forecast projecting
maximum daily temperature 24 months forward. A Quick Suite user might ask:
*"Pull NOAA climate data for a station and project temperature trends for the
next two years."* This workflow is what happens behind the scenes.

**Data:** NOAA GHCN Daily on RODA (`s3://noaa-ghcn-pds/`). Over 100,000
global weather stations, observations from 1763 to present, updated daily.
The forecast uses `date` (YYYYMMDD) and `tmax` (maximum temperature in tenths
of a degree C). The Prophet model fits with additive seasonality — appropriate
for climate data where seasonal amplitude is relatively constant — and returns
a 24-month forward projection.

**Output:** A Parquet file at `result_uri` containing `ds` (date), `yhat`
(point forecast), `yhat_lower`, `yhat_upper`, and decomposed trend and
seasonality components. The named snapshot `noaa-ghcn-tmax-24mo-forecast` is
stored in `qs-compute-snapshots` for later retrieval or comparison via
`compute_compare`. Forecast jobs on a single-station subset typically complete
in 3–5 minutes.

**Prerequisites:** None. NOAA GHCN Daily is a public dataset with no access
controls. Set a `department` tag in the run step for spend tracking (e.g.,
`department: "climate-science"`). Stacks required: `data`, `compute`.
