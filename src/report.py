"""Generate manuscript and application materials from validated output tables."""
import json,re
from string import Template
import numpy as np
import pandas as pd
from data import ROOT,OUT
from validate import assert_current_validation

def pct(r):return f'{100*r.estimate:.1f}% (95% CI {100*r.ci_low:.1f}–{100*r.ci_high:.1f})'
def or_ci(r):return f'{r.odds_ratio:.2f} (95% CI {r.ci_low:.2f}–{r.ci_high:.2f})'
def mdtable(headers,rows):
    return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+'\n'.join('| '+' | '.join(map(str,row))+' |' for row in rows)

def run():
    validation=assert_current_validation()
    if not all(v['passed'] for v in validation.values()):raise ValueError('Unvalidated report')
    reg=pd.read_csv(OUT/'regression.csv');desc=pd.read_csv(OUT/'descriptive.csv');flow=pd.read_csv(OUT/'sample_flow.csv')
    marginal=pd.read_csv(OUT/'marginal_probabilities.csv');table1=pd.read_csv(OUT/'table1.csv')
    miss=pd.read_csv(OUT/'missingness.csv');profiles=pd.read_csv(OUT/'missingness_profiles.csv')
    diagnostics=json.loads((OUT/'python_diagnostics.json').read_text())
    support=pd.read_csv(OUT/'standardization_support.csv');cells=pd.read_csv(OUT/'model_cells.csv');target=json.loads((OUT/'target_definition.json').read_text());bounds=pd.read_csv(OUT/'ascertainment_bounds.csv');ipw=pd.read_csv(OUT/'pir_response_weighting.csv');ipws=pd.read_csv(OUT/'pir_response_summary.csv').iloc[0];jackknife=pd.read_csv(OUT/'r_jackknife_validation.csv');calibration=pd.read_csv(OUT/'inference_calibrations.csv');psu=pd.read_csv(OUT/'psu_influence.csv');components=pd.read_csv(OUT/'ascertainment_components.csv')
    def coefficient(model,term='uninsured'):return reg[(reg.model==model)&(reg.term==term)].iloc[0]
    primary=coefficient('M3');m1=coefficient('M1');m2=coefficient('M2')
    insured=desc[(desc.group=='Insured')&(desc.estimand=='Awareness prevalence')].iloc[0]
    uninsured=desc[(desc.group=='Uninsured')&(desc.estimand=='Awareness prevalence')].iloc[0]
    overall=desc[(desc.group=='All')&(desc.estimand=='Awareness prevalence')].iloc[0]
    prevalence=desc[desc.estimand=='Hypertension prevalence'].iloc[0]
    n=int(primary.n);analytic=int(m1.n)
    abstract=f'The outcome/exposure-complete sample included {analytic:,} participants; Model 3 included {n:,}. Awareness was {pct(insured)} among insured and {pct(uninsured)} among uninsured adults. The fully adjusted uninsured-versus-insured odds ratio was {or_ci(primary)} (p={primary.p:.3f}; residual design df={int(primary.residual_df)}). The standardized uninsured-minus-insured awareness difference was {100*marginal.iloc[2].estimate:.1f} percentage points (95% CI {100*marginal.iloc[2].ci_low:.1f}–{100*marginal.iloc[2].ci_high:.1f}). Sensitivity estimates were generally imprecise, with a direction reversal in the measured-only 140/90 domain.'
    sections=[]
    sections.append('### Participant selection and descriptive estimates\n\n'+f'The source contained {int(flow.iloc[0].n):,} respondents, of whom {int(flow.iloc[1].n):,} were aged 20–64. The examined target included {int(flow.iloc[2].n):,} adults, of whom {int(flow.iloc[3].n):,} had classifiable operational hypertension status using available BP or current medication. Operational hypertension eligibility included {int(flow.iloc[4].n):,}; {int(flow.iloc[4].n-flow.iloc[5].n)} lacked valid awareness or insurance. The outcome/exposure-complete sample contained {analytic:,} adults. Figure 1 and sample_flow.csv show sequential counts. There were {target['unclassifiable_n']:,} examined adults with unresolved ascertainment, including one BP-complete adult with unknown medication and below-threshold BP. Revised eligibility admits {target['known_medication_missing_bp_n']} current-medication cases without complete BP. These are post-review changes; the submitted BP-complete model is preserved as sensitivity.\n\n'+f'Weighted operational hypertension prevalence among ascertainment-classifiable examined adults was {pct(prevalence)} (n={int(prevalence.n):,}). Awareness among hypertension-eligible adults with valid awareness was {pct(overall)} (n={int(overall.n):,}), while insurance-specific denominators were {int(insured.n):,} insured and {int(uninsured.n):,} uninsured. Awareness was {pct(insured)} and {pct(uninsured)}, respectively. These outcome-specific estimates do not all use the same denominator.\n\n')
    sections.append('### Table 1. Study population by insurance\n\n')
    rows=[]
    labels={'RIDAGEYR':'Age (years)','pir':'Income-to-poverty ratio','sbp':'Mean SBP (mmHg)','dbp':'Mean DBP (mmHg)','awareness':'Awareness (%)','sex':'Sex','race':'Race/ethnicity','education':'Education','pir_group':'PIR category'}
    for (v,level),group in table1.groupby(['variable','level'],sort=False):
        row=[labels[v]+(' · '+level if level not in ['Mean','Aware'] else '')]
        for insurance in ['Insured','Uninsured']:
            r=group[group.insurance==insurance].iloc[0];binary=v not in ['RIDAGEYR','pir','sbp','dbp']
            estimate=pct(r) if binary else f'{r.estimate:.1f} ({r.ci_low:.1f}–{r.ci_high:.1f})'
            if str(r.reliability).startswith('suppress:'):estimate='Suppressed†'
            count=int(r.category_n) if np.isfinite(r.category_n) else int(r.n)
            label=f'category n={count:,}; denominator n={int(r.n):,}' if np.isfinite(r.category_n) else f'denominator n={int(r.n):,}'
            row.append(f'{estimate}; {label}; missing n={int(r.total_group_n-r.n):,}')
        rows.append(row)
    table1_rendered=mdtable(['Characteristic','Insured','Uninsured'],rows)
    (ROOT/'TABLES.md').write_text('# Table 1. Study population by insurance\n\n'+table1_rendered+'\n\nWeighted estimates; category n, valid denominator n and missing n are unweighted. †NCHS numeric suppression flag. Machine table: outputs/table1.csv. Variable-specific denominators do not imply complete measurements for medication-confirmed cases.\n')
    sections.append('[Full Table 1 with category counts, variable-specific denominators and missingness](TABLES.md).\n\nPercentages are weighted; Category counts, valid denominators and missing counts are unweighted and printed separately. Composition denominators are variable-specific and recorded in table1.csv. †Fails NCHS numeric reliability screening; estimates and flags are retained in machine-readable outputs for audit. No baseline significance-screening tests were conducted.\n\n')
    sections.append('### Adjusted models and absolute estimates\n\n'+f'Model 1 produced uninsured-versus-insured OR {or_ci(m1)} (p={m1.p:.3f}); Model 2 produced {or_ci(m2)} (p={m2.p:.3f}). Model 3 produced aOR {or_ci(primary)} (p={primary.p:.3f}), based on {n:,} cases with {int(primary.events):,} aware outcomes and {n-int(primary.events):,} unaware outcomes. Model 3 residual reference degrees of freedom were {int(primary.residual_df)}, compared with {int(m1.residual_df)} and {int(m2.residual_df)} for Models 1 and 2.\n\n'+mdtable(['Model','N','Uninsured OR (95% CI)','Residual df'],[[name,f'{int(coefficient(name).n):,}',or_ci(coefficient(name)),int(coefficient(name).residual_df)] for name in ['M1','M2','M3','M1_common','M2_common']])+'\n\n'+f'Standardized awareness probability was {pct(marginal.iloc[0])} for insured and {pct(marginal.iloc[1])} for uninsured status in the weighted Model 3 covariate distribution. The difference was {100*marginal.iloc[2].estimate:.1f} percentage points (95% CI {100*marginal.iloc[2].ci_low:.1f}–{100*marginal.iloc[2].ci_high:.1f}). These primary marginal intervals use {int(marginal.iloc[2].inference_df)} model residual reference df, matching coefficient inference, with joint distribution/model linearization. Individual probabilities use logit-transformed bounded intervals. Full-design-df coefficient calibration is a separate reference sensitivity, not a new variance estimate.\n\n')
    retention=profiles[profiles.variable=='complete_covariates'].iloc[0]
    missing_pir=miss[(miss.population=='Hypertension eligible')&(miss.variable=='pir')].iloc[0]
    diag=next(x for x in diagnostics if x['model']=='M3');c=cells[cells.model=='M3']
    sections.append('### Missingness, ascertainment and diagnostics\n\n'+f'Model 3 excluded {analytic-n:,} outcome/exposure-complete participants for covariate missingness. Its weighted retention was {100*retention.estimate:.1f}%. In the broader hypertension-eligible domain, PIR was missing for {int(missing_pir.missing_n):,} participants ({100*missing_pir.missing_weighted_fraction:.1f}% of weighted cases). Included and excluded profiles, common-sample coefficients and awareness bounds are retained in separate output files; they do not eliminate nonresponse bias.\n\n'+f'The primary model converged, had rank {diag["rank"]}, prediction range {diag["min_prediction"]:.3f}–{diag["max_prediction"]:.3f}, weighted information condition number {diag["bread_condition"]:.1f}, maximum weighted leverage {diag["max_weighted_leverage"]:.3f} and positive minimum covariance eigenvalue. No individually tabulated Model 3 category had zero outcomes; the smallest category had {int(c.n.min()):,} cases. Insurance-by-category cells were smaller: the minimum contained {int(support.loc[support.level.notna(),'n'].min())} cases with as few as {int(support.loc[support.level.notna(),'aware_n'].min())} aware outcomes. All categorical levels were present in both insurance groups, but marginal standardization remains model-dependent and small cells limit support. This check does not rule out sparsity in combinations of categories. All {len(psu)} delete-one-PSU fits converged; uninsured log-odds coefficients ranged from {psu.uninsured_beta.min():.3f} to {psu.uninsured_beta.max():.3f}, showing design-unit influence even though no deletion reversed the primary direction.\n\n'+f'Among BP-below-threshold medication-only cases with valid insurance/awareness, there were {int(components[(components.component.str.startswith("Medication"))&(components.uninsured==0)].iloc[0].n):,} insured and {int(components[(components.component.str.startswith("Medication"))&(components.uninsured==1)].iloc[0].n):,} uninsured adults. All reported awareness, illustrating the questionnaire/ascertainment linkage rather than proving absence of bias.\n\n')
    sections.append('### Original-protocol and post-review sensitivity analyses\n\n'+mdtable(['Specification','N','Uninsured OR (95% CI)'],[[name,f'{int(coefficient(name).n):,}',or_ci(coefficient(name))] for name in ['threshold140','measured130','measured140','readings23','readings1234','two_readings','age20_59','age30_64','bp_complete','insured_no_lapse','exclude_pregnant','omit_pir','quadratic_age','categorical_pir']])+'\n\n'+f'The measured-only 130/80 estimate was {or_ci(coefficient("measured130"))}; the measured-only 140/90 estimate was {or_ci(coefficient("measured140"))}, reversing the primary point-estimate direction. Thus direction was not invariant across all case definitions, and imprecision precluded firm sensitivity conclusions. The secondary no-usual-care association was {or_ci(coefficient("usual_care","no_usual_care"))}; after also including insurance it was {or_ci(coefficient("usual_care_insurance","no_usual_care"))}. These exploratory coefficients are not causal or mediation effects, and no multiplicity correction supports significance-based interpretation.\n\n')
    htb=bounds[(bounds.estimand=='Hypertension prevalence')&(bounds.group=='All')]
    awb=bounds[(bounds.estimand=='Awareness prevalence')&(bounds.group=='All')]
    ipwor=ipw[ipw.estimand=='Uninsured odds ratio'].iloc[0]
    alt=calibration[(calibration.model=='M3')&(calibration.reference=='full_design')].iloc[0]
    sections.append('### Post-review missingness, ascertainment and inference checks\n\n'+f'Weighted worst-case ascertainment bounds among all {target["all_target_exam_n"]:,} examined target adults were {100*htb.estimate.min():.1f}–{100*htb.estimate.max():.1f}% for operational hypertension prevalence and {100*awb.estimate.min():.1f}–{100*awb.estimate.max():.1f}% for awareness when unresolved cases/outcomes were assigned feasible extremes. These are identification sensitivity endpoints conditional on the observed examination sample, not a combined confidence interval or a bound on clinical truth. They do not account for examination nonparticipation.\n\n'+f'The missing-PIR response-weighting sensitivity targeted {int(ipws.target_n):,} outcome/exposure- and non-PIR-covariate-complete cases, of whom {int(ipws.missing_pir_n):,} had missing PIR; {int(ipws.education_or_other_non_PIR_excluded_n)} case still lacked another required covariate. It yielded uninsured OR {ipwor.estimate:.2f} (95% CI {ipwor.ci_low:.2f}–{ipwor.ci_high:.2f}). Response probabilities ranged {ipws.min_response_probability:.3f}–{ipws.max_response_probability:.3f}, maximum inverse response factor was {ipws.max_inverse_response_weight:.2f}, and Kish effective weight n was {ipws.respondent_effective_weight_n:.1f} (a weight-dispersion diagnostic, not full survey-design effective n). All 30 JKn replicates refit auxiliary means, response and outcome models. The sensitivity assumes PIR MAR conditional on observed predictors and response positivity; neither is established by the observed records, and no independent Python response-weighting verification is claimed.\n\n'+f'For primary nonlinear standardization, independently refit R JKn/Taylor SE ratios ranged {jackknife.jackknife_taylor_se_ratio.min():.3f}–{jackknife.jackknife_taylor_se_ratio.max():.3f}; this is reassuring diagnostic agreement, not exact equivalence. Retaining identical Model 3 coefficients/SE but using full design df gave OR {or_ci(alt)}. The conservative residual-df analysis remains primary; neither calibration establishes a clear adjusted association.\n\n')
    comparison=pd.read_csv(OUT/'validation_comparison.csv')
    sections.append('### Validation and figures\n\n'+f'Independent raw coding checks passed for {validation["raw_coding"]["variables"]} core variables. Python/R comparisons passed for {validation["regression"]["rows_compared"]} coefficient rows, {validation["descriptive"]["rows_compared"]} descriptive rows, {validation["table1"]["rows_compared"]} Table 1 rows and {validation["marginal"]["rows_compared"]} marginal estimates; every R regression mask was rebuilt independently and {validation['full_covariance']['entries_compared']:,} full covariance entries compared. The automated test outcomes are recorded in outputs/test_results.json. Agreement concerns coding and numerical inference, not the correctness of every epidemiological assumption.\n\n')
    for name,label in [('participant_flow','Participant flow'),('awareness_by_insurance','Crude awareness'),('adjusted_odds_ratios','Adjusted odds ratios'),('adjusted_probabilities','Standardized probabilities'),('sensitivity_comparisons','Sensitivity comparisons')]:
        sections.append(f'![{label}](figures/{name}.png)\n\n')
    sections.append('Figure captions and interval conventions: figures/CAPTIONS.md. All figures have 300-DPI PNG and vector PDF versions.\n\n')
    manuscript=Template((ROOT/'docs/manuscript_template.md').read_text()).substitute(abstract_results=abstract,results=''.join(sections))
    (ROOT/'MANUSCRIPT.md').write_text(manuscript)
    words=len(re.findall(r'\b[\w–]+\b',manuscript.split('## References')[0]))
    (OUT/'manuscript_metadata.json').write_text(json.dumps({'word_count_excluding_references':words,'source':'docs/manuscript_template.md + validated CSV files'},indent=2))
    title='Health Insurance Coverage and Hypertension Awareness Among U.S. Adults'
    findings=f'Awareness was {100*insured.estimate:.1f}% among insured and {100*uninsured.estimate:.1f}% among uninsured adults. The fully adjusted uninsured-versus-insured OR was {or_ci(primary)}; the interval included no association. The primary adjusted sample contained {n:,} adults, with only {int(primary.residual_df)} residual survey df.'
    readme=f'''# {title}

**NHANES 2017–2018 · reproducible epidemiology · Python + R survey**

An audited historical descriptive replication/extension asking whether uninsured U.S. adults aged 20–64 meeting an operational hypertension definition report lower awareness after demographic and socioeconomic adjustment.

## Actual findings

{findings} The measured-only 140/90 sensitivity reversed direction and was imprecise. This is an educational AI-assisted manuscript draft, not a publication or an identified causal study.

![Weighted awareness](figures/awareness_by_insurance.png)

## Start here

- [Journal review and revision disposition](REVIEW.md): prioritized concerns, repairs and unresolved limits.\n- [Research protocol](research_protocol.md): hypothesis, estimands, conceptual diagram and planned sensitivities; version 2 amendments are post-review/exploratory; version 1 is preserved.
- [Manuscript](MANUSCRIPT.md): generated results and interpretation.
- [Methodological review](METHODOLOGICAL_REVIEW.md): audit limitations and unresolved scientific questions; private archives are excluded.
- [Faculty outreach summary](docs/FACULTY_OUTREACH.md) and [application materials](docs/APPLICATION_MATERIALS.md).
- [Final QA report](QUALITY_ASSURANCE.md) and [STROBE crosswalk](docs/STROBE_CHECKLIST.md).

## Reproduce

Python 3.10+ and R with survey are required. From the repository directory:

```bash
python -m pip install -r requirements.txt
Rscript -e 'install.packages("survey", repos="https://cloud.r-project.org")'
python run_all.py
```

See the repository-root `REPRODUCIBILITY.md` for requirements. The public repository excludes cached raw files; the first run downloads official CDC NHANES 2017–2018 sources and checks them against recorded hashes.

## Repository map

| Location | Purpose |
|---|---|
| src/data.py | Source ingestion, integrity and documented coding |
| src/survey.py | Independent Python score/Taylor inference and standardization |
| src/pipeline.py | Domains, descriptive analysis, 21 model specifications plus reviewer-directed R replicate/MAR sensitivities, diagnostics |
| r/survey_analysis.R | Raw coding, independently reconstructed masks, full covariance and reference inference |
| r/reviewer_sensitivities.R | Refit JKn standardization and MAR-dependent PIR response weighting |
| src/validate.py | Numerical comparison with R |
| src/figures.py, src/report.py | Calculated figures, manuscript and summaries |
| tests/ | Synthetic edge cases, design and authentic-data tests |
| data/raw/, data_dictionary.csv | Authentic sources and variable definitions |
| outputs/ | Table 1, prevalence, coefficients, sensitivities, diagnostics and validation |
| figures/ | Five PNG/PDF pairs and captions |
| docs/METHODOLOGICAL_REVIEW.md | Prior internal methodological critique; excludes private archives |

## Scientific choices and limits

Examination weights, masked strata and clusters are retained before domain analysis. Revised primary hypertension includes mean BP ≥130/80 or current medication; sensitivity uses measured-only cases. BPQ040A is ever advised medication; BPQ050A is current use. Unknown responses remain missing except documented structural skips. Model 3 includes age, sex, race/ethnicity, education and PIR. R survey supplies reported inference; Python ordinary weighted-GLM covariance is never presented as survey variance.

Cross-sectional timing, medication-linked selection, self-report, single-visit BP, missing income and low design df limit interpretation. No current national prevalence or clinical diagnosis claim. Formal publication requires qualified epidemiology review and applicant verification of personal contributions.

## Data and attribution

[Official CDC release](https://wwwn.cdc.gov/nchs/nhanes/search/DataPage.aspx?Cycle=2017-2018), [provenance](outputs/provenance.json), [data reuse notes](DATA_PROVENANCE.md). No private participant information was obtained. No claim of faculty supervision, peer review or personal applicant authorship is made. No code license is imposed on the user's behalf; see LICENSE_NOTES.md.
'''
    # Keep the hand-curated public README untouched during report generation.
    outreach=f'''# One-page project summary

**{title}: NHANES 2017–2018**  
Applicant: [name] · Educational secondary analysis; AI-assisted, not peer reviewed

**Question.** Among U.S. adults aged 20–64 meeting an operational hypertension definition, is current lack of insurance associated with lower self-reported awareness after demographic/SES adjustment?

**Data and design.** Authentic CDC DEMO_J, BPX_J, BPQ_J, HIQ_J and HUQ_J; one-to-one merges; operational hypertension defined by available first-three BP means ≥130/80 or current prescribed medication. Awareness uses BPQ020; insurance uses HIQ011. The analysis preserves the full positive-weight MEC design before subpopulation restriction and admits medication-confirmed cases without BP. Reviewer-directed changes are post hoc.

**Methods.** Weighted descriptions and logistic Models 1–3, Taylor linearization with masked strata/PSUs, R survey reference inference, independent Python numerical comparisons. The final model adjusts for age, sex, six race/ethnicity groups, four education groups and continuous PIR. Common-sample models, measurement/threshold/case-definition sensitivities, MAR-dependent missing-PIR response weighting with refit PSU replicates, missingness profiles and influence diagnostics accompany the main results.

**Actual findings.** {findings} Standardized uninsured-minus-insured awareness difference: {100*marginal.iloc[2].estimate:.1f} percentage points (95% CI {100*marginal.iloc[2].ci_low:.1f}–{100*marginal.iloc[2].ci_high:.1f}). This does not establish an adjusted association. Measured-only 140/90 estimates reversed direction with wide uncertainty.

**Limits.** Cross-sectional and historical; awareness self-reported; BP measured at one visit. Medication inclusion is linked to diagnosis and changes selection. Primary complete cases exclude some participants with missing income; a MAR-dependent response-weighting sensitivity is not a verified cure; ordinary examination weights do not repair item missingness. Model 3 has few residual design df. No causal or novelty claim.

**Reproducible artifacts.** Protocol, audited original, data dictionary, modular pipeline, R validation, tests, Table 1, regression/sensitivity outputs, five PNG/PDF figures and manuscript. Code and actual outputs are ready for review.

**Contribution disclosure.** AI performed substantial coding and writing in this iteration. Applicant must rerun, understand, independently review and document their actual contribution before presenting the work. Supervision and publication are not claimed.

**Research development.** Qualified review priorities: target/ascertainment bias, residual-df convention, sparse categories/overlap, survey-compatible missing-data strategy and whether a prespecified multi-cycle extension is justified.
'''
    (ROOT/'docs/FACULTY_OUTREACH.md').write_text(outreach)
    application=f'''# Application materials — adapt only after verifying personal contribution

## Statement of purpose research description (three paragraphs)

I am developing my understanding of epidemiologic measurement and complex survey analysis through an AI-assisted secondary analysis of NHANES 2017–2018. The project asks whether lack of current health insurance is associated with lower reported hypertension awareness among adults aged 20–64. Its protocol distinguishes previous diagnosis from measured BP and examines how including medication users changes the population under study. Before using this statement, I will verify and document the components that I personally reran, reviewed and extended.

The workflow joins authentic CDC components, applies documented questionnaire skip patterns and retains examination weights, strata and clusters for domain inference. R survey provides reference logistic-model inference, while Python handles processing, tests, visualization and independent numerical comparisons. {findings} Sensitivity analyses made clear that case definition, missing covariates and survey design degrees of freedom affect interpretation; the project does not establish a causal insurance effect.

The next work I intend to undertake is an independently reviewed missing-data strategy, more explicit investigation of temporal coverage history and a protocol-driven assessment of whether additional survey cycles would support a more precise target estimate. The value of this project for my training is learning to connect a clinical question to defensible definitions and uncertainty, and to report inconclusive evidence transparently. I will describe it as a portfolio manuscript draft and disclose computational assistance, rather than claim peer review or faculty supervision.

## CV-ready description

**Independent public-data research portfolio (AI-assisted), NHANES 2017–2018 — manuscript draft.** Developed/reviewed [replace with verified personal contribution] a reproducible Python/R survey workflow evaluating insurance and hypertension awareness in {n:,} complete-case adults; incorporated masked survey design, ascertainment and missingness sensitivities, independent numerical validation and uncertainty-focused reporting. Fully adjusted OR {primary.odds_ratio:.2f} (95% CI {primary.ci_low:.2f}–{primary.ci_high:.2f}); no clear adjusted association established.

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
'''
    (ROOT/'docs/APPLICATION_MATERIALS.md').write_text(application)
    print('Generated manuscript:',words,'words excluding references; application snippets')

if __name__=='__main__':run()
