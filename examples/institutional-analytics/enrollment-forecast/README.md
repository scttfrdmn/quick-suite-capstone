# Enrollment Headcount Forecast (IPEDS)

**Who runs this:** Institutional Research directors and enrollment planning
analysts preparing multi-year headcount projections for budget planning,
accreditation self-studies, or provost briefings.

**What data it needs:** No institutional data setup is required. This scenario
pulls directly from the publicly available IPEDS (Integrated Postsecondary
Education Data System) enrollment headcount dataset hosted on the Registry of
Open Data on AWS (RODA). The `roda_search` and `roda_load` steps discover and
ingest the dataset automatically into Quick Sight as a managed dataset.

**What question it answers:** Given IPEDS historical enrollment trends, what
is the projected headcount for the next 8 semesters, and what are the 95%
confidence bounds? The Prophet time-series model handles seasonal enrollment
patterns (fall peak, spring trough, summer dip) using multiplicative
seasonality, which better captures the compounding effects of demographic
shifts common in higher education.

**What output it produces:** A Quick Sight dataset containing point forecasts
and confidence intervals for 8 forward semesters, stored as a named snapshot
(`enrollment-forecast-8sem`) for reuse in dashboards. The final router step
passes the forecast summary to the model router, which drafts a polished
2-paragraph narrative suitable for a provost's budget presentation — including
trend direction, magnitude, and a plain-language interpretation of the
confidence interval. The narrative is returned directly in the workflow output
and can be copied into slides or a budget memo.
