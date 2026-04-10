# Compute: K-Means Clustering

Use `compute_run` with the `clustering-kmeans` profile to segment
records into groups — then use the results in your code.

## Scenario

You're building a targeted yield campaign and need to segment this
year's admitted students by academic preparation and financial need.

## Tool calls

First, check what the profile expects:

```
compute_profiles

category: "segmentation"
```

Then submit the job:

```
compute_run

profile_id: "clustering-kmeans"
source_uri: "claws://s3-admitted-students-2026"
parameters:
  k: 5
  features: ["high_school_gpa", "sat_total", "efc", "distance_miles"]
  standardize: true
result_label: "yield-segments-2026"
```

## Response

```json
{
  "job_id": "exec-a1b2c3d4",
  "status": "RUNNING",
  "estimated_cost_usd": 0.01,
  "estimated_duration_seconds": 15
}
```

Poll with `compute_status`:

```
compute_status

job_id: "exec-a1b2c3d4"
```

When complete:

```json
{
  "status": "SUCCEEDED",
  "actual_cost_usd": 0.008,
  "duration_seconds": 12,
  "summary": {
    "row_count": 8432,
    "columns": ["high_school_gpa", "sat_total", "efc", "distance_miles",
                "cluster_id", "cluster_distance"]
  },
  "export_urls": {
    "csv": "https://s3.amazonaws.com/...?X-Amz-Signature=...",
    "xlsx": "https://s3.amazonaws.com/...?X-Amz-Signature=..."
  },
  "result_dataset": "qs-compute-yield-segments-2026"
}
```

## How this fits your workflow

You're writing enrollment strategy code in Kiro. The clustering runs
server-side in 12 seconds, and you get back:

1. A Quick Sight dataset with cluster assignments for dashboarding
2. CSV/XLSX download links for local analysis
3. A named snapshot (`yield-segments-2026`) you can compare later

Download the CSV and continue in your notebook:

```python
import pandas as pd

df = pd.read_csv("yield-segments-2026.csv")

# Analyze cluster characteristics
for cluster_id in range(5):
    cluster = df[df["cluster_id"] == cluster_id]
    print(f"Cluster {cluster_id}: n={len(cluster)}, "
          f"mean GPA={cluster['high_school_gpa'].mean():.2f}, "
          f"mean EFC=${cluster['efc'].mean():,.0f}")
```

## Comparing snapshots over time

Next year, run the same clustering and compare:

```
compute_compare

label_a: "yield-segments-2026"
label_b: "yield-segments-2027"
```

Returns added/removed/unchanged row counts and schema diffs — showing
how your admitted class composition shifted year over year.
