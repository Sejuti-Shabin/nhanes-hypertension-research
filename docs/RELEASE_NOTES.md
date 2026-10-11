# Public GitHub edition — release notes

Prepared from the user's `insurance-hypertension-study.zip` on October 10, 2026. This is **repository cleanup**, not new statistical research.

## Changed

- Removed internal snapshots and full prior-project duplicates, compiled libraries, local environment artifacts and Python caches.
- Omitted source CDC `.xpt`/`.htm` files and participant-level derived `SEQN` analysis/influence tables from the public package. The pipeline can download authentic CDC source files; `data/source_manifest.json` checks identities.
- Retained relevant statistical source code, R `survey` scripts, unit tests, sensitivity analyses, research protocol, manuscript, published-data provenance, aggregate result tables, original figures and the eight-page writing-sample PDF.
- Replaced development-centric README with a faculty-facing landing page and a clear AI-contribution disclosure and release-specific reproducibility guidance.
- Changed report regeneration so it does not overwrite the public README; modified computational QA generation so it no longer requires private backup snapshots.
- Expanded `.gitignore` so a future pipeline run does not accidentally add participant-level data or ephemeral receipts to GitHub.

## Local checks during cleanup

- **3/3** public-package smoke tests passed.
- **13/13** selected Python coding and authentic-data tests passed using authentic CDC source files in a *temporary test copy*; the temporary copy is not in the public ZIP.
- Python source compiled successfully.
- **Not run:** two tests requiring R execution or the original full source/output receipt state; a complete public end-to-end rerun remains pending because `Rscript` was not available in the packaging environment.
- This cleanup did **not** recompute or claim to independently validate the reported survey results.

## Before presenting as applicant's own work

Perform a full local rerun, assess data source validity and current statistical methods, verify citations and case definitions, solicit expert critique where possible, and truthfully document the applicant's coding, methodological and writing contributions in `CONTRIBUTIONS.md`. The project should be described as a training manuscript, **not** as a published paper or a new scientific discovery.
