# Quality assurance of supplied analysis (snapshot)

The original uploaded ZIP reported 15 automated tests passing and numerical agreement between its Python and R survey calculations. This **public-portfolio cleanup does not constitute a fresh full analysis rerun**. Detailed review and earlier checks are summarized in `docs/METHODOLOGICAL_REVIEW.md`.

The earlier reported fully adjusted uninsured-versus-insured odds ratio was **0.60** (95% CI **0.22–1.62**), based on **1,534** complete cases, with only **3 residual survey degrees of freedom**. This is an imprecise observational estimate, not a causal conclusion.

To obtain run-specific validation on your own machine, install Python dependencies and R `survey`, then run `python run_all.py`. If successful, `src/qa.py` will replace this snapshot note with a newly generated run-specific QA report.

**Outstanding steps:** reproducible run on the applicant's machine, independent assessment of variable definitions and analytic assumptions by a qualified epidemiologist, literature review updating, and accurate documentation of individual and AI contributions.
