# Sponsored Program Expenditure Anomaly Detection

**Who runs this:** Research compliance officers, sponsored programs
administrators, and post-award finance staff at research universities who are
responsible for monitoring award burn rates, identifying potential financial
misuse, and preparing for federal agency audits (NSF, NIH, DOE) that require
documented internal controls over sponsored expenditures.

**What data it needs:** This scenario requires sponsored programs expenditure
data in an Athena-queryable table via AWS Glue, with monthly expenditure
records per award including budget totals and award end dates. Institutional
data setup is required — see `scenario.yaml` for the expected schema and Glue
registration steps. The clAWS plan step computes derived features
(`monthly_pct_of_budget`, `days_to_expiration`) directly in the Athena query,
so these do not need to be pre-calculated in the source table. The compliance
team's IAM principal must hold the "read" clAWS Cedar action for the sponsored
programs domain; access is enforced at the Gateway boundary before any query
executes.

**What question it answers:** Which awards show statistically unusual
expenditure patterns relative to their budget size and time-to-expiration?
Isolation Forest is well-suited to this problem because it does not require
labeled examples of misuse — it learns the distribution of normal burn
patterns across all active awards and scores outliers based on how easily they
can be isolated. A contamination parameter of 0.03 flags approximately the top
3% most anomalous expenditure records, which at most institutions corresponds
to a manageable review queue of 15-30 awards per quarter rather than an
unworkable alert flood.

**What output it produces:** An anomaly detection result stored as a Quick
Sight snapshot (`grant-anomalies-isolation-forest`) containing each award's
anomaly score, a binary anomaly flag, and the original feature values
(monthly spend percentage, days to expiration, expenditure amount). The
`return_scores: true` parameter ensures continuous scores are returned alongside
binary flags, allowing the compliance team to rank flagged awards by severity
rather than treating all flagged records equally. The S3 export with provenance
chain provides an audit-ready artifact documenting exactly which records were
analyzed, when the analysis ran, and the query plan that produced the input
data.
