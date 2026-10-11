# Focused literature review and evidence positioning

Search date October 10, 2026. Focused searches of PubMed, CDC and original publisher pages for NHANES, insurance, awareness and routine care; not a systematic review. This educational analysis extends an established topic. Full-text access was incomplete for some papers; below separates checked metadata/abstracts from interpretation.

| Verifiable publication | Checked evidence and relevance | Difference from this analysis |
|---|---|---|
| Egan BM, Li J, Small J, Nietert PJ, Sinopoli A. *The growing gap in hypertension control between insured and uninsured adults: National Health and Nutrition Examination Survey 1988 to 2010.* Hypertension. 2014;64:997–1004. [PubMed](https://pubmed.ncbi.nlm.nih.gov/25185135/), [DOI](https://doi.org/10.1161/HYPERTENSIONAHA.114.04276). | Abstract directly examines insurance-related care-cascade gaps, including awareness, among nonelderly adults. | Earlier pooled cycles and a different threshold/population. Insurance and awareness is not a new research question. |
| Duru OK et al. *Health insurance status and hypertension monitoring and control in the United States.* Am J Hypertens. 2007;20:348–353. [PubMed](https://pubmed.ncbi.nlm.nih.gov/17386339/), [DOI](https://doi.org/10.1016/j.amjhyper.2006.11.007). | Metadata and abstract establish prior NHANES work on insurance and hypertension care. | Earlier cycles and different operational ascertainment; not a direct numerical benchmark. |
| NCHS. *Characteristics of U.S. Adults With Hypertension Who Are Unaware of Their Hypertension, 2011–2014.* Data Brief 278. 2017. [CDC](https://www.cdc.gov/nchs/products/databriefs/db278.htm). | Official primary report describes awareness by insurance and healthcare utilization. | Different age range, survey years and case definition. |
| Calixte R, Chahal K, Besson A, Kaplan MS. *Access to routine health care and awareness of hypertension status among adults: Results from NHANES, 2011–2018.* [Publisher](https://www.sciencedirect.com/science/article/pii/S0091743523004292), [DOI](https://doi.org/10.1016/j.ypmed.2023.107843). | Publisher abstract connects routine care to awareness in adults 18–64. | Pooled cycles and different age boundary; usual care is secondary here. February 2024;179:107843 verified against the [author institution record](https://researchconnect.suny.edu/en/publications/access-to-routine-health-care-and-awareness-of-hypertension-statu/); DOI year is not publication year. |
| Muntner P et al. *Trends in blood pressure control among US adults with hypertension, 1999–2000 to 2017–2018.* JAMA. 2020;324:1190–1200. [PubMed](https://pubmed.ncbi.nlm.nih.gov/32902588/), [DOI](https://doi.org/10.1001/jama.2020.14545). | Primary report contextualizes hypertension care in the final pre-pandemic cycle. | Control differs from awareness; pooled trends cannot be estimated in one cycle. |

## Methods sources

- [Official DEMO_J](https://wwwn.cdc.gov/nchs/data/nhanes/public/2017/datafiles/DEMO_J.htm), [BPX_J](https://wwwn.cdc.gov/nchs/data/nhanes/public/2017/datafiles/BPX_J.htm), [BPQ_J](https://wwwn.cdc.gov/nchs/data/nhanes/public/2017/datafiles/BPQ_J.htm), [HIQ_J](https://wwwn.cdc.gov/nchs/data/nhanes/public/2017/datafiles/HIQ_J.htm), [HUQ_J](https://wwwn.cdc.gov/nchs/data/nhanes/public/2017/datafiles/HUQ_J.htm). Locally cached verbatim source codebooks.
- [CDC NHANES weighting](https://wwwn.cdc.gov/nchs/nhanes/tutorials/weighting.aspx) and [variance](https://wwwn.cdc.gov/nchs/nhanes/tutorials/varianceestimation.aspx).
- Parker JD et al. *NCHS Data Presentation Standards for Proportions.* Vital Health Stat 2(175). 2017, revised source PDF. [Report](https://www.cdc.gov/nchs/data/series/sr_02/sr02_175.pdf).
- R `survey` 4.5 installed package help and source, particularly `svyglm`, `svydesign`, `svyciprop`, `svyrecvar`; local reference session version is captured. [CRAN package](https://cran.r-project.org/package=survey).
- [STROBE statement and cross-sectional checklist](https://www.strobe-statement.org/).

## Contribution and scope

The contribution is a transparent one-cycle association estimate and a reproducible examination of medication-linked ascertainment, missing covariates and small design degrees of freedom. This review does not establish novelty, causal effectiveness of coverage, or current national awareness. Clinical cutoffs are operational study definitions; current guidelines and patient management are outside scope.
