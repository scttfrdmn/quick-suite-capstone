# Course Evaluation Theme Discovery (LDA Topic Modeling)

**Who runs this:** Academic Affairs offices, institutional effectiveness
analysts, and faculty senate curriculum committees who want to systematically
surface themes from large volumes of course evaluation open-ended responses
without manually reviewing thousands of individual comments.

**What data it needs:** This scenario requires course evaluation open-ended
response data stored in S3 as Parquet or CSV files, accessible via a registered
clAWS S3 source. The files must include a free-text response field, course
identifier, academic department code, and term. Institutional data setup is
required — see `scenario.yaml` for the expected schema and S3 registration
steps. Responses should be anonymized before registration (no student or
instructor names in the text field). The clAWS probe step performs an
additional PII scan on sampled rows before the plan is executed.

**What question it answers:** Across all open-ended course evaluation responses
for the current academic year, what are the 12 most common thematic topics, and
how do those topics distribute across academic departments? LDA (Latent
Dirichlet Allocation) surfaces coherent word clusters that correspond to
recurring student experience themes — such as clarity of instruction, workload,
assessment fairness, or course pacing — without requiring a pre-defined rubric.
The `group_by: department` parameter produces per-department topic distributions,
allowing the faculty senate to compare theme prevalence across colleges or
schools.

**What output it produces:** A topic model result stored as a Quick Sight
snapshot (`course-eval-topics-2024`) containing the top terms for each of the
12 topics, topic prevalence across the full corpus, and per-department topic
distribution scores. The result is immediately usable in Quick Sight to build
a heatmap of topic prevalence by department or a word-cloud visualization of
top topic terms. The full clAWS provenance chain is preserved in the export,
documenting which response set was analyzed and when.
