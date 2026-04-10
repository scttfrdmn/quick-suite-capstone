# Compute: Difference-in-Differences

Use `compute_run` with the `causal-did` profile to estimate the causal
effect of an intervention using a difference-in-differences design.

## Scenario

Your institution launched a proactive advising program for first-gen
students in Fall 2024. You want to know if it actually improved
retention — not just whether the treatment group did better (they
might have been trending better already).

## Tool call

```
compute_run

profile_id: "causal-did"
source_uri: "claws://s3-advising-intervention-cohort"
parameters:
  outcome: "retained_spring"
  treatment: "advising_program"
  time: "cohort_year"
  pre_periods: ["2021", "2022", "2023"]
  post_periods: ["2024", "2025"]
  cluster_var: "advisor_id"
```

## Response (after polling compute_status)

```json
{
  "status": "SUCCEEDED",
  "summary": {
    "row_count": 12400,
    "columns": ["cohort_year", "advising_program", "retained_spring",
                "did_estimate", "did_se", "did_pvalue",
                "parallel_trends_pvalue", "event_study_coefs",
                "placebo_pvalue"],
    "metadata": {
      "did_estimate": 0.067,
      "did_se": 0.023,
      "did_pvalue": 0.004,
      "parallel_trends_pvalue": 0.42,
      "placebo_tests": {
        "2022_vs_2021": {"estimate": 0.008, "pvalue": 0.71},
        "2023_vs_2022": {"estimate": -0.003, "pvalue": 0.88}
      },
      "event_study_coefficients": {
        "2021": {"coef": 0.002, "se": 0.019},
        "2022": {"coef": 0.008, "se": 0.021},
        "2023": {"coef": -0.003, "se": 0.020},
        "2024": {"coef": 0.059, "se": 0.024},
        "2025": {"coef": 0.075, "se": 0.025}
      }
    }
  }
}
```

## Reading the results

- **DID estimate: 0.067** — the program increased retention by 6.7
  percentage points
- **Parallel trends p-value: 0.42** — you cannot reject parallel
  trends in the pre-period (good — the assumption holds)
- **Placebo tests: all p > 0.5** — no significant treatment effect in
  years when there was no treatment (good — no false positives)
- **Event study coefficients** — flat pre-period, jump in 2024,
  growing in 2025 (classic DiD pattern)

## How this fits your workflow

You're writing an evaluation report. The DiD results give you a
defensible causal claim for the provost: "The proactive advising program
caused a 6.7pp improvement in first-gen retention, and the parallel
trends and placebo tests confirm this isn't an artifact of pre-existing
trends."

If the parallel trends test had failed (p < 0.05), you'd switch to
`causal-rd` (if there's an eligibility cutoff) or `causal-iv` (if you
have an instrument).

## Other causal profiles

| Profile | When to use |
|---------|-------------|
| `causal-did` | Treatment at a point in time, panel data, pre/post comparison |
| `causal-rd` | Sharp or fuzzy eligibility cutoff (GPA threshold, income limit) |
| `causal-iv` | You have an instrument (lottery assignment, geographic distance) |
