# Research Computing Persona — Example Prompts

Target user: research computing director, research office analyst, or faculty
researcher at an R1 university. Familiar with sponsored programs administration,
bibliometrics, and scientific data formats (NetCDF, GeoJSON). Wants to analyze
research portfolios, publication networks, and scientific datasets without standing
up infrastructure or writing pipeline code.

---

## 1. Grant Portfolio Burn Rate and NCE Risk

**Prompt:**
> Our sponsored programs office needs to review the current state of all active
> awards before the fiscal year closes. Pull the expenditure transaction data from
> our institutional data warehouse, compute the burn rate per award, and flag any
> awards that have spent more than 90% of their budget — those are NCE candidates
> that need PI attention. Include a PI-level summary showing how many awards each
> PI has at risk.

**What Quick Suite does:**
Runs clAWS discover → probe → plan → excavate → export, then calls `compute_run`
with `profile_id: grant-portfolio`, `nce_threshold: 0.90`, and `pi_column` set to
the PI identifier. The result dataset contains `burn_rate`, `pct_expended`, and
`nce_risk` columns merged to every transaction row, plus a PI summary in diagnostics.

---

## 2. Faculty Co-authorship Network

**Prompt:**
> I want to understand the collaboration landscape in our College of Engineering.
> We have a publications table in the data catalog with a semicolon-separated
> author list per publication. Build the co-authorship network, compute degree
> and betweenness centrality for each faculty member, and detect collaboration
> communities. Who are the key connectors bridging different research clusters?

**What Quick Suite does:**
Runs clAWS to extract the publications table, then `compute_run` with
`profile_id: network-coauthor`, `author_column: authors`,
`publication_id_column: pub_id`, `min_collaborations: 2`. Diagnostics include
`top_authors_by_degree` and `n_communities`. The result is one row per
(author, publication) with `degree_centrality`, `betweenness_centrality`,
and `community_id`.

---

## 3. NetCDF Climate Data → 24-Month Forecast

**Prompt:**
> I have a NetCDF4 file of 10-year monthly maximum temperature observations from
> our campus weather station stored in S3 at s3://research-data/station-tmax.nc.
> Flatten the data to a table and immediately run a 24-month Prophet forecast so
> I can see projected temperature trends for our infrastructure planning report.

**What Quick Suite does:**
Calls `compute_run` with `profile_id: ingest-netcdf`, `source_uri` pointing to
the .nc file, and `chain_profile_id: forecast-prophet` with
`chain_parameters: {date_column: time, value_column: tmax, forecast_horizon: 24}`.
The two profiles run in sequence in a single Step Functions execution. The final
output is a forecast DataFrame with confidence intervals.

---

## 4. PDF Document Text Extraction → Sentiment Analysis

**Prompt:**
> We have 300 pages of accreditation self-study PDFs uploaded to
> s3://institutional-docs/self-study-2025.pdf. Extract the text page by page
> and score the sentiment of each page — I want to know which sections read as
> negative or neutral so we can identify areas where reviewers may flag concerns.

**What Quick Suite does:**
Calls `compute_run` with `profile_id: ingest-pdf-extract`,
`chain_profile_id: text-sentiment`, `chain_parameters: {text_column: text, output_scores: true}`.
Pages shorter than 100 characters are filtered automatically. The final dataset
has `page_number`, `text`, `sentiment`, and `compound_score` per page.

---

## 5. Custom Python Transform on Award Data

**Prompt:**
> I have a Python script at s3://research-scripts/normalize_award_periods.py that
> converts our award period fields to fiscal-year quarters and computes a
> days-remaining column. I want to run it against the expenditure data we extracted
> earlier without uploading the data anywhere new. The script defines a
> transform(df) function.

**What Quick Suite does:**
Calls `compute_run` with `profile_id: custom-python`,
`source_uri` pointing to the expenditure data, and
`parameters: {script_uri: s3://research-scripts/normalize_award_periods.py}`.
The script runs in a RestrictedPython sandbox with pd and np available.
The generated output is returned as the job result dataset.

---

## 6. AI-Generated Analysis from Natural Language

**Prompt:**
> I don't have a script ready, but I want to compute the 3-month rolling average
> of expenditure_usd grouped by pi_id and flag months where any PI's spend exceeds
> 1.5× their rolling average. Write the analysis and run it on our expenditure data.

**What Quick Suite does:**
Calls `compute_run` with `profile_id: custom-generated` and
`objective: "Compute 3-month rolling average of expenditure_usd grouped by pi_id.
Add a flag column spike_flag=True when expenditure_usd > 1.5 * rolling average."`.
The router `code` tool generates a `transform(df)` script, stores it to S3 for
audit, and executes it in the RestrictedPython sandbox. The generated script URI
is returned in diagnostics for review.

---

## 7. GeoJSON Campus Boundary Ingest for Spatial Analysis

**Prompt:**
> Our GIS team uploaded a GeoJSON file of campus building footprints to
> s3://campus-gis/buildings.geojson. I need to convert it to a flat table with
> the building properties and WKT geometry so I can join it with our space
> utilization dataset in Quick Sight. Include bounding box columns for each building.

**What Quick Suite does:**
Calls `compute_run` with `profile_id: ingest-geojson`,
`source_uri: s3://campus-gis/buildings.geojson`,
`parameters: {include_bbox: true}`. Each GeoJSON feature becomes one row
with all property columns (building name, use type, square footage, etc.)
plus `geometry_wkt`, `bbox_minx`, `bbox_miny`, `bbox_maxx`, `bbox_maxy`.
The result registers directly as a Quick Sight dataset for spatial joins.
