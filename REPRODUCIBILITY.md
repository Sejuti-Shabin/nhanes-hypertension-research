# Reproducibility guide

## Scope of this public release

This is a **cleaned portfolio edition**, derived from an earlier executed analysis. The checked-in tables and figures are **snapshots of that run**, not evidence that every step was independently rerun in a clean public checkout. To verify a new run, execute the end-to-end pipeline below. Source data and person-level derived files are not included in this public package.

## Requirements

- Python 3.10+; packages pinned in `requirements.txt` (use a virtual environment).
- R 4.x with `survey` and `foreign`; run `Rscript -e 'install.packages(c("survey", "foreign"), repos="https://cloud.r-project.org")'` if required.
- Internet access for the first run to fetch **official CDC NHANES 2017–2018 XPORT and codebook files**, or locally populated `data/raw/` using the **exact files** recorded in `data/source_manifest.json`.
- Approximately several minutes for data processing, fitting, and testing; compute time varies by machine.

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
Rscript -e 'install.packages(c("survey", "foreign"), repos="https://cloud.r-project.org")'
python run_all.py
```

For testing only the repository packaging (without downloading sources or installing R):

```bash
python -m unittest discover -s tests -p 'test_public_release.py' -v
```

After `run_all.py` completes, inspect `outputs/run_state.json`, `outputs/validation.json`, `outputs/validation_provenance.json`, `outputs/logs/`, and `outputs/test_results.json`. Failures invalidate earlier status receipts; do not present stale results as currently reproduced. `python run_all.py --check-only` tests the fully generated outputs and **is not a substitute for a fresh full run**.

## Source identity and survey analysis

Five official NHANES 2017–2018 components are used: `DEMO_J`, `BPX_J`, `BPQ_J`, `HIQ_J`, `HUQ_J`. The source loader checks file hashes against `data/source_manifest.json`; a changed CDC file prompts manual review rather than automatic acceptance. Do not edit the manifest simply to suppress a mismatch. Official documentation: https://wwwn.cdc.gov/nchs/nhanes/search/DataPage.aspx?Cycle=2017-2018

The full **MEC sample** is retained when constructing masked design strata, primary sampling units and examination weights; the age/hypertension domain is defined after the survey design. R `survey` computes reference intervals, weighted models and analytic sensitivities. Python separately implements and validates survey score/Taylor calculations. The main adjusted model has **three residual survey degrees of freedom**; estimates are imprecise and should not be interpreted causally.

Validation compares independently reconstructed R model domains and coded variables, coefficients and covariance, and selected sensitivity outputs. Exact-version requirements and tolerance documentation are in the code and `src/validate.py`. A successful numerical run is **not** an independent assessment of epidemiological assumptions, missing-data assumptions, validity of causal inference, or peer review.

## What's intentionally not committed

`data/raw/*` (CDC XPORT/codebooks), `outputs/design_frame.csv` (person-level analytic records), `outputs/observation_influence.csv`, `outputs/pir_response_diagnostics.csv`, `outputs/r_model_objects.rds`, model receipt/status files, build products and earlier large internal backups. These are created locally or only belong in private review archives. See `.gitignore`.

## Generated versus hand-edited content

`src/report.py` regenerates `MANUSCRIPT.md`, `TABLES.md`, and the docs/application snippets from validated tables; it does **not** overwrite the hand-curated public `README.md`. `src/qa.py` regenerates the computational QA report after a successful pipeline run. Review the manuscript, its citations, and AI-contribution disclosure before putting your name on it.

## Scientific limits

A single cross-sectional NHANES cycle, case-ascertainment/medication coupling, survey sample size and only three residual degrees of freedom constrain inference. Missing-PIR sensitivity depends on unverified MAR and model assumptions. The data do not establish that insurance causes diagnosis or awareness. Keep the distinction between existing-data replication, research training and original published research.
