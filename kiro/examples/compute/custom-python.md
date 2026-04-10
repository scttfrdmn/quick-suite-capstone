# Compute: Custom Python Analysis

Use `compute_run` with the `custom-python` profile to run your own
Python script against a dataset — in a RestrictedPython sandbox with
governed execution.

## Scenario

You need an analysis that doesn't match any of the 41 built-in profiles.
You're writing a custom enrollment yield model with institution-specific
business rules. You want to iterate on the script in Kiro and submit it
for execution against production data.

## Writing the script

In Kiro, write your transform function in a file:

```python
# yield_model.py

def transform(df):
    """
    Custom yield model with institution-specific business rules.
    
    Input: admitted students with columns:
      admit_type, hs_gpa, sat_total, efc, distance_miles,
      campus_visit, financial_aid_offered
    
    Output: same rows + yield_score, yield_tier
    """
    import pandas as pd
    import numpy as np
    
    # Institution-specific weights (calibrated from prior years)
    weights = {
        "hs_gpa": 0.20,
        "sat_total": 0.15,
        "efc_normalized": 0.10,
        "distance_score": 0.15,
        "visit_score": 0.25,
        "aid_gap_score": 0.15,
    }
    
    # Normalize features
    df["hs_gpa_norm"] = df["hs_gpa"] / 4.0
    df["sat_norm"] = df["sat_total"] / 1600
    df["efc_normalized"] = 1 - (df["efc"].clip(upper=50000) / 50000)
    df["distance_score"] = 1 / (1 + df["distance_miles"] / 100)
    df["visit_score"] = df["campus_visit"].astype(float)
    df["aid_gap_score"] = (
        df["financial_aid_offered"] / df["efc"].replace(0, 1)
    ).clip(upper=2) / 2
    
    # Weighted composite
    df["yield_score"] = sum(
        weights[k] * df[k.replace("efc_normalized", "efc_normalized")
                          .replace("distance_score", "distance_score")
                          .replace("visit_score", "visit_score")
                          .replace("aid_gap_score", "aid_gap_score")]
        for k in weights
        if k in df.columns or k.replace("_score", "") in df.columns
    )
    
    # Tier assignment
    df["yield_tier"] = pd.cut(
        df["yield_score"],
        bins=[0, 0.3, 0.5, 0.7, 1.0],
        labels=["unlikely", "possible", "likely", "very_likely"]
    )
    
    return df
```

Upload to S3:

```bash
aws s3 cp yield_model.py s3://qs-compute-scripts/yield_model.py
```

## Tool call

```
compute_run

profile_id: "custom-python"
source_uri: "claws://s3-admitted-students-2026"
parameters:
  script_uri: "s3://qs-compute-scripts/yield_model.py"
result_label: "yield-scores-2026"
```

## What happens under the hood

1. The script is downloaded from S3
2. It runs in a **RestrictedPython sandbox** — no network access, no
   file system access, no `import os` or `import subprocess`
3. `_SafePandasProxy` blocks URL-based `read_*` calls (no
   `pd.read_csv("http://...")`)
4. The `transform(df)` function receives the dataset as a DataFrame
5. Results are delivered to Quick Sight and S3

## How this fits your workflow

This is the most natural Kiro workflow: write code in the editor, test
locally with a sample, submit for execution against the full dataset.
The RestrictedPython sandbox means your script can't do anything
dangerous — it can only transform the DataFrame it receives.

**Iterate locally first:**

```python
# test_yield_model.py — run locally in Kiro
import pandas as pd
from yield_model import transform

sample = pd.read_csv("sample_admitted.csv")
result = transform(sample)
print(result[["hs_gpa", "yield_score", "yield_tier"]].head(10))
```

Then submit the production run via `compute_run` when you're satisfied.

## custom-generated alternative

If you'd rather describe what you want in plain language and let an LLM
write the script:

```
compute_run

profile_id: "custom-generated"
source_uri: "claws://s3-admitted-students-2026"
parameters:
  description: "Calculate a yield score from 0-1 based on GPA (20%),
  SAT (15%), EFC inverse (10%), distance inverse (15%), campus visit
  (25%), and aid-to-need ratio (15%). Assign tiers: unlikely (<0.3),
  possible (0.3-0.5), likely (0.5-0.7), very likely (>0.7)."
```

The Router generates the Python code, AST static analysis validates it,
and it runs in the same RestrictedPython sandbox.
