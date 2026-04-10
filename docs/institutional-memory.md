# Institutional Memory

Quick Suite has no persistent memory by design — every session starts fresh. This means findings
from watch runner alerts, literature surveillance, or previous analysis sessions evaporate when
the browser tab closes. The institutional memory layer adds persistence using infrastructure
Quick Suite already understands: S3-backed data registered as a QuickSight dataset.

---

## What the Memory Layer Is

Memory records are stored as NDJSON in an S3 bucket (`claws-memory-{ACCOUNT_ID}`). On the first
write for a user, the file is registered as a QuickSight dataset via the `register-memory-source`
Lambda in quick-suite-data. Quick Index auto-discovers this dataset on its next crawl, making the
records queryable in Quick Suite chat alongside any other dataset.

```
claws.remember (write)
    │
    ▼
s3://claws-memory-{ACCOUNT_ID}/{account_id}/{user_arn_hash}/findings.jsonl
    │
    ▼ (registered once as QuickSight dataset)
Quick Index crawl → queryable in Quick Suite chat
    │
    ▼
claws.recall (read) / "what happened while I was away?"
```

Each memory record carries:

| Field | Description |
|-------|-------------|
| `memory_id` | Unique ID for this finding |
| `subject` | One-line summary of what was found |
| `fact` | Full finding — free text or structured |
| `confidence` | 0.0–1.0 |
| `tags` | List of topic tags (e.g. `["reagent", "critical"]`) |
| `severity` | `critical`, `warning`, or `informational` |
| `source_plan_id` | The clAWS plan that produced this finding |
| `recorded_at` | ISO-8601 timestamp |
| `expires_at` | Optional TTL — `recall` filters expired records |
| `team_id` | Optional — makes the record visible to team members |

---

## What Writes to Memory

**1. Explicit `claws.remember` call**

The Quick Suite agent or a user calls `claws.remember` directly during a session:

```
"Remember that the anti-GAPDH clone 6C5 antibody showed cross-reactivity in the 
 Western blot from run-abc123. Tag it critical and link it to that plan."
```

**2. Watch runner auto-remember** *(clAWS v0.17.0)*

Watches with `memory_config.auto_remember: true` write to the memory store automatically when
they fire. Science alert watches (literature surveillance, cross-discipline signal detection)
default to this behavior. The watch runner formats the `subject` from a template, writes the
diff summary as `fact`, and calls the memory write path without requiring user interaction.

Watch field:
```yaml
memory_config:
  auto_remember: true
  severity: critical
  subject_template: "Watch {watch_id}: {diff_summary.added_count} new results in {source_id}"
```

**3. Export hook** *(planned)*

`claws.export` with `remember: true` writes a provenance summary to memory after data export —
useful when sharing results with colleagues or filing them for later reference.

---

## What Reads Memory

**1. `claws.recall` tool**

Direct query from Quick Suite chat. Supports structural and semantic filters:

```
"What critical reagent findings have been recorded in the last 30 days?"
→ claws.recall: { severity: ["critical"], since_days: 30, limit: 20 }
```

Returns `records` list sorted by `recorded_at` descending, with expired records filtered out.
Team-scoped records are included when the caller's `team_id` matches.

**2. Quick Suite dataset query**

Because the memory file is registered as a QuickSight dataset, Quick Suite's agent can query it
directly using natural language the same way it queries any other dataset:

```
"What do I have pending from the last week?"
"Show me everything tagged reagent that's still open."
```

No special tool call needed — Quick Index makes the dataset discoverable.

**3. Session initialization flows**

The `recall-brief` and `morning-brief` Quick Flows templates run `claws.recall` automatically
and synthesize a digest with `router.summarize`. Use them to bootstrap a session with context
from what happened while you were away. See [`docs/workflows/`](workflows/).

---

## The Push Pattern

Quick Suite is a reactive system — it answers questions but cannot push notifications. The
memory layer needs a way to alert users when something significant is recorded, without requiring
them to be in an active session.

**What doesn't work (verified April 2026):**

- **Quick Suite memory (Dec 2025)** — UI-only, inference-based user preferences. No external
  write API; tools cannot write to it.
- **AgentCore Memory API** (`BatchCreateMemoryRecords`) — separate system; writes do NOT surface
  in Quick Suite chat sessions.
- **`GenerateEmbedUrlForRegisteredUser` / `QuickChat`** — the `QuickChat: {}` experience type
  has zero parameters. No `InitialQuery` option exists on any embedding experience type. Deep-link
  pre-population of a chat question is not possible.

**What works — T+x scheduling:**

When the watch runner writes a critical finding to memory, it can schedule a one-shot Quick Flow
execution using EventBridge Scheduler's `at(timestamp)` expression:

```
watch fires → claws.remember (finding persisted)
    │
    └── EventBridge Scheduler: at(now + N minutes)
            → QuickSight start_automation_job: "recall-brief"
                → claws.recall → router.summarize → EventBridge
                    → SNS rule → email/Slack
```

`start_automation_job` is a QuickSight API operation (`boto3.client('quicksight').start_automation_job(...)`)
that triggers a Quick Flow programmatically. The EventBridge Scheduler schedule uses
`ActionAfterCompletion: DELETE` to auto-clean after firing.

The user gets an email within minutes of the alert. When they open Quick Suite, the memory
record is already there and queryable. They don't need to know a flow was triggered.

Watch field:
```yaml
flow_config:
  flow_id: recall-brief
  delay_minutes: 5
  input:
    severity_filter: ["critical", "warning"]
```

---

## Setup

### 1. Deploy quick-suite-data with memory registration

The `register-memory-source` Lambda must be deployed first — it registers the S3 NDJSON file
as a QuickSight dataset when `claws.remember` is called for the first time.

```bash
cd quick-suite-data
uv run cdk deploy --context memory_registrar_export=true
```

Note the `MemoryRegistrarArn` CloudFormation output:
```bash
aws cloudformation describe-stacks --stack-name QuickSuiteData \
  --query 'Stacks[0].Outputs[?OutputKey==`MemoryRegistrarArn`].OutputValue' \
  --output text
```

### 2. Deploy quick-suite-claws with memory bucket and registrar ARN

```bash
cd quick-suite-claws
uv run cdk deploy \
  --context memory_registrar_arn=arn:aws:lambda:us-east-1:123456789012:function:qs-data-register-memory-source
```

This creates the `claws-memory-{ACCOUNT_ID}` S3 bucket and wires `MEMORY_REGISTRAR_ARN` into
the `remember` Lambda. Cedar policies for `claws.remember` and `claws.recall` are included in
the default policy set.

### 3. Configure the recall-brief flow in Quick Suite

In the Quick Suite admin console:
1. Navigate to **Quick Flows → Import**
2. Upload `docs/workflows/recall-brief.yaml` from this repo
3. Set the flow ID to `recall-brief` (must match `flow_id` in watch `flow_config`)
4. Optionally import `docs/workflows/morning-brief.yaml` for the scheduled digest

### 4. Create the EventBridge → SNS routing rule

Memory briefs fire an EventBridge event with `detail-type: ClawsMemoryBrief`. Route this to
an SNS topic subscribed to user email or Slack:

```json
{
  "source": ["claws.memory"],
  "detail-type": ["ClawsMemoryBrief"]
}
```

```bash
aws events put-rule \
  --name ClawsMemoryBriefToSNS \
  --event-pattern '{"source":["claws.memory"],"detail-type":["ClawsMemoryBrief"]}' \
  --state ENABLED

aws events put-targets \
  --rule ClawsMemoryBriefToSNS \
  --targets "Id=SNS,Arn=arn:aws:sns:us-east-1:123456789012:claws-alerts"
```

### 5. First write

On the first `claws.remember` call, the `register-memory-source` Lambda is invoked
automatically. Quick Index picks up the new dataset on its next crawl (typically within an
hour). After that, the memory file is queryable from Quick Suite chat.

---

## Example: Antibody Alert End-to-End

A researcher has a living literature watch (`watch-a1b2c3d4`) scanning PubMed for papers
about GAPDH antibody cross-reactivity. The watch runs nightly.

**Tuesday night, 2:17 AM:**
The watch runner detects two new papers added to the PubMed index. One describes cross-reactivity
of anti-GAPDH clone 6C5 with a 50 kDa off-target band in HeLa lysate — directly relevant to
the researcher's ongoing Western blot work.

Because the watch has `memory_config.auto_remember: true` and `severity: critical`, the runner:
1. Writes to `s3://claws-memory-.../findings.jsonl`:
   ```json
   {"memory_id": "mem-f8a2c1e3", "subject": "GAPDH 6C5 cross-reactivity in HeLa lysate",
    "fact": "New paper (PMID 40123456) reports 50 kDa off-target band with clone 6C5...",
    "severity": "critical", "tags": ["reagent", "antibody", "published-figure"],
    "source_plan_id": "plan-a1b2c3", "recorded_at": "2026-04-08T02:17:44Z"}
   ```
2. Schedules a one-shot EventBridge rule at 2:22 AM: `start_automation_job("recall-brief")`

**Tuesday night, 2:22 AM:**
The `recall-brief` flow fires automatically:
- `claws.recall` retrieves the new critical finding
- `router.summarize` writes: *"Critical reagent alert (recorded 2:17 AM): New publication
  reports anti-GAPDH clone 6C5 cross-reactivity with a 50 kDa off-target in HeLa lysate
  (PMID 40123456). Review before next Western blot run."*
- EventBridge event fires → SNS → email arrives in the researcher's inbox

**Wednesday morning:**
The researcher opens Quick Suite and types: *"What happened with the GAPDH watch overnight?"*

Quick Suite queries the memory dataset: the record from 2:17 AM is returned. The researcher
can then call `claws.recall` for full context, probe the source plan, or run a new analysis
against the referenced paper.

The finding persists until it expires (`expires_days: 90`) or the researcher marks it resolved.

---

## Architecture Reference

```
                    quick-suite-data
                    ┌──────────────────────────────────┐
                    │  register-memory-source Lambda   │
                    │  (QuickSight CreateDataSource/   │
                    │   CreateDataSet/CreateIngestion) │
                    └────────────────┬─────────────────┘
                                     │ (invoked on first write)
          quick-suite-claws          │
          ┌──────────────────────────▼────────────────────────────┐
          │                                                        │
          │  claws.remember ──► s3://claws-memory-{ACCT}/         │
          │                         findings.jsonl                │
          │  claws.recall   ◄── (filter + scope)                  │
          │                                                        │
          │  watch runner ─────────────────────────────────────►  │
          │   (auto_remember)   EventBridge Scheduler             │
          │                         at(now+5min)                  │
          └────────────────────────────────────────────────────── ┘
                                     │
                    QuickSight start_automation_job
                                     │
                    recall-brief flow
                    ├── claws.recall
                    ├── router.summarize
                    └── claws.export → EventBridge → SNS → email

          Quick Index crawl
          ┌────────────────────────────────────────┐
          │  s3://claws-memory → QuickSight dataset │
          │  discoverable in Quick Suite chat       │
          └────────────────────────────────────────┘
```
