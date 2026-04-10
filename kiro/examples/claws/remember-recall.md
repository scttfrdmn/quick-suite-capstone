# clAWS: Remember and Recall

Use `remember` to store structured findings in institutional memory, and
`recall` to retrieve them later — across sessions.

## Scenario

You've just completed an analysis that found a significant equity gap in
DFWI rates for a specific department. You want to record this finding so
it's available in future sessions and shows up in the institution's
QuickSight dashboards.

## Tool calls

### Remember a finding

```
remember

record:
  type: "equity_finding"
  severity: "high"
  department: "Chemistry"
  finding: "DFWI rate for first-generation students in CHEM 101 is 34%, vs 18% for continuing-generation. Disparate impact ratio 0.53 (below 80% threshold)."
  source_job_id: "exec-a1b2c3d4"
  tags: ["equity", "dfwi", "chemistry", "first-gen", "accreditation"]
  expires_at: "2027-04-10T00:00:00Z"
```

Response:
```json
{
  "status": "stored",
  "memory_key": "mem-7f8e9d0c",
  "dataset_registered": true
}
```

The `dataset_registered: true` means this is the first write for your
user — the Data extension's `register-memory-source` Lambda
automatically registered the NDJSON file as a QuickSight dataset.
Future writes append to the same file.

### Recall findings

Later — in a different session — retrieve relevant findings:

```
recall

tags: ["equity", "accreditation"]
since_days: 90
severity: "high"
```

Response:
```json
{
  "records": [
    {
      "memory_key": "mem-7f8e9d0c",
      "type": "equity_finding",
      "severity": "high",
      "department": "Chemistry",
      "finding": "DFWI rate for first-generation students in CHEM 101 is 34%...",
      "tags": ["equity", "dfwi", "chemistry", "first-gen", "accreditation"],
      "timestamp": "2026-04-10T14:32:00Z"
    },
    {
      "memory_key": "mem-3a4b5c6d",
      "type": "equity_finding",
      "severity": "high",
      "department": "Mathematics",
      "finding": "DFWI rate for Pell recipients in MATH 201 is 29%...",
      "tags": ["equity", "dfwi", "mathematics", "pell", "accreditation"],
      "timestamp": "2026-03-15T09:18:00Z"
    }
  ],
  "total": 12,
  "filtered": 2
}
```

## How this fits your workflow

Institutional memory solves the "I ran this analysis three months ago"
problem. Findings persist across sessions:

```python
# You're starting a new accreditation self-study
# Recall all equity findings from the past year
findings = recall(tags=["equity", "accreditation"], since_days=365)

# Use them to build the evidence section
for record in findings["records"]:
    print(f"- {record['department']}: {record['finding']}")
```

The findings are also available as a QuickSight dataset — the provost's
equity dashboard can pull directly from the same memory store.

## Automatic memory from watches

You don't have to remember manually. Literature and cross-discipline
watches auto-remember their findings by default:

```
watch

plan_id: "plan-literature-monitor"
schedule: "rate(1 day)"
watch_type: "literature"
semantic_match:
  lab_profile_ssm_key: "/lab/chen/profile-abstract"
  abstract_similarity_threshold: 0.80
```

Every day, the watch fires, scores new papers, and auto-remembers any
that exceed the threshold. Use `recall` to retrieve them:

```
recall

tags: ["literature"]
since_days: 7
query: "CRISPR delivery"
```
