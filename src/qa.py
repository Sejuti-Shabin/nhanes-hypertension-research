"""Summarize a verified executed run without relying on unpublished archives."""
import json
import pandas as pd
from data import ROOT, OUT
from validate import assert_current_validation

def run():
    report = assert_current_validation()
    tests = json.loads((OUT/'test_results.json').read_text())
    stages = json.loads((OUT/'execution.json').read_text())
    if not tests.get('passed') or any(s.get('returncode', 1) != 0 for s in stages):
        raise AssertionError('Unsuccessful stages/test outcomes; QA report not updated')
    reg = pd.read_csv(OUT/'regression.csv')
    m3 = reg[(reg.model == 'M3') & (reg.term == 'uninsured')].iloc[0]
    marginal = pd.read_csv(OUT/'marginal_probabilities.csv').iloc[2]
    design = int(m3.design_df); residual = int(m3.residual_df)
    doc = f"""# Computational QA and study limitations

This document was regenerated from a **completed, executed** analysis and numerical comparisons. It is not a faculty peer review and cannot validate untestable epidemiological assumptions.

## Statistical output

- Fully adjusted uninsured-versus-insured odds ratio: **{m3.odds_ratio:.2f}** (95% CI {m3.ci_low:.2f}–{m3.ci_high:.2f}); complete-case n={int(m3.n):,}.
- Full design df={design}, adjusted-model residual df={residual}. Wide intervals preclude a definitive adjusted conclusion.
- Standardized uninsured-minus-insured awareness difference: {100*marginal.estimate:.1f} percentage points (95% CI {100*marginal.ci_low:.1f}–{100*marginal.ci_high:.1f}).

## Executed checks

- Automated tests: {tests.get('tests_run')} executed; {tests.get('failed', 0)} failures, {tests.get('errors', 0)} errors.
- Numerical R/Python coefficient rows compared: {report.get('regression', {}).get('rows_compared','not recorded')}.
- Complete R/Python covariance entries compared: {report.get('full_covariance', {}).get('entries_compared','not recorded')}.
- Independent R domain checks: {report.get('independent_domains', {}).get('models','not recorded')}.
- Log files and run receipts are generated locally into `outputs/` but excluded from public version control. Current success is verified only after running `python run_all.py`.

## Limitations and authorship

Cross-sectional measurement, current-insurance/previous-diagnosis temporal ambiguity, operational hypertension definition, medication-related case selection, single-visit BP, missing data, small survey degrees of freedom, and observational confounding remain unresolved. Sensitivity analysis does not establish a causal effect or original discovery. The repository was developed with substantial AI assistance; document verified applicant contributions in `CONTRIBUTIONS.md`. Only a qualified epidemiology review can establish suitability for submission.
"""
    (ROOT/'QUALITY_ASSURANCE.md').write_text(doc)
    print('Computational QA report regenerated from verified outputs')

if __name__ == '__main__':
    run()
