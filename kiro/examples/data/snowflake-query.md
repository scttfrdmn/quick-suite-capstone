# Data: Query Snowflake

Use `snowflake_query` to run parameterized, read-only SQL against a
Snowflake data warehouse — directly from Kiro, with mutation detection
and row limits.

## Scenario

You're writing an enrollment model and need current-term registration
counts from your institution's Snowflake warehouse.

## Tool calls

First, browse available tables:

```
snowflake_browse

source_label: "registrar-warehouse"
schema: "ENROLLMENT"
```

Response:
```json
{
  "tables": [
    {"name": "REGISTRATIONS", "row_count": 2450000, "columns": 28},
    {"name": "COURSE_SECTIONS", "row_count": 45000, "columns": 15},
    {"name": "TERM_CALENDAR", "row_count": 120, "columns": 8}
  ]
}
```

Then preview the schema:

```
snowflake_preview

source_label: "registrar-warehouse"
table: "ENROLLMENT.REGISTRATIONS"
max_rows: 5
```

Response includes column names, types, sample data, and quality metrics
(null %, cardinality, duplicate %).

Now run a targeted query:

```
snowflake_query

source_label: "registrar-warehouse"
query: "SELECT TERM_CODE, STUDENT_LEVEL, COUNT(*) as headcount
        FROM ENROLLMENT.REGISTRATIONS
        WHERE TERM_CODE = ?
        GROUP BY TERM_CODE, STUDENT_LEVEL"
bindings: ["202610"]
```

## Response includes

```json
{
  "columns": ["TERM_CODE", "STUDENT_LEVEL", "HEADCOUNT"],
  "rows": [
    ["202610", "UG", 18432],
    ["202610", "GR", 4201],
    ["202610", "ND", 892]
  ],
  "row_count": 3
}
```

## How this fits your workflow

You're building an enrollment forecast model in Kiro. Instead of
opening a Snowflake client, writing the query, exporting to CSV, and
loading it — you query directly, see the shape of the data, and feed
it into your analysis:

```python
# Enrollment data from Snowflake query above
enrollment = {"UG": 18432, "GR": 4201, "ND": 892}

# Now run a forecast against the full time series
result = compute_run(
    profile_id="forecast-prophet",
    source_uri="claws://snowflake-enrollment-history",
    parameters={
        "date_column": "TERM_START_DATE",
        "value_column": "HEADCOUNT",
        "periods": 8
    }
)
```

## Per-caller credentials

If your institution uses per-user Snowflake credentials rather than a
shared service account:

```
snowflake_query

source_label: "registrar-warehouse"
query: "SELECT ..."
caller_secret_arn: "arn:aws:secretsmanager:us-east-1:123456789012:secret:my-snowflake-creds"
```

The ARN is validated against an allowlist prefix — you can only use
Secrets Manager ARNs that your administrator has pre-approved.
