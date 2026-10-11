# One-page project summary

**Health Insurance Coverage and Hypertension Awareness Among U.S. Adults: NHANES 2017–2018**  
Applicant: [name] · Educational secondary analysis; AI-assisted, not peer reviewed

**Question.** Among U.S. adults aged 20–64 meeting an operational hypertension definition, is current lack of insurance associated with lower self-reported awareness after demographic/SES adjustment?

**Data and design.** Authentic CDC DEMO_J, BPX_J, BPQ_J, HIQ_J and HUQ_J; one-to-one merges; operational hypertension defined by available first-three BP means ≥130/80 or current prescribed medication. Awareness uses BPQ020; insurance uses HIQ011. The analysis preserves the full positive-weight MEC design before subpopulation restriction and admits medication-confirmed cases without BP. Reviewer-directed changes are post hoc.

**Methods.** Weighted descriptions and logistic Models 1–3, Taylor linearization with masked strata/PSUs, R survey reference inference, independent Python numerical comparisons. The final model adjusts for age, sex, six race/ethnicity groups, four education groups and continuous PIR. Common-sample models, measurement/threshold/case-definition sensitivities, MAR-dependent missing-PIR response weighting with refit PSU replicates, missingness profiles and influence diagnostics accompany the main results.

**Actual findings.** Awareness was 55.1% among insured and 43.1% among uninsured adults. The fully adjusted uninsured-versus-insured OR was 0.60 (95% CI 0.22–1.62); the interval included no association. The primary adjusted sample contained 1,534 adults, with only 3 residual survey df. Standardized uninsured-minus-insured awareness difference: -11.6 percentage points (95% CI -33.7–10.5). This does not establish an adjusted association. Measured-only 140/90 estimates reversed direction with wide uncertainty.

**Limits.** Cross-sectional and historical; awareness self-reported; BP measured at one visit. Medication inclusion is linked to diagnosis and changes selection. Primary complete cases exclude some participants with missing income; a MAR-dependent response-weighting sensitivity is not a verified cure; ordinary examination weights do not repair item missingness. Model 3 has few residual design df. No causal or novelty claim.

**Reproducible artifacts.** Protocol, audited original, data dictionary, modular pipeline, R validation, tests, Table 1, regression/sensitivity outputs, five PNG/PDF figures and manuscript. Code and actual outputs are ready for review.

**Contribution disclosure.** AI performed substantial coding and writing in this iteration. Applicant must rerun, understand, independently review and document their actual contribution before presenting the work. Supervision and publication are not claimed.

**Research development.** Qualified review priorities: target/ascertainment bias, residual-df convention, sparse categories/overlap, survey-compatible missing-data strategy and whether a prespecified multi-cycle extension is justified.
