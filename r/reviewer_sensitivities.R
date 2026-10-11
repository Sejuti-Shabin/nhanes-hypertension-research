# Post-review sensitivities: independent nonlinear JKn and missing-PIR weighting.
suppressPackageStartupMessages(library(survey))
options(survey.lonely.psu='fail')
args<-commandArgs(trailingOnly=TRUE);root<-if(length(args))normalizePath(args[1])else normalizePath('.')
out<-file.path(root,'outputs')
d<-read.csv(file.path(out,'design_frame.csv'),na.strings=c('','NA'),check.names=FALSE)
levels_list<-list(sex=c('Female','Male'),race=c('White','Black','Mexican American','Other Hispanic','Asian','Other/multiracial'),
 education=c('College graduate','Some college/AA','High school/GED','Below high school'))
for(v in names(levels_list))d[[v]]<-factor(d[[v]],levels=levels_list[[v]])
full<-svydesign(ids=~SDMVPSU,strata=~SDMVSTRA,weights=~WTMEC2YR,nest=TRUE,data=d)
repfull<-as.svrepdesign(full,type='JKn',mse=TRUE)
formula<-awareness ~ uninsured + age10 + sex + race + education + pir
conservative_df<-degf(full)-(ncol(model.matrix(formula,d[d$domain_m3==1,]))-1)

score_model <- function(data,w,formula) {
 if(sum(w)>0)w<-w/mean(w[w>0]) else stop('Empty weighted model')
 x<-model.matrix(formula,data)
 if(qr(x[w>0,,drop=FALSE])$rank!=ncol(x))stop('Rank-deficient replicate score')
 data$.analysis_weight<-w
 model<-glm(formula,data=data,weights=.analysis_weight,family=quasibinomial(),control=glm.control(epsilon=1e-12,maxit=200))
 if(!model$converged||any(!is.finite(coef(model))))stop('Unstable replicate model')
 model
}
standardize <- function(mod,data,w) {
 # Nuisance-adjusted empirical distribution is included by recomputing each replicate.
 predictions<-sapply(0:1,function(status){z<-data;z$uninsured<-status;as.numeric(predict(mod,newdata=z,type='response'))})
 means<-colSums(predictions*w)/sum(w)
 c(uninsured_beta=unname(coef(mod)['uninsured']),Insured=means[1],Uninsured=means[2],Difference=means[2]-means[1])
}
ccrep<-subset(repfull,domain_m3==1)
cc<-withReplicates(ccrep,function(w,data)standardize(score_model(data,w,formula),data,w),return.replicates=TRUE)
taylor<-read.csv(file.path(out,'marginal_probabilities.csv'));rt<-read.csv(file.path(out,'regression.csv'))
reference<-c(rt$se[rt$model=='M3'&rt$term=='uninsured'],taylor$se)
check<-data.frame(estimand=names(coef(cc)),estimate=as.numeric(coef(cc)),jackknife_se=as.numeric(SE(cc)),taylor_se=reference,
                 jackknife_taylor_se_ratio=as.numeric(SE(cc))/reference,n=sum(d$domain_m3==1),replicates=ncol(weights(ccrep,type='analysis')))
check$review_flag<-ifelse(check$jackknife_taylor_se_ratio<.70|check$jackknife_taylor_se_ratio>1.30,'review discrepancy','within diagnostic range (not equivalence test)')
write.csv(check,file.path(out,'r_jackknife_validation.csv'),row.names=FALSE)
write.csv(as.data.frame(cc$replicates),file.path(out,'r_jackknife_replicates.csv'),row.names=FALSE)

# Response weighting addresses PIR item missingness only, under a stated MAR model.
# Education-missing records (one in this snapshot) remain excluded and counted.
base<-d$domain_analytic==1&complete.cases(d[,c('age10','sex','race','education','awareness','uninsured','no_usual_care')])
# Fill missing auxiliary BP only for nuisance prediction; never substitute analytic BP.
# The common missing-BP flag retains the distinction. Predominantly medication-confirmed cases.
d$bp_missing<-as.numeric(is.na(d$sbp)|is.na(d$dbp))
mean_s<-weighted.mean(d$sbp[base],d$WTMEC2YR[base],na.rm=TRUE)
mean_d<-weighted.mean(d$dbp[base],d$WTMEC2YR[base],na.rm=TRUE)
d$sbp_aux<-ifelse(is.na(d$sbp),mean_s,d$sbp)/10
d$dbp_aux<-ifelse(is.na(d$dbp),mean_d,d$dbp)/10
d$log_exam_weight<-log(d$WTMEC2YR)
d$pir_observed<-as.numeric(!is.na(d$pir))
# Means are nuisance transformations only. Their estimation is recomputed within each replicate below.
response_formula<-pir_observed ~ uninsured * awareness + age10 + I(age10^2) + sex + race + education + sbp_aux + dbp_aux + bp_missing + no_usual_care + log_exam_weight
full_ipw<-svydesign(ids=~SDMVPSU,strata=~SDMVSTRA,weights=~WTMEC2YR,nest=TRUE,data=d)
rep_ipw<-as.svrepdesign(full_ipw,type='JKn',mse=TRUE)
ipw_design<-subset(rep_ipw,base)
fit_ipw <- function(w,data,details=FALSE) {
 # Repeat auxiliary filling means, response fitting and weighted regression under every replicate.
 ms<-weighted.mean(data$sbp,w,na.rm=TRUE);md<-weighted.mean(data$dbp,w,na.rm=TRUE)
 data$sbp_aux<-ifelse(is.na(data$sbp),ms,data$sbp)/10
 data$dbp_aux<-ifelse(is.na(data$dbp),md,data$dbp)/10
 response<-score_model(data,w,response_formula)
 probability<-as.numeric(predict(response,type='response'))
 if(any(!is.finite(probability))||any(probability<=0)||any(probability>=1))stop('Nonfinite response probability / separation')
 observed<-data$pir_observed==1
 adjusted_weights<-w[observed]/probability[observed]
 outcome<-score_model(data[observed,],adjusted_weights,formula)
 values<-standardize(outcome,data[observed,],adjusted_weights)
 if(details)return(list(values=values,probability=probability,observed=observed,response=response,adjusted_weights=adjusted_weights))
 values
}
ipw<-withReplicates(ipw_design,fit_ipw,return.replicates=TRUE)
point<-fit_ipw(d$WTMEC2YR[base],d[base,],TRUE)
q<-qt(.975,conservative_df);vals<-as.numeric(coef(ipw));ses<-as.numeric(SE(ipw))
rows<-data.frame(estimand=names(coef(ipw)),estimate=vals,se=ses,ci_low=vals-q*ses,ci_high=vals+q*ses,
                inference_df=conservative_df,target_n=sum(base),observed_pir_n=sum(base&!is.na(d$pir)))
for(i in 1:nrow(rows)) {
 if(i==1){rows$estimate[i]<-exp(vals[i]);rows$ci_low[i]<-exp(vals[i]-q*ses[i]);rows$ci_high[i]<-exp(vals[i]+q*ses[i]);rows$estimand[i]<-'Uninsured odds ratio';rows$se[i]<-ses[i]}
 if(i %in% 2:3){rows$ci_low[i]<-plogis(qlogis(vals[i])-q*ses[i]/(vals[i]*(1-vals[i])));rows$ci_high[i]<-plogis(qlogis(vals[i])+q*ses[i]/(vals[i]*(1-vals[i])))}
}
rows$ci_method<-c('log-OR JKn t','logit-probability JKn t','logit-probability JKn t','difference JKn t')
write.csv(rows,file.path(out,'pir_response_weighting.csv'),row.names=FALSE)
write.csv(as.data.frame(ipw$replicates),file.path(out,'pir_response_replicates.csv'),row.names=FALSE)
records<-d[base,c('SEQN','uninsured','awareness','pir_observed','WTMEC2YR')]
records$response_probability<-point$probability
records$inverse_response_weight<-1/point$probability
write.csv(records,file.path(out,'pir_response_diagnostics.csv'),row.names=FALSE)
summary<-data.frame(target_n=sum(base),education_or_other_non_PIR_excluded_n=sum(d$domain_analytic==1)-sum(base),
 observed_pir_n=sum(point$observed),missing_pir_n=sum(!point$observed),
 min_response_probability=min(point$probability),max_response_probability=max(point$probability),
 min_inverse_response_weight=min(1/point$probability),max_inverse_response_weight=max(1/point$probability),
 respondent_effective_weight_n=sum(point$adjusted_weights)^2/sum(point$adjusted_weights^2),
 response_model_rank=point$response$rank,replicate_count=nrow(ipw$replicates),
 variance='Stratified delete-one-PSU JKn; nuisance response and outcome models refit in each replicate',
 assumptions='MAR for PIR given modeled observed variables, response positivity and correct nuisance/outcome specification; not verified from data')
write.csv(summary,file.path(out,'pir_response_summary.csv'),row.names=FALSE)
writeLines(paste(deparse(response_formula),collapse=' '),file.path(out,'pir_response_model.txt'))
stopifnot(all(is.finite(as.matrix(ipw$replicates))),all(is.finite(check$jackknife_se)))
receipt_paths<-c('r/reviewer_sensitivities.R','outputs/design_frame.csv','outputs/regression.csv','outputs/marginal_probabilities.csv',paste0('outputs/',c('r_jackknife_validation.csv','r_jackknife_replicates.csv','pir_response_weighting.csv','pir_response_replicates.csv','pir_response_diagnostics.csv','pir_response_summary.csv')))
write.csv(data.frame(path=receipt_paths,md5=unname(tools::md5sum(file.path(root,receipt_paths)))),file.path(out,'r_reviewer_receipt.csv'),row.names=FALSE)
cat('Post-review R JKn and missing-PIR response weighting completed; 30 replicates each\n')
