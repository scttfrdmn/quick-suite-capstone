# Data: Search Public Datasets

Use `roda_search` to find datasets in the Registry of Open Data on AWS
— 500+ curated public datasets searchable by keyword, tag, or format.

## Scenario

You're writing a climate analysis script and need historical temperature
data. You know NOAA has something on RODA but don't know the exact
dataset name or S3 path.

## Tool call

```
roda_search

query: "NOAA historical temperature daily observations"
format: "parquet"
max_results: 5
```

## Response includes

```json
{
  "count": 3,
  "datasets": [
    {
      "slug": "noaa-ghcn-pds",
      "title": "NOAA Global Historical Climatology Network Daily",
      "description": "Daily climate summaries from 100,000+ stations worldwide",
      "tags": ["climate", "weather", "noaa", "temperature"],
      "formats": ["csv", "parquet"],
      "s3_bucket": "noaa-ghcn-pds",
      "quality_score": 0.92,
      "last_verified": "2026-04-03"
    }
  ]
}
```

## How this fits your workflow

You're writing a forecast script in Kiro. Instead of tabbing over to
the RODA website, searching, finding the S3 path, and figuring out the
schema, you search from the editor. The response tells you the bucket
name and quality score. You can follow up with `s3_preview` to see
actual columns:

```
s3_preview

bucket: "noaa-ghcn-pds"
key: "parquet/by-station/USW00094728.parquet"
max_rows: 5
```

Then use the column names directly in your code:

```python
df = pd.read_parquet("s3://noaa-ghcn-pds/parquet/by-station/USW00094728.parquet")
forecast = compute_run(
    profile_id="forecast-prophet",
    source_uri="s3://noaa-ghcn-pds/parquet/by-station/USW00094728.parquet",
    parameters={"date_column": "DATE", "value_column": "TMAX", "periods": 24}
)
```
