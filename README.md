# Hypertension Awareness and Health Insurance in U.S. Adults

**An epidemiology research-training portfolio using CDC NHANES 2017–2018**  
Python · R `survey` · Complex survey analysis · Clinical epidemiology

> **Research status:** Public-data secondary analysis and manuscript-style training project, developed with substantial AI assistance. It is **not** a peer-reviewed publication or independently supervised research. Before using this as a personal PhD writing sample, the applicant should rerun, verify and explain the methods and document their individual contribution.

## Research question

Among adults aged **20–64** meeting an operational definition of hypertension, is being **uninsured** associated with lower self-reported awareness of a previous hypertension diagnosis after adjusting for sociodemographic characteristics?

The objective is to examine an observational association and understand how measurement definitions, adjustment and complex sampling influence the estimate. **No causal effect is claimed.**

## Key results

| Analysis | Estimate |
|---|---:|
| Hypertension awareness, insured | **55.1%** |
| Hypertension awareness, uninsured | **43.1%** |
| Adjusted OR, uninsured vs insured | **0.60** |
| 95% confidence interval | **0.22–1.62** |
| Complete-case adjusted model | **n = 1,534** |
| Model 3 residual survey degrees of freedom | **3** |

**Interpretation:** Observed awareness was lower among uninsured respondents, but the adjusted confidence interval includes no association and substantial uncertainty in both directions. Different case definitions yielded unstable estimates, including a direction reversal for measured-only 140/90. The result **does not demonstrate** that insurance changes awareness.

![Survey-weighted awareness by insurance status](figures/awareness_by_insurance.png)

## Methods in brief

- **Design:** Cross-sectional NHANES 2017–2018, U.S. noninstitutionalized adults aged 20–64.
- **Outcome:** Previous clinician-diagnosed hypertension reported in questionnaire (`BPQ020`).
- **Exposure:** Current health insurance (`HIQ011`).
- **Operational cases:** First-three-reading mean blood pressure ≥130/80 mmHg or reported current prescribed BP medicine (`BPQ050A`), with documented missingness/skip treatment.
- **Analyses:** Survey-weighted descriptive estimates, logistic regression adjusted for age, sex, race/ethnicity, education and income-to-poverty ratio; survey-design-aware R inference and Python comparison.
- **Checks:** Threshold and case-definition sensitivity, missing-data diagnostics, sampling-unit influence, automated validation, transparent reporting.

The inclusion of medication-defined cases can introduce diagnosis-linked selection. A single NHANES visit is not a clinical diagnosis. These and other concerns are discussed in the [manuscript](MANUSCRIPT.md).

## Explore the project

| Start here | What's inside |
|---|---|
| [One-page faculty summary](docs/FACULTY_OUTREACH.md) | Short research overview with transparent limitations |
| [Academic writing sample (PDF draft)](docs/academic_writing_sample_DRAFT.pdf) | Eight-page manuscript-style writing sample for review; **draft only** |
| [Full manuscript (Markdown)](MANUSCRIPT.md) | Literature, methods, results, discussion and references |
| [Research protocol](research_protocol.md) | Hypothesis, analytic definitions and study plan |
| [Selected aggregate results](outputs/) | Survey-weighted model tables and sensitivities |
| [Figures](figures/) | Publication-style PNG and PDF charts |
| [Methodological review](docs/METHODOLOGICAL_REVIEW.md) | Unresolved biases, reviewer-style critique and revisions |
| [Methods/code](src/) and [R validation](r/) | Reproducible statistical pipeline |
| [Research contribution notes](CONTRIBUTIONS.md) | Guidance to document personal contributions accurately |
| [Public release notes](docs/RELEASE_NOTES.md) | Exactly what was checked and what remains to verify |

![Survey-adjusted odds ratios](figures/adjusted_odds_ratios.png)

## Reproducing the analysis

This public repository intentionally **does not include raw CDC XPORT files, participant-level analytic records, local build libraries or prior backup archives**. The first full run downloads official NHANES source files (internet required); content hashes are checked against the recorded source manifest. **R with the `survey` package is required** for a complete run.

```bash
python -m pip install -r requirements.txt
Rscript -e 'install.packages(c("survey", "foreign"), repos="https://cloud.r-project.org")'
python run_all.py
```

See [Reproducibility](REPRODUCIBILITY.md) for virtual environments, data provenance, validation scope and technical limitations. The checked-in figures/tables come from the earlier supplied executed analysis; **the cleaned repository has not been independently rerun end-to-end in this environment**.

## Caveats and research integrity

- Adjusted inference is **highly imprecise** due to few residual design degrees of freedom; the study is not definitive.
- Association cannot establish causality: coverage may change after diagnosis; current coverage is not lifetime access.
- Diagnostic criteria, measurement missingness, residual confounding and model choices affect estimates.
- All survey estimates describe the historical **2017–2018** target population, not current 2026 prevalence.
- Literature novelty is limited; this is a **methodology-oriented replication/extension**, not a new discovery.
- AI substantially assisted earlier coding and drafting. See [CONTRIBUTIONS.md](CONTRIBUTIONS.md). Do not attribute work or faculty supervision that cannot be documented.

[Original data: CDC/NCHS NHANES](https://wwwn.cdc.gov/nchs/nhanes/search/DataPage.aspx?Cycle=2017-2018) · [Data provenance](DATA_PROVENANCE.md) · [STROBE crosswalk](docs/STROBE_CHECKLIST.md) · [Code licensing considerations](LICENSE_NOTES.md)
