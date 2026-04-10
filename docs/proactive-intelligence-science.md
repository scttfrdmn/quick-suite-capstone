# Proactive Intelligence: The Science Itself

This document continues `proactive-intelligence-roadmap.md`, extending the analysis
from research administration into the actual experimental science — hypotheses, data
collection, analysis, interpretation, and publication.

---

## The Different Problem

Administrative research computing has structured data: award tables, compliance
checklists, submission deadlines. The science has messy data: mass spectrometry outputs,
genomic sequences, field survey CSVs, telescope images, EEG recordings, interview
transcripts.

The administrative layer can be solved with good data pipelines. The science layer
requires the system to understand what the data *means* — or at least to know when it
doesn't know.

---

## Five Ideas

### 1. Anomaly-to-Hypothesis Engine

**What it does:** Runs anomaly detection across a lab's experimental data continuously,
but instead of flagging "here is an outlier," it asks: is this instrument error, an
uncontrolled confound, or a real effect worth following up? It cross-references the
anomaly against published literature to classify which.

**WTF moment:** "Your RNA-seq data from the treated group has an anomalous expression
cluster in genes you were not studying. Cross-referencing with PubMed: three papers in
the last 18 months report similar off-target expression patterns in this cell line under
this treatment. Two interpret it as noise. One published last month interprets it as a
secondary pathway interaction. That paper's lead author is 40 miles from you. Here is
their contact."

**Why it's WTF:** Every researcher has had a finding hiding in their data that they
dismissed as noise and later saw published by someone else. The literature
cross-reference is what makes this science rather than anomaly detection — the system
is classifying the anomaly against what's known, not just surfacing it.

**Technical path:** `anomaly-isolation-forest` compute profile (exists) + Router
`research` tool for literature cross-reference against PubMed/Semantic Scholar. New
orchestration: anomaly → literature search → significance classification. The `refine`
tool's summarization is the right shape for the classification step. Missing:
domain-specific anomaly thresholds per data type (genomics, proteomics, behavioral,
geophysical have completely different signal-to-noise characteristics).

---

### 2. Experimental Design Critic

**What it does:** Reviews a proposed experimental design against the statistical power
required to detect the effect size the PI is targeting, identifies confounds that
published literature has shown affect this assay or model system, and suggests design
modifications before the first experiment runs — not after reviewers reject the paper.

**WTF moment:** "Your proposed n=12 per group gives you 61% power to detect a 20%
effect at α=0.05. Based on the three most recent papers using this cell line and
treatment combination, actual effect sizes are typically 12–15%. At that effect size
you have 38% power. You need n=22 per group to reach 80%. Additionally, two papers
report that passage number above 25 is a significant confound in this assay — your
protocol doesn't specify passage number control."

**Why it's WTF:** Power calculations exist. Literature review exists. Nobody combines
them automatically, in the context of actual effect sizes from this specific system from
published data. The confound identification from literature is the part that currently
requires a very thorough PI or a very good postdoc.

**Technical path:** New `power-analysis` compute profile. Router `research` tool against
PubMed/bioRxiv for effect size extraction from methods sections — an LLM extraction
task. New piece: structured extraction of reported effect sizes and experimental
confounds from literature. The clAWS plan/excavate split is the right model: PI submits
a protocol, system returns a concrete critique before "executing."

---

### 3. Reproducibility Pre-flight

**What it does:** Before manuscript submission, re-executes all analysis code against
deposited data, compares statistical outputs to numbers in the manuscript, checks that
figures can be regenerated, and verifies all referenced datasets exist and are
accessible. Catches the mistakes made at 11pm before they reach a reviewer.

**WTF moment:** "Your manuscript reports p=0.0234 in Table 2, row 3. Re-running your
analysis script produces p=0.0312. The discrepancy traces to a data cleaning step in
`preprocess.py` line 47, modified after your final analysis run but before data deposit.
Here is the version that produces the reported result. This is a one-line fix. If this
reaches a reviewer, it is a retraction risk."

**Why it's WTF:** This is not catching fraud. It is catching the mundane mistakes that
cause retractions. The WTF is the specificity: not "your results don't reproduce" but
"here is the exact line of code and here is the fix."

**Technical path:** Provenance engine (see `proactive-intelligence-roadmap.md`) is the
prerequisite. Compute job history + S3 versioning + `audit_export` produces the raw
material. New piece: manuscript figure extraction + automated comparison against
re-execution outputs. The `custom-python` compute profile can run analysis code in the
RestrictedPython sandbox, compare outputs, and surface discrepancies.

---

### 4. Living Literature Review

**What it does:** Maintains a continuously-updated structured summary of the literature
in a research area, keyed to the specific questions the lab is working on. Flags when a
newly-published paper changes the interpretation of existing results, contradicts a core
assumption in an active grant, or invalidates a methodology being used.

**WTF moment:** "A paper published this morning reports that your primary antibody —
used in 23 experiments over the past two years — has significant cross-reactivity with
a protein upregulated under your experimental conditions. This would affect the
interpretation of 8 of your published figures. Here is a prioritized list of which
experiments are most affected and what validation steps would confirm or refute the
cross-reactivity in your specific system."

**Why it's WTF:** Antibody validation failures have caused hundreds of retractions. The
researchers who published those papers were not negligent — the cross-reactivity data
didn't exist yet. A system that watches new publications against your specific reagents
and conditions has a model of what you're doing and what would break it. That's
categorically different from a search engine.

**Technical path:** `watch` scheduled plans against PubMed/bioRxiv via `federated_search`.
Router `research` tool for semantic matching against lab protocols and reagent list.
New piece: reagent/antibody registry as a clAWS data source — structured enough for
Cedar policies, rich enough for semantic matching. The watch runner's drift detection
pattern (v0.9.0) is the right model: "baseline" is the current interpretation of
results; "drift" is a paper that changes it.

---

### 5. Cross-Discipline Signal Detector

**What it does:** Monitors literature outside a PI's primary field for methodological
advances and findings directly applicable to their work — specifically targeting the
case where a technique developed in field A solves an open problem in field B that
field B doesn't know field A solved.

**WTF moment:** "The open problem in your grant — separating population heterogeneity
from temporal dynamics in your longitudinal cohort — was solved in 2021 by an
econometrics team studying income mobility. The method is called 'cohort deconvolution'
and the R implementation has 400+ citations in economics and 2 citations in biology.
Here is how it applies to your dataset and a sketch of the analysis."

**Why it's WTF:** This is the most cognitively expensive thing a researcher can do —
read deeply enough outside their field to recognize a solution to their problem. Nobody
does it systematically because it's not tractable. A system that does it continuously,
for the specific open problems in specific grants, is not a search tool. It's a
research collaborator.

**Technical path:** Router `research` tool with cross-disciplinary corpus (Semantic
Scholar covers most fields). New piece: "open problem" extraction from grant specific
aims — structured LLM extraction of what the PI claims they don't yet know how to do.
Then: continuous semantic matching of "open problem" statements against new publications
across all fields. `watch` + Router orchestration. The clAWS `plan` tool's
free-text-to-structured-query pattern is the right model: convert unstructured "open
problem" to structured search terms, execute against literature, return matches with
applicability assessment.

---

## The Shift for the Science

The administrative shift was reactive → proactive. For the science, the shift is more
specific:

### From search to surveillance

Every tool researchers currently use requires them to initiate a search. They have to
already know what question to ask. The ideas above maintain a persistent model of what
each lab is doing, what they assume, what their open problems are, and what would change
or break their work. The system watches the world on their behalf and surfaces things
they didn't know to look for.

### From data to interpretation

Anomaly detection is not new. What's new is asking "is this anomaly interesting?" in
the context of what's published. Power calculation is not new. What's new is running it
against actual effect sizes from comparable systems rather than textbook formulas. The
compute profiles and Router infrastructure can do the calculation — the WTF comes from
combining it with domain knowledge extracted from literature.

---

## The Hard Technical Problem

The technical gap is narrower than it looks for some of these:

- Provenance engine and reproducibility pre-flight: infrastructure is mostly present
- Collaboration network intelligence: `network-coauthor` and `grant-portfolio` profiles
  exist; needs semantic matching and new-award `watch`

The genuine hard problem is **literature extraction**: structured extraction of effect
sizes, confounds, reagent cross-reactivity, open problems, and methodological
contributions from unstructured paper text. That's a Router task — it's what the
`research` tool is for — but it requires:

1. Prompt engineering per scientific domain
2. Careful grounding with citations to avoid hallucinated references
3. A schema for what "useful structured output" means per use case (effect size vs
   confound vs methodology vs open problem are different extractions)

This is product definition work, not infrastructure work. The infrastructure can execute
whatever is well-defined. The gap is defining it well enough to be trustworthy.

The trustworthiness bar matters more here than in administration. An accreditation gap
alert that's wrong is an annoyance. An anomaly classification that's wrong could send a
researcher down a dead end for six months. The system needs to communicate uncertainty
clearly and err on the side of "this might be interesting, verify it" rather than
"this is definitely significant."
