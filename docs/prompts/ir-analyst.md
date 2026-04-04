# Example Prompts: IR Analyst

Institutional Research analysts use Quick Suite to produce accreditation reports,
equity studies, enrollment projections, and peer benchmarking — without writing SQL
or managing infrastructure.

---

## 1. First-to-Second Year Retention by Cohort

**User prompt:**
> "Show me first-to-second year retention rates for the 2021 and 2022 entry cohorts,
> broken out by Pell grant status and degree program."

**Tools called (in order):**
1. `claws-discover` — find the student enrollment/retention table in Glue catalog
2. `claws-probe` — verify schema has cohort, re-enrollment, and Pell columns
3. `claws-plan` — plan query to extract cohort records with Pell status
4. `claws-excavate` — execute the plan
5. `claws-refine` — deduplicate
6. `claws-export` — stage to S3
7. `compute_run` (profile: `retention-cohort`) — build cohort retention matrix
8. `compute_status` — poll until complete

**What you get:** Semester-by-semester retention matrix per cohort × Pell group;
attrition rates by stage; long-form table ready for Quick Sight dashboard.

---

## 2. Equity Gap Analysis — GPA by First-Generation Status

**User prompt:**
> "Are there equity gaps in student GPA between first-generation and continuing-generation
> students in the College of Engineering?"

**Tools called:**
1. `compute_run` (profile: `equity-gap`) — direct S3 source with student outcome data
2. `compute_status` — poll until complete

**What you get:** Group-level mean GPA, equity index (ratio to reference group),
gap magnitude ranked by subgroup; flags groups below 0.90 equity threshold.

---

## 3. DFWI Rate Trend — Course-Level Equity Review

**User prompt:**
> "Which courses in the College of Arts and Sciences had DFWI rates above 25% last
> semester? Break it out by instructor and section."

**Tools called:**
1. `claws-discover` — find grade roster in Athena
2. `claws-probe` — confirm grade column and department
3. `claws-plan` + `claws-excavate` — extract grades for CAS courses last semester
4. `compute_run` (profile: `dfwi-analysis`) — compute DFWI rates by course/instructor
5. `compute_status`

**What you get:** Per-course DFWI rates, section-level breakdown, overall department
summary; `is_dfwi` flag on each grade record for downstream filtering.

---

## 4. Enrollment Forecast — 3-Year Headcount Projection

**User prompt:**
> "Project enrollment headcount by college for the next 3 academic years, using the
> last 10 years of historical data."

**Tools called:**
1. `claws-discover` — find historical headcount table
2. `claws-plan` + `claws-excavate` — pull 10-year term enrollment series
3. `compute_run` (profile: `forecast-prophet`) — run Prophet forecast per college
4. `compute_status`

**What you get:** 3-year forecasted headcount with 80% and 95% confidence intervals,
trend and seasonality components, per-college series in Quick Sight.

---

## 5. Peer Benchmarking — Graduation Rates vs. Aspirational Peers

**User prompt:**
> "Compare our 6-year graduation rate against our 10 aspirational peer institutions
> using the IPEDS dataset. Mark us as the focal institution."

**Tools called:**
1. `roda_search` — find IPEDS graduation rates dataset
2. `roda_load` — load into Quick Sight
3. `compute_run` (profile: `peer-benchmark`) — z-scores and percentile ranks;
   `focal_id` set to institution's UNITID
4. `compute_status`

**What you get:** Z-score and percentile rank vs. peer set for each metric;
`is_focal = true` row with full peer comparison table.

---

## 6. Seasonality in Financial Aid Applications

**User prompt:**
> "Decompose the monthly financial aid application volume time series to separate
> the seasonal filing spike from the underlying trend."

**Tools called:**
1. `claws-discover` + `claws-excavate` — pull monthly FAFSA/application counts
2. `compute_run` (profile: `seasonality-decompose`) — STL decomposition, period=12
3. `compute_status`

**What you get:** Trend, seasonal, and residual columns appended to the time series;
isolates the March–April filing spike from the multi-year enrollment trend.
