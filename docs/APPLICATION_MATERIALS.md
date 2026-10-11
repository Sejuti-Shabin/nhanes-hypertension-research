# Application materials — adapt only after verifying personal contribution

## Statement of purpose research description (three paragraphs)

I am developing my understanding of epidemiologic measurement and complex survey analysis through an AI-assisted secondary analysis of NHANES 2017–2018. The project asks whether lack of current health insurance is associated with lower reported hypertension awareness among adults aged 20–64. Its protocol distinguishes previous diagnosis from measured BP and examines how including medication users changes the population under study. Before using this statement, I will verify and document the components that I personally reran, reviewed and extended.

The workflow joins authentic CDC components, applies documented questionnaire skip patterns and retains examination weights, strata and clusters for domain inference. R survey provides reference logistic-model inference, while Python handles processing, tests, visualization and independent numerical comparisons. Awareness was 55.1% among insured and 43.1% among uninsured adults. The fully adjusted uninsured-versus-insured OR was 0.60 (95% CI 0.22–1.62); the interval included no association. The primary adjusted sample contained 1,534 adults, with only 3 residual survey df. Sensitivity analyses made clear that case definition, missing covariates and survey design degrees of freedom affect interpretation; the project does not establish a causal insurance effect.

The next work I intend to undertake is an independently reviewed missing-data strategy, more explicit investigation of temporal coverage history and a protocol-driven assessment of whether additional survey cycles would support a more precise target estimate. The value of this project for my training is learning to connect a clinical question to defensible definitions and uncertainty, and to report inconclusive evidence transparently. I will describe it as a portfolio manuscript draft and disclose computational assistance, rather than claim peer review or faculty supervision.

## CV-ready description

**Independent public-data research portfolio (AI-assisted), NHANES 2017–2018 — manuscript draft.** Developed/reviewed [replace with verified personal contribution] a reproducible Python/R survey workflow evaluating insurance and hypertension awareness in 1,534 complete-case adults; incorporated masked survey design, ascertainment and missingness sensitivities, independent numerical validation and uncertainty-focused reporting. Fully adjusted OR 0.60 (95% CI 0.22–1.62); no clear adjusted association established.

## Skills demonstrated by the artifacts

- Epidemiological question formulation, operational definitions and conceptual causal diagrams.
- Clinical measurement interpretation and questionnaire skip-pattern coding.
- Authentic-source provenance, validated one-to-one joins and missingness audits.
- Complex-survey weighting, domain estimation, Taylor variance and svyglm inference.
- Odds-ratio interpretation, descriptive standardization and bias sensitivity.
- Model convergence, sparse-category, leverage and sampling-unit influence assessment.
- Modular Python engineering, automated tests and independent R comparisons.
- Publication-style figures, STROBE-oriented reporting and transparent contribution disclosure.

These artifacts demonstrate an implemented workflow, not proof that the applicant independently possesses every listed skill. Personal competence should be demonstrated by rerunning and explaining the work.
