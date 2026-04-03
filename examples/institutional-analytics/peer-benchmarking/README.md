# Peer Benchmarking — Tuition Revenue per FTE (IPEDS)

**Who runs this:** Institutional Research directors and CFO analysts preparing
peer comparison reports for board presentations, regional accreditation
self-studies, or strategic planning retreats where leadership wants to know how
their institution's tuition revenue efficiency compares to national peers.

**What data it needs:** No institutional data setup is required. This scenario
pulls entirely from the publicly available IPEDS finance and enrollment dataset
hosted on RODA. The dataset includes tuition revenue, FTE enrollment,
selectivity rates, endowment figures, and Pell concentrations for thousands of
degree-granting institutions, providing a natural national peer group without
any manual peer-list curation.

**What question it answers:** Controlling for institutional size, selectivity,
endowment per FTE, and Pell concentration, where does the institution sit in the
national distribution of tuition revenue per FTE? The linear regression surfaces
the predicted value for a peer-matched institution of similar characteristics,
and the residual reveals whether the institution is capturing more or less
tuition revenue than peers with comparable profiles. Positive residuals may
indicate pricing power or strong net-tuition optimization; negative residuals
may point to discount rate pressure or mission-driven affordability commitments
worth articulating to the board.

**What output it produces:** A regression model result stored as a Quick Sight
snapshot (`peer-benchmark-tuition-fte`) containing predicted values, residuals,
and coefficient estimates for each feature. The router step passes the summary
statistics to the model router, which drafts three concise, board-appropriate
talking points contextualizing the institution's position in the peer
distribution. The talking points are returned in the workflow output and are
designed to be dropped directly into a slide deck or finance committee memo
with minimal editing.
