# GBIF Species Range Shift Detection

An ecologist uses Quick Suite to detect climate-driven northward range shifts
in species occurrence data from the Global Biodiversity Information Facility
(GBIF). The workflow loads GBIF occurrence records from RODA, enriches each
observation with Census ACS geographic variables to capture landscape context,
and then runs a Spearman correlation analysis to quantify the relationship
between observed latitude and year — the primary signal of poleward range
movement. Two compute jobs run in sequence using the chained `result_uri`
pattern: geo-enrichment first, then correlation analysis on the enriched
output.

**Data source:** GBIF occurrence snapshot on RODA (`s3://gbif-open-data-us-east-1/`).
GBIF aggregates species occurrence records from natural history museums,
citizen science platforms (iNaturalist, eBird), and research surveys
worldwide. Relevant columns: `decimalLatitude`, `decimalLongitude`, `year`,
`species`, `elevation`. The ACS 5-year enrichment adds `median_household_income`
and `population_density` for the census tract containing each observation,
providing a human land-use covariate for modeling.

**Output:** The final `result_uri` from the correlation step is a Parquet file
containing the top-5 pairwise Spearman correlation coefficients and p-values
among `decimalLatitude`, `year`, and `elevation`. A positive, significant
`(year, decimalLatitude)` correlation is the expected range-shift signal. Both
intermediate (enriched occurrences) and final (correlations) results are
stored as named snapshots and retrievable via `compute_snapshots`.

**Prerequisites:** None. GBIF occurrence snapshots and Census ACS data are
publicly accessible. The `geo-enrich` profile calls the Census Bureau's
geocoding and ACS APIs; no additional API keys are required when running via
the campus-compute Lambda target. Enrichment runtime scales with the
number of occurrence records — filtering to a single species or taxon before
loading is recommended for initial runs.
