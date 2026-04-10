# clAWS: Set Up a Proactive Watch

Use `watch` to create a scheduled monitor that runs automatically and
surfaces findings before anyone asks.

## Scenario

You're a junior faculty member who wants to be notified when NIH or NSF
posts new awards in your research area — especially at peer institutions.

## Tool calls

### Step 1: Create a locked plan

Watches execute a locked plan on schedule. First, create the plan that
defines what to search:

```
plan

source_id: "nih_reporter"
objective: "Find new R01 and R21 awards in computational genomics
awarded in the last 30 days"
```

### Step 2: Create the watch

```
watch

plan_id: "plan-9a8b7c6d"
schedule: "rate(7 days)"
watch_type: "new_award"
semantic_match:
  lab_profile_ssm_key: "/quick-suite/lab/chen/profile-abstract"
  abstract_similarity_threshold: 0.82
  abstract_field: "abstract_text"
action_routing:
  destination_type: "sns"
  destination_arn: "arn:aws:sns:us-east-1:123456789012:lab-chen-alerts"
  context_template: "New {source_type} award: {title} (PI: {pi_name}, ${award_amount}). Similarity: {similarity_score}. {draft_text}"
```

Response:
```json
{
  "watch_id": "watch-5e4f3d2c",
  "status": "active",
  "next_run": "2026-04-17T08:00:00Z",
  "schedule": "rate(7 days)"
}
```

### Step 3: Check watch status

```
watches
```

Response:
```json
{
  "watches": [
    {
      "watch_id": "watch-5e4f3d2c",
      "plan_id": "plan-9a8b7c6d",
      "watch_type": "new_award",
      "status": "active",
      "last_run": "2026-04-10T08:00:00Z",
      "last_result": {
        "findings_count": 2,
        "remembered": true
      },
      "next_run": "2026-04-17T08:00:00Z"
    }
  ]
}
```

## What happens on each run

1. The watch runner executes the locked plan against NIH Reporter
2. Each returned award's abstract is scored for semantic similarity
   against your lab profile abstract (stored in SSM Parameter Store)
3. Awards scoring above 0.82 are flagged as findings
4. Router `summarize` drafts a briefing for each finding
5. Findings auto-remember to institutional memory
6. SNS notification dispatches with the context template filled in

No LLM is involved in the query execution — the plan is locked and
immutable. The only LLM calls are for similarity scoring and draft text.

## Five watch types

| Type | What to monitor | Example |
|------|----------------|---------|
| `new_award` | New grants matching your profile | NIH R01s in your field |
| `literature` | New papers matching your research | PubMed/bioRxiv monitoring |
| `cross_discipline` | Adjacent-field papers on your open problems | Materials science papers relevant to your biology problems |
| `compliance` | Rule violations in institutional data | Subject count exceeded, new international site added |
| `accreditation` | Evidence gaps against standards | SACSCOC retention thresholds not met |

## How this fits your workflow

Set up watches once, then forget about them. Findings accumulate in
memory and arrive via SNS. When you start a new session in Kiro:

```
recall

tags: ["new_award"]
since_days: 30
```

You see all new awards discovered in the last month, with similarity
scores, PI names, and award amounts — without having to remember to
search manually.

## Flow triggers

For more complex responses, add a flow trigger to automatically start a
Quick Flows automation when a finding meets criteria:

```
watch

plan_id: "plan-literature-monitor"
schedule: "rate(1 day)"
watch_type: "literature"
flow_trigger:
  delay_minutes: 480
  target_arn: "arn:aws:quicksight:us-east-1:123456789012:automation/weekly-digest"
```

This creates a one-shot EventBridge Scheduler that fires 8 hours after
the finding, triggering a Quick Flows job (e.g., compile a weekly digest
email for the lab).
