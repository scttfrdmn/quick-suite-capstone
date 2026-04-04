# Example Prompts: Compliance Officer

Compliance officers use Quick Suite to detect anomalies in sponsored program spending,
produce equity reports for accreditation bodies, monitor IRB data access, and audit
financial transactions — within policy-gated data access enforced by Cedar and
Bedrock Guardrails.

---

## 1. Sponsored Program Spending Anomalies

**User prompt:**
> "Flag any transactions in our sponsored program accounts that fall outside normal
> spending patterns for the award type and budget period."

**Tools called:**
1. `claws-discover` — find sponsored program transaction table in Athena
2. `claws-probe` — verify schema; check for PII in sample rows
3. `claws-plan` + `claws-excavate` — extract transactions with award type,
   budget period, and amount; Cedar policy enforces `sponsored_programs` domain access
4. `compute_run` (profile: `anomaly-isolation-forest`) — features: `amount`,
   `days_into_period`, `object_code`, `award_type`; `contamination: 0.05`
5. `compute_status`

**What you get:** `is_anomaly` and `anomaly_score` per transaction; top anomalous
transactions ranked by score; ready for sponsor audit export.

---

## 2. Equity Reporting — DFWI Rates for Accreditation

**User prompt:**
> "For our SACSCOC reaffirmation, I need DFWI rates by college and demographic group
> for the last three academic years."

**Tools called:**
1. `claws-discover` — find grade roster in Glue catalog
2. `claws-plan` + `claws-excavate` — extract 3 years of grades with demographic fields
3. `compute_run` (profile: `dfwi-analysis`) — group_by: `college`, `pell_recipient`,
   `urm`, `term`
4. `compute_status`

**What you get:** DFWI rate table by college × demographic × term; overall and
subgroup rates with year-over-year trend; SACSCOC-ready summary output.

---

## 3. IRB Data Access Audit

**User prompt:**
> "Pull the audit log for all clAWS data excavations that touched the IRB-restricted
> student mental health dataset in the last 90 days."

**Tools called:**
1. `claws-discover` — find IRB-restricted source (Cedar policy: `requires_irb: true`)
2. `team_plans` — list all plans referencing the restricted source for the team
3. (Internal) `audit_export` Lambda — retrieves CloudWatch audit records for the
   date range; returns NDJSON with hashed inputs/outputs to `s3://…/audit/`

**What you get:** Chronological log of who ran which plan, when, what data scope,
and estimated cost — no raw PII; SHA-256-hashed inputs/outputs per FERPA requirements.

---

## 4. Chi-Square Test — Demographic Parity in Admissions

**User prompt:**
> "Test whether admission decisions are independent of race/ethnicity category.
> I need a chi-square result for our Title VI compliance file."

**Tools called:**
1. `claws-discover` + `claws-excavate` — pull applicant records with admission
   decision and race/ethnicity; Cedar enforces `admissions` domain access
2. `compute_run` (profile: `chi-square`) — `row_column: race_ethnicity`,
   `col_column: admitted`
3. `compute_status`

**What you get:** Chi-square statistic, p-value, Cramér's V effect size; observed
and expected contingency tables; ready for Title VI documentation.

---

## 5. Change Detection — When Did Sponsored Spending Pattern Shift?

**User prompt:**
> "Our NSF grant had a no-cost extension in Year 3. Detect whether the spending
> pattern structurally changed at that point compared to the original period."

**Tools called:**
1. `claws-excavate` — pull monthly spending totals for the award
2. `compute_run` (profile: `change-detection`) — `model: l2`, `min_segment_length: 2`
3. `compute_status`

**What you get:** `change_point: true` rows at detected structural break dates;
`segment_id` separates pre- and post-extension spending regimes; supports
sponsor closeout narrative.

---

## 6. Equity Gap — Financial Aid Award Distribution

**User prompt:**
> "Check whether the distribution of institutional grant aid is equitable across
> first-generation and Pell-recipient student populations."

**Tools called:**
1. `claws-discover` + `claws-excavate` — pull financial aid award records
2. `compute_run` (profile: `equity-gap`) — `metric_column: institutional_grant_amt`,
   `group_columns: ["first_gen", "pell_recipient"]`, `reference_group: "no"`
3. `compute_status`

**What you get:** Group-level mean award amounts, equity indices relative to
continuing-generation/non-Pell baseline; gap table flagging groups below 0.90
equity threshold for Title IV reporting.
