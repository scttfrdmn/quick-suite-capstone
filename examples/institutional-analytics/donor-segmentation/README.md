# Alumni Donor Segmentation (K-Means)

**Who runs this:** Advancement analytics teams, major gifts officers, and
Annual Fund directors who need to segment their alumni giving population for
targeted stewardship, solicitation strategy, and portfolio assignment.

**What data it needs:** This scenario requires access to an institutional alumni
giving database stored in an Athena-queryable table via AWS Glue. The table
must include individual gift transactions with donor identifiers, gift dates,
amounts, fund codes, and solicitation types. Institutional data setup is
required — see `scenario.yaml` for the expected schema. The clAWS plan step
aggregates raw gift transactions into per-donor RFM (Recency, Frequency,
Monetary) signals before clustering; the raw transaction table is never
exported directly. A minimum of 500 distinct donors is recommended for stable
k=4 cluster separation.

**What question it answers:** Given five years of alumni giving history, which
natural donor segments emerge based on total lifetime giving, gift frequency,
recency of last gift, and largest single gift? K-means with k=4 typically
surfaces segments corresponding to lapsed donors, consistent annual-fund
donors, mid-level prospects, and major gift candidates — though the actual
cluster boundaries are data-driven, not hand-labeled.

**What output it produces:** A Quick Sight dataset and named snapshot
(`donor-segments-kmeans-k4`) containing each donor's cluster assignment (0-3)
alongside their RFM feature values. The snapshot is immediately usable in a
Quick Sight analysis to profile each segment by average giving, gift frequency,
and years of engagement. The major gifts team receives a filtered view of
cluster members whose profiles match major gift thresholds, while the Annual
Fund team can target lapsed-donor segments with re-engagement messaging.
The full provenance chain from clAWS is preserved in the export record.
