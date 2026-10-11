# Protocol amendments

Version 1 was written before new insurance outcome analysis. Implementation clarifications, failures and changes will be appended here. This record is retrospective and is not a public preregistration.

Implementation clarification: R svyglm numerical convergence tolerance tightened from its default to 1e-12 (max 200 iterations) after Python/R SE differences of approximately 1e-6 in secondary models. Specifications were unchanged and subsequent comparisons passed. R survey 4.5 was successfully installed using local aliases to already installed BLAS/LAPACK libraries; no system files changed. NCHS effective-n cap and boundary review added to the beta-interval screening implementation. Primary sample has one BP-complete adult with unknown medication and below-threshold measurement, excluded as unclassifiable, not assumed normotensive.

## Reviewer-directed version 2 (post hoc)

The journal-style REVIEW.md was written after inspection of initial results and before executing reviewer-directed revisions. Revision changes are exploratory and do not inherit “planned” status from the initial protocol. Submitted code/results are preserved in internal pre-review snapshot (excluded from public portfolio); initial protocol in docs/research_protocol_v1.md.

1. Remove the unnecessary complete-BP requirement for known medication cases from the primary analysis; retain it as the bp_complete sensitivity. Resolve an OR-positive BP result from either known elevated mean rather than requiring both components. Report classifiable examined denominators and ascertainment/awareness bounds.
2. Harmonize model-standardized interval reference with Model 3 residual df; logit-transform probability intervals. Add full-design-df coefficient calibration as a reference sensitivity without significance-based selection.
3. Independently rebuild every R model mask and compare full Taylor covariance matrices. Tighten reference GLM convergence to 1e-14 after the full-matrix check exposed a ~1.3e-8 off-diagonal difference in measured140; tolerance for comparisons remains unchanged.
4. Add R JKn nonlinear standardization verification and PIR response-weighting sensitivity with nuisance/outcome/auxiliary-mean refits in every PSU replicate. MAR and positivity are assumptions; missing education is not repaired.
5. Add the current uninsured versus insured/no reported past-year lapse restriction using authentic HIQ210; do not recode the uninsured's skipped HIQ210 as no lapse.
6. Add CDC's cycle-specific nonresponse guidance, OR noncollapsibility, explicit observed-data targets and unresolved novelty limitations. Strengthen runner failure state, validation fingerprints and reliability-edge tests. Regenerate all dependent reporting from actual outputs.
