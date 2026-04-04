# Example Prompts: Faculty Researcher

Faculty researchers use Quick Suite to analyze research data, explore datasets from
public repositories, run statistical tests, and identify patterns — without
requiring a data science team or cloud infrastructure expertise.

---

## 1. Course Evaluation Open-Ended Themes

**User prompt:**
> "I have 3,000 course evaluation open-ended responses. Can you identify the main
> themes students are writing about without me having to read all of them?"

**Tools called:**
1. `claws-discover` — find course eval response table
2. `claws-excavate` — pull open-ended text responses
3. `compute_run` (profile: `text-topics`) — LDA/NMF topic modeling; `num_topics: 8`
4. `compute_status`

**What you get:** Each response tagged with a dominant topic and probability;
topic-term matrix showing the top 10 words per theme; ready for qualitative labeling.

---

## 2. Survey Response Deduplication Before Analysis

**User prompt:**
> "Before I analyze this climate survey dataset, I want to flag near-duplicate
> responses that might indicate copy-paste or survey fatigue."

**Tools called:**
1. `compute_run` (profile: `text-similarity`) — TF-IDF cosine similarity,
   `similarity_threshold: 0.85`
2. `compute_status`

**What you get:** `similarity_group_id` and `is_near_duplicate` flags on each record;
`canonical_id` identifies the representative for each duplicate cluster;
group summary shows cluster sizes.

---

## 3. Sentiment Analysis on Post-Intervention Survey

**User prompt:**
> "I ran a writing intervention in my first-year composition course. Score the
> student reflection texts as positive, negative, or neutral so I can track
> sentiment shift pre- and post-intervention."

**Tools called:**
1. `compute_run` (profile: `text-sentiment`) — VADER scoring; `output_scores: true`
2. `compute_status`

**What you get:** `sentiment` label and `sentiment_score` (-1 to +1) per response;
optional `pos_score`, `neg_score`, `neu_score`, `compound_score` for fine-grained
pre/post comparison.

---

## 4. Grant Portfolio Anomaly Detection

**User prompt:**
> "Flag any grant spending transactions in my lab's portfolio that look anomalous
> compared to typical monthly spending patterns."

**Tools called:**
1. `claws-discover` — find grant transaction table in Athena
2. `claws-probe` + `claws-plan` + `claws-excavate` — extract lab's transactions
3. `compute_run` (profile: `anomaly-isolation-forest`) — Isolation Forest,
   features: `amount`, `days_since_award_start`, `spending_category`
4. `compute_status`

**What you get:** `is_anomaly` flag and `anomaly_score` on each transaction;
transactions scoring below -0.1 are flagged as potential outliers.

---

## 5. ANOVA — Do Grade Distributions Differ Across Sections?

**User prompt:**
> "I'm teaching four sections of the same course. Test whether final exam scores
> differ significantly across sections."

**Tools called:**
1. `compute_run` (profile: `anova`) — one-way ANOVA + Tukey HSD pairwise tests
2. `compute_status`

**What you get:** F-statistic, p-value, eta-squared effect size; pairwise Tukey HSD
comparisons with Bonferroni-corrected significance; group means table.

---

## 6. Change Detection — When Did Course Outcomes Shift?

**User prompt:**
> "My department changed its gateway course curriculum in 2019. Did pass rates
> actually change structurally, or was it noise?"

**Tools called:**
1. `compute_run` (profile: `change-detection`) — PELT algorithm, `model: rbf`
2. `compute_status`

**What you get:** `change_point: true` rows flagging the detected structural break
dates; `segment_id` identifies pre- and post-change segments; diagnostics report
exact dates and magnitudes.
