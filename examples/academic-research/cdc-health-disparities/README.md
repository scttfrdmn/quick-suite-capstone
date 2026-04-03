# CDC PLACES Health Disparities Regression

A public health researcher uses Quick Suite to model social determinants of
diabetes prevalence at the census tract level using CDC PLACES data, then
generates a grant-ready narrative summarizing the findings. The workflow spans
all three stacks: quick-suite-data discovers and loads the dataset,
quick-suite-compute runs a logistic regression, and quick-suite-router drafts
the significance section using the `analyze` tool.

**Data source:** CDC PLACES (Population Level Analysis and Community
Estimates) on RODA. PLACES provides model-based prevalence estimates for 36
chronic disease measures and 13 health risk behaviors at the census tract and
county level across all 50 states. The dataset is derived from Behavioral Risk
Factor Surveillance System (BRFSS) data. Key columns in this workflow:
`diabetes_prevalence`, `median_income`, `pct_no_insurance`, `pct_poverty`,
and `pct_obesity`. All measures are tract-level percentages or rates.

**Output:** The `regression-glm` compute profile returns a Parquet file with
model coefficients, standard errors, odds ratios, and 95% confidence intervals
for each predictor. The `analyze` router step returns a structured narrative
paragraph (in `content`) suitable for the Significance section of an NIH or
NSF proposal, referencing the strongest predictors and their effect sizes.
Both the regression result and narrative are scoped to the
`cdc-places-diabetes-sdoh-regression` snapshot.

**Prerequisites:** None. CDC PLACES is a publicly available RODA dataset. The
router `analyze` tool requires the quick-suite-router stack to be deployed and
the `public-health` department to have budget headroom in the spend ledger.
The `context` field passes the `result_uri` (S3 path) directly to the router;
the router's Lambda reads the Parquet file to ground the narrative in the
actual coefficients.
