# NOAA GHCN Climate Trend Forecast

A climate scientist searches the Registry of Open Data on AWS for NOAA Global
Historical Climatology Network (GHCN) daily temperature records, loads the
dataset into Quick Sight, and runs a Prophet time-series forecast projecting
maximum daily temperature 24 months into the future. The full workflow runs
in Quick Suite using two stacks — quick-suite-data for data discovery and
loading, and quick-suite-compute for the forecast — without requiring any
local compute or data transfer.

**Data source:** NOAA GHCN Daily on RODA (`s3://noaa-ghcn-pds/`). Contains
global station observations from 1763 to present, updated daily. Key columns
used: `date` (YYYYMMDD), `tmax` (maximum temperature in tenths of a degree C).
The `forecast-prophet` compute profile fits a Facebook Prophet model with
additive seasonality and returns a 24-month forward projection with 80%
and 95% confidence intervals.

**Output:** A Parquet result file at the `result_uri` returned by
`compute_status`. Columns include `ds` (date), `yhat` (point forecast),
`yhat_lower`, `yhat_upper`, and the decomposed trend and seasonality
components. The named snapshot `noaa-ghcn-tmax-24mo-forecast` is
retrievable via `compute_snapshots` for comparison runs.

**Prerequisites:** None. NOAA GHCN Daily is a public dataset on RODA with no
access controls. Quick Suite users need compute access to the
`forecast-prophet` profile and a department tag for spend tracking
(`department: "climate-science"` in the run step). Forecast job typically
completes in 3-5 minutes for a single-station subset.
