# First-to-Second Year Retention by Cohort and Pell Status

**Who runs this:** Retention analysts, Student Success directors, and
Institutional Research staff preparing accreditation self-studies (HLC, SACSCOC)
or Title IV compliance reports that require disaggregated retention rates by
Pell grant status, cohort year, and program of study.

**What data it needs:** This scenario requires access to institutional Student
Information System (SIS) data stored in an Athena-queryable table via AWS Glue.
The table must include student identifiers, entry term, re-enrollment date (null
if not retained), Pell recipient status, and degree program. Institutional data
setup is required — see the setup notes in `scenario.yaml` for the expected
schema and source registration steps. Student records must be anonymized at the
SIS export layer; clAWS performs an additional PII scan during the probe step
and will flag any unexpected identifiers before the query plan is approved.

**What question it answers:** What percentage of students who entered in each
cohort term re-enrolled in their second year, broken down by Pell grant status
and degree program? This disaggregation is central to equity-focused retention
reporting and to demonstrating Pell gap reduction as required by many regional
accreditors.

**What output it produces:** A retention-cohort analysis result stored in Quick
Sight and as a named snapshot (`retention-cohort-pell`), showing retention rates
and confidence intervals by cohort-term and Pell status group. The raw refined
dataset is also exported to S3 with a full clAWS provenance chain (plan, query,
refinement lineage) suitable for submission as an accreditation evidence artifact.
Results are broken down at the semester grain, enabling trend comparison across
multiple cohort years in a single run.
