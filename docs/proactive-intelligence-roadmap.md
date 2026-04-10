# Proactive Intelligence Roadmap

This document catalogs high-leverage capability directions for the Quick Suite higher
education platform — organized around a central thesis about what separates a useful
tool from a transformative one.

---

## The Core Shift

Every system researchers and administrators interact with today is **reactive**: it
answers questions asked of it, surfaces violations after the fact, and reports on what
already happened.

The shift that makes this platform genuinely WTF-worthy is moving from reactive to
**proactive**: the system has enough context about institutional goals, research
portfolios, enrollment targets, and compliance surfaces to ask the questions the user
didn't know to ask.

"Do you know there's a researcher two floors up solving the adjacent problem?" cannot
be queried. It requires the system to have a model of what would be *valuable* to know,
not just an interface for what you already know to ask. That's the difference between
a tool and a colleague.

The technical infrastructure to do this — Cedar policies, watch runner, federated
search across public databases, compute profiles, provenance tracking — is either
already built or one profile away from built. What's missing in each case is domain
ontology: what does "grant portfolio health" mean, what signals constitute a
"collaboration opportunity," what changes constitute a compliance surface-area expansion.
That's a product definition problem, not an engineering problem.

---

## Higher Education Administration

*Persona: IR analysts, enrollment management, accreditation coordinators, VPs.*

### 1. Causal Intervention Intelligence

**What it does:** Runs quasi-experimental analysis on institutional data — instrumental
variables, regression discontinuity, difference-in-differences — to separate programs
that *cause* better outcomes from programs that serve students who were already going
to succeed.

**WTF moment:** "Your first-year advising expansion is associated with a 14% retention
improvement. But our causal model shows the entire effect is explained by which advisor
students were assigned to, not advising frequency. Four advisors are driving the
outcome. The other 22 have no detectable effect."

**Why it's WTF:** Every institution has correlation-based program evaluation. Nobody
has causal attribution at the program-component level running continuously on their own
data. This is what a $400K consulting engagement produces once. This produces it
quarterly, automatically.

**Technical path:** New `causal-iv` and `causal-rd` compute profiles extending the
existing profile execution framework. Needs time-series enrollment/retention data with
treatment/control identifiers. The data pipeline and profile execution are present —
missing are the causal inference profiles and automated identification of natural
experiments in historical records.

---

### 2. The Invisible Accreditation Team

**What it does:** Continuously maintains a structured evidence ledger mapped to
accreditation standards. Monitors data for gaps proactively. Drafts self-study
narratives from current institutional data on demand.

**WTF moment:** "Your SACSCOC Compliance Certification draft is complete. Based on
current data, you have a documentation gap in Standard 8.2.c — faculty credentials
in three online programs. You have 14 months before your next review. Here are the
23 faculty records that need updated transcripts."

**Why it's WTF:** Self-study preparation consumes 18–24 months of staff time. The WTF
isn't "AI wrote our report" — everyone expects that eventually. The WTF is finding the
gap 14 months early. That's the difference between a finding and a recommendation.

**Technical path:** Orchestrated clAWS `discover` + `excavate` + `refine` against
internal data, mapped to an accreditation standard ontology. The compliance `audit_export`
Lambda (v0.11.0) is already the right shape — it needs to run proactively on a schedule
rather than on-demand, against a standards-mapping configuration layer.

---

### 3. IPEDS Competitive Intelligence

**What it does:** Pulls peer institution IPEDS submissions, runs causal models against
their longitudinal data, and identifies what structural or program changes preceded
their outcome improvements.

**WTF moment:** "State University improved six-year graduation rate from 58% to 71%
over four years. Their IPEDS data shows the improvement tracks a cohort where Pell
concentration decreased 8 points AND residential capacity expanded. The graduation
effect appears in the residential cohort, not commuter. Their announced intervention
was 'enhanced advising.'"

**Why it's WTF:** Every VP of Enrollment has a peer benchmarking spreadsheet. Nobody
has causal decomposition of competitor outcomes from public data. The competitor's press
release says advising. The data says housing. That's actionable intelligence.

**Technical path:** IPEDS is public — `roda_search` already finds it. `federated_search`
+ `compute_run` with causal profiles against longitudinal IPEDS cohort data. New piece:
automated peer group identification by Carnegie class + enrollment band + mission type.
This is a profile + orchestration problem; the technical stack is present.

---

### 4. Enrollment Cliff Navigator

**What it does:** Scores every admitted student daily on defection probability,
identifies the specific friction signal, routes to the right staff member with a drafted
outreach message, and tracks whether the intervention changed trajectory.

**WTF moment:** "Admitted student Maya Rodriguez has an 84% deposit probability that
dropped to 31% in 72 hours. Signal: two visits to a competitor's financial aid portal.
She has not received a revised award package since the competitor's scholarship
announcement last week. Suggested action: revised package + personal call from Director
of Financial Aid. Draft message attached. Expected yield lift: +47 points at this score
range."

**Why it's WTF:** Enrollment CRMs exist. Predictive models exist. None close the loop
from signal → cause → right person → drafted action → measured outcome. The WTF is the
complete circuit, not any individual component.

**Technical path:** `watch` scheduled plans + `drift_detection` on applicant behavioral
data + routing logic to staff queue. The watch runner (v0.7.0) + drift detection (v0.9.0)
architecture is already exactly this pattern. Missing: applicant portal data integration
and the action-routing layer.

---

## Academic Research Administration

*Persona: Principal investigators, lab managers, research computing staff, sponsored programs.*

### 1. Grant Cliff Detector

**What it does:** Monitors every active award for no-cost extension risk, effort
reporting gaps, carry-forward anomalies, and subrecipient compliance issues. Projects
cash flow and burn rate per project. Identifies the PI's historical proposal submission
patterns and flags when they need to be writing.

**WTF moment:** "You have three awards ending in the next 18 months with no renewal in
the pipeline. Based on your historical submission patterns, you needed to start two of
them six weeks ago. Your NIH R01 renewal has a 34% fundability probability at current
payline. Your collaborator at Michigan has a pending award in the same mechanism that
lists cross-institutional collaboration as a future direction. You may want to be on
their team rather than competing."

**Why it's WTF:** Sponsored programs offices track compliance. PIs track nothing. The
gap between "your award is ending" and "here is your strategic grant position and what
to do about it" is the WTF. The strategic layer doesn't exist in any current system.

**Technical path:** Federated query against NIH Reporter + NSF Award Search (public
APIs) + internal award management data via `federated_search`. New `grant-pipeline`
compute profile. `watch` on NIH payline publications + competitor award announcements
matching research area. Causal models: what submission timing patterns predict
successful R01 renewal.

---

### 2. Research Data Provenance Engine

**What it does:** Catalogs every dataset a lab generates, maintains a complete
provenance graph from raw instrument output to published figure, and validates
reproducibility on demand — including retroactively, from existing CloudTrail and
S3 versioning records.

**WTF moment:** "Figure 3B in your 2024 Nature Methods paper cannot be reproduced from
current repository state. The pipeline script references a preprocessing filter modified
8 months ago. The original version exists in your lab's S3 backup. Your postdoc who
built this pipeline left 14 months ago. Here is the exact command sequence that produced
the published figure, recovered from compute job logs."

**Why it's WTF:** The system can reconstruct provenance retroactively from what already
exists — CloudTrail, S3 versioning, compute job history — without requiring researchers
to change behavior. That's the WTF: it works on the lab you already have, not the
perfectly-organized lab you wish you had.

**Technical path:** `audit_export` Lambda pattern (clAWS v0.11.0) applied to compute
job history + S3 object versioning events. New `provenance-graph` compute profile.
`claws://` URIs connecting instrument S3 output → processed data → figure artifacts.
This is existing infrastructure applied to a new data domain.

---

### 3. Collaboration Network Intelligence

**What it does:** Maps your actual collaboration network against your stated research
interests, surfaces internal colleagues and external PIs working on adjacent problems,
and detects collaboration opportunities created by new award announcements — on day one
of the new award period.

**WTF moment:** "Three researchers at your institution are publishing in your exact niche
and you have never co-authored with any of them. One received a new R01 last month that
lists 'collaboration with behavioral neuroscience' as a future direction. You are a
behavioral neuroscientist. This is the first day of their award period."

**Why it's WTF:** By the time an award is old news, collaboration conversations are
already happening without you. Day-one awareness of a new aligned award — with the
PI's research profile, contact information, and the specific gap in their proposal that
you fill — is something that cannot happen through existing mechanisms.

**Technical path:** `network-coauthor` + `grant-portfolio` compute profiles (both exist)
+ NIH Reporter / NSF Award Search via `federated_search`. New piece: semantic similarity
between research abstracts to surface non-obvious adjacencies. `watch` on new award
announcements matching semantic profile. Router's `summarize` tool for abstract
comparison.

---

### 4. IRB and Compliance Autopilot

**What it does:** Monitors active IRB protocols for amendments triggered by scope creep,
tracks export control classifications when international collaborators join, identifies
data use agreement gaps when new data sources are added, and drafts amendment language
before the first data collection — not after the audit finding.

**WTF moment:** "You added a new site to your multi-site trial last month. That site is
in Germany. Your current Data Use Agreement does not authorize international data transfer
under GDPR Article 46. Your first data collection at that site is scheduled in three
weeks. Here is a draft IRB amendment and a template DUA addendum for your program
officer."

**Why it's WTF:** Compliance violations don't happen because PIs are malicious — they
happen because the compliance surface area is enormous and researchers are not lawyers.
This catches the gap three weeks before the first data collection, not after the audit
finding. That's the entire value: interception, not punishment.

**Technical path:** clAWS `watch` on IRB protocol records + export control database +
DUA registry. Cedar policies encoding compliance rules. The IRB workflow (v0.11.0
`pending_approval` status, `approve_plan` Lambda) is structurally the right model —
apply it to compliance monitoring. `refine` + `audit_export` for draft amendment
generation.

---

## The Science Itself

*What no one has built yet — tools that touch actual experimental science, not research
administration.*

See `docs/proactive-intelligence-science.md`.
