# Example Prompts: Advancement Officer

Advancement officers use Quick Suite to identify prospects, segment donors, score
major gift candidates, and map alumni geographic density — without building custom
analytics pipelines or waiting on IT.

---

## 1. Donor Segmentation by Giving Behavior

**User prompt:**
> "Segment our alumni donor base into four groups based on their giving history.
> I want to understand who our loyal mid-level donors are vs. lapsed major donors."

**Tools called:**
1. `claws-discover` — find alumni giving history table
2. `claws-probe` + `claws-plan` + `claws-excavate` — extract 5-year giving records
3. `claws-refine` — deduplicate gift records
4. `claws-export` — stage to S3
5. `compute_run` (profile: `clustering-kmeans`) — k=4, features: `total_giving`,
   `gift_count`, `years_since_last_gift`, `largest_gift`
6. `compute_status`

**What you get:** Each donor assigned to a cluster (0–3) with distance to centroid;
cluster profile diagnostics show mean giving characteristics per segment.

---

## 2. Major Gift Prospect Scoring

**User prompt:**
> "Score our alumni prospects for major gift likelihood based on their engagement,
> capacity indicators, and giving history. I need a ranked list for our capital
> campaign."

**Tools called:**
1. `claws-discover` + `claws-excavate` — pull prospect data with engagement scores
2. `compute_run` (profile: `regression-logistic`) — target: `gave_major_gift`,
   features: `engagement_score`, `estimated_capacity`, `years_of_giving`,
   `event_attendance`, `volunteer_roles`
3. `compute_status`

**What you get:** `predicted_prob` (0–1 major gift likelihood) and `predicted_class`
per prospect; feature importances ranked by contribution to the model.

---

## 3. Alumni Geographic Catchment — Event Planning

**User prompt:**
> "For our regional alumni events, assign each alumnus to the nearest campus
> within 75 miles so we can plan host locations. Use straight-line distance."

**Tools called:**
1. `claws-discover` + `claws-excavate` — pull alumni address lat/lon
2. `compute_run` (profile: `isochrone`) — `origins_uri: s3://…/campus_locations.csv`,
   `max_distance_km: 120` (≈75 miles)
3. `compute_status`

**What you get:** `nearest_origin` (campus name), `distance_km`, and
`within_catchment` flag per alumnus; diagnostics show count per campus catchment.

---

## 4. Alumni Density by Congressional District

**User prompt:**
> "Map our alumni home addresses to congressional districts so government relations
> can prioritize outreach for the appropriations cycle."

**Tools called:**
1. `s3_preview` — confirm alumni address file schema in S3
2. `compute_run` (profile: `spatial-aggregate`) — `boundary_uri` pointing to
   congressional district GeoJSON, metrics: alumni count per district
3. `compute_status`

**What you get:** Each alumnus tagged with `polygon_id` and district name;
polygon-level summary with count, and optional giving metrics aggregated by district.

---

## 5. Lapsed Donor Reactivation — Survival Analysis

**User prompt:**
> "How long do lapsed donors typically stay lapsed before returning? And are
> major gift donors more likely to reactivate than annual fund donors?"

**Tools called:**
1. `claws-excavate` — extract lapsed donor records with last gift date and
   reactivation date (if any)
2. `compute_run` (profile: `survival-kaplan-meier`) — duration: `years_lapsed`,
   event: `reactivated`, group: `donor_segment`
3. `compute_status`

**What you get:** Kaplan-Meier survival curves by donor segment; median time-to-
reactivation; log-rank test comparing segments; hazard ratios.

---

## 6. Random Forest — Predict Who Will Upgrade Their Gift

**User prompt:**
> "Which of our current annual fund donors are most likely to upgrade to a
> leadership-level gift this year? Train on last year's upgrades."

**Tools called:**
1. `claws-excavate` — pull donor giving history with `upgraded` label from last cycle
2. `compute_run` (profile: `classification-random-forest`) — target: `upgraded`,
   features: `total_giving`, `consecutive_years`, `last_gift_amount`,
   `engagement_score`, `pref_channel`; `class_weight: balanced`
3. `compute_status`

**What you get:** `predicted_class` (upgraded/not) and `predicted_prob_upgraded`
per donor; feature importances showing which signals drive upgrade likelihood.
