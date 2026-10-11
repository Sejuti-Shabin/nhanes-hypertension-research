# Reference implementation: survey 4.5. Define full design BEFORE domains.
suppressPackageStartupMessages(library(survey))
suppressPackageStartupMessages(library(foreign))
options(survey.lonely.psu='fail', survey.adjust.domain.lonely=FALSE)
args <- commandArgs(trailingOnly=TRUE)
root <- if(length(args)) normalizePath(args[1]) else normalizePath('.')
out <- file.path(root,'outputs')
source(file.path(root,'r/reliability.R'))
d <- read.csv(file.path(out,'design_frame.csv'),check.names=FALSE,na.strings=c('','NA'))
stopifnot(!anyDuplicated(d$SEQN),all(d$WTMEC2YR>0))

# Independent raw-XPORT reconstruction of core variables (not just CSV inference).
files <- c('DEMO_J','BPX_J','BPQ_J','HIQ_J','HUQ_J')
raw <- lapply(files,function(f) {
 x<-read.xport(file.path(root,'data/raw',paste0(f,'.xpt')))
 stopifnot(!anyDuplicated(x$SEQN));x
})
r <- raw[[1]]
for(i in 2:5)r<-merge(r,raw[[i]],by='SEQN',all.x=TRUE,sort=FALSE)
r<-r[match(d$SEQN,r$SEQN),]
stopifnot(all(r$SEQN==d$SEQN))
for(v in names(r)) if(is.numeric(r[[v]]))r[[v]][!is.na(r[[v]])&abs(r[[v]])<1e-50]<-0
r$sbp<-rowMeans(r[,paste0('BPXSY',1:3)],na.rm=TRUE)
r$dbp<-rowMeans(r[,paste0('BPXDI',1:3)],na.rm=TRUE)
r$sbp[is.nan(r$sbp)]<-NA;r$dbp[is.nan(r$dbp)]<-NA
r$awareness<-ifelse(r$BPQ020==1,1,ifelse(r$BPQ020==2,0,NA))
r$uninsured<-ifelse(r$HIQ011==2,1,ifelse(r$HIQ011==1,0,NA))
r$medication<-ifelse(r$BPQ050A==1,1,ifelse(r$BPQ050A==2,0,NA))
structural<-is.na(r$BPQ050A)&(!is.na(r$BPQ020)&r$BPQ020==2 | (!is.na(r$BPQ020)&r$BPQ020==1&!is.na(r$BPQ040A)&r$BPQ040A==2))
r$medication[structural]<-0
r$elevated_130<-ifelse(!is.na(r$sbp)&!is.na(r$dbp),0,NA)
r$elevated_130[which(r$sbp>=130|r$dbp>=80)]<-1
r$hypertension_130<-rep(NA_real_,nrow(r))
r$hypertension_130[which(r$elevated_130==1|r$medication==1)]<-1
r$hypertension_130[which(r$elevated_130==0&r$medication==0)]<-0
r$age10<-(r$RIDAGEYR-40)/10
r$sex<-c('Male','Female')[match(r$RIAGENDR,c(1,2))]
r$race<-c('Mexican American','Other Hispanic','White','Black','Asian','Other/multiracial')[match(r$RIDRETH3,c(1,2,3,4,6,7))]
r$education<-c('Below high school','Below high school','High school/GED','Some college/AA','College graduate')[match(r$DMDEDUC2,1:5)]
r$pir<-ifelse(r$INDFMPIR>=0&r$INDFMPIR<=5,r$INDFMPIR,NA)
r$no_usual_care<-c(0,1,0)[match(r$HUQ030,1:3)]
checkvars<-c('sbp','dbp','awareness','uninsured','medication','elevated_130','hypertension_130','WTMEC2YR','age10','sex','race','education','pir','no_usual_care','SDMVSTRA','SDMVPSU')
checks<-data.frame(variable=checkvars,passed=sapply(checkvars,function(v)isTRUE(all.equal(r[[v]],d[[v]],tolerance=1e-10))))
write.csv(checks,file.path(out,'r_raw_coding_validation.csv'),row.names=FALSE)
stopifnot(all(checks$passed))
primary<-r$RIDAGEYR>=20&r$RIDAGEYR<=64&!is.na(r$hypertension_130)&r$hypertension_130==1
primary[is.na(primary)]<-FALSE
stopifnot(all(as.integer(primary)==d$domain_primary))

levels_list<-list(sex=c('Female','Male'),race=c('White','Black','Mexican American','Other Hispanic','Asian','Other/multiracial'),
 education=c('College graduate','Some college/AA','High school/GED','Below high school'),pir_group=c('PIR >2','PIR >1–2','PIR ≤1'))
for(v in names(levels_list))d[[v]]<-factor(d[[v]],levels=levels_list[[v]])
full<-svydesign(ids=~SDMVPSU,strata=~SDMVSTRA,weights=~WTMEC2YR,data=d,nest=TRUE)
design_df<-degf(full)
stopifnot(design_df==15)

# Ratios use bounded beta/Korn-Graubard-type intervals for proportions.
estimate <- function(variable,mask,binary=FALSE) {
 mask <- mask & !is.na(d[[variable]]); mask[is.na(mask)]<-FALSE
 dd<-subset(full,mask)
 if(!sum(mask))stop('Empty descriptive domain')
 f<-as.formula(paste0('~',variable))
 m<-svymean(f,dd,na.rm=TRUE)
 p<-as.numeric(coef(m));se<-as.numeric(SE(m));n<-sum(mask);ddf<-degf(dd)
 ci<-as.numeric(confint(m,df=ddf))
 neff<-NA_real_;flag<-'not a proportion';compflag<-''
 if(binary) {
  kg<-kg_interval(p,se,n,ddf);ci<-kg$ci;neff<-kg$effective_n
  # Independently compare survey beta endpoints when no NCHS cap is needed.
  if(p>0&&p<1&&p*(1-p)/se^2<=n) {
   reference<-as.numeric(confint(svyciprop(f,dd,method='beta',na.rm=TRUE)))
   stopifnot(isTRUE(all.equal(reference,ci,tolerance=1e-10)))
  }
  flag<-nchs_screen(p,n,neff,ci,ddf)
  compflag<-nchs_screen(1-p,n,neff,1-rev(ci),ddf)
 }
 data.frame(n=n,estimate=p,se=se,ci_low=ci[1],ci_high=ci[2],design_df=ddf,
  effective_n=neff,absolute_ci_width=diff(ci),relative_ci_width=if(binary)diff(ci)/p else NA,
  reliability=flag,complement_reliability=compflag,ci_method=if(binary)'beta/Korn-Graubard-type' else 'Taylor t')
}

target<-d$RIDAGEYR>=20&d$RIDAGEYR<=64
rows<-list(cbind(estimand='Hypertension prevalence',group='All',variable='hypertension_130',estimate('hypertension_130',target,TRUE)))
for(g in c('All','Insured','Uninsured')) {
 mask<-d$domain_primary==1
 if(g!='All')mask<-mask & d$uninsured==as.numeric(g=='Uninsured')
 rows[[length(rows)+1]]<-cbind(estimand='Awareness prevalence',group=g,variable='awareness',estimate('awareness',mask,TRUE))
}
write.csv(do.call(rbind,rows),file.path(out,'descriptive.csv'),row.names=FALSE)
# Independent grouped interface, not used to delete design records before domains.
byinsurance<-svyby(~awareness,~uninsured,subset(full,domain_analytic==1),svymean,na.rm=TRUE,vartype=c('se','ci'))
write.csv(byinsurance,file.path(out,'r_svyby_awareness.csv'),row.names=FALSE)

# Table 1, outcome/exposure-complete hypertensive domain; each variable own denominator.
table1<-list()
for(g in c('Insured','Uninsured')) {
 mask<-d$domain_analytic==1 & d$uninsured==as.numeric(g=='Uninsured')
 for(v in c('RIDAGEYR','pir','sbp','dbp','awareness')) {
  table1[[length(table1)+1]]<-cbind(insurance=g,variable=v,level=if(v=='awareness')'Aware' else 'Mean',
     total_group_n=sum(mask),category_n=NA,estimate(v,mask,v=='awareness'))
 }
 for(v in names(levels_list))for(level in levels_list[[v]]) {
  full$variables$tmp<-ifelse(is.na(d[[v]]),NA,as.numeric(d[[v]]==level))
  d$tmp<-full$variables$tmp
  table1[[length(table1)+1]]<-cbind(insurance=g,variable=v,level=level,total_group_n=sum(mask),
     category_n=sum(mask & !is.na(d[[v]]) & d[[v]]==level),estimate('tmp',mask,TRUE))
 }
}
write.csv(do.call(rbind,table1),file.path(out,'table1.csv'),row.names=FALSE)

specs<-read.csv(file.path(out,'model_specifications.csv'),stringsAsFactors=FALSE)
reg<-list();diagnostics<-list();fits<-list();covariances<-list();domainchecks<-list()
# Every model mask is rebuilt from raw component variables, not trusted from CSV.
r$pir_group<-as.character(cut(r$pir,c(-.001,1,2,5),labels=c('PIR ≤1','PIR >1–2','PIR >2')))
r$age10_sq<-r$age10^2
rebuild_case<-function(rr,threshold=130,readings=1:3) {
 sy<-rowMeans(rr[,paste0('BPXSY',readings)],na.rm=TRUE);di<-rowMeans(rr[,paste0('BPXDI',readings)],na.rm=TRUE)
 sy[is.nan(sy)]<-NA;di[is.nan(di)]<-NA
 measured<-ifelse(!is.na(sy)&!is.na(di),0,NA)
 measured[which(sy>=threshold|di>=if(threshold==130)80 else 90)]<-1
 ht<-rep(NA_real_,nrow(rr));ht[which(measured==1|rr$medication==1)]<-1;ht[which(measured==0&rr$medication==0)]<-0
 list(sbp=sy,dbp=di,measured=measured,hypertension=ht,ns=rowSums(!is.na(rr[,paste0('BPXSY',readings)])),nd=rowSums(!is.na(rr[,paste0('BPXDI',readings)])))
}
rebuild_mask<-function(spec) {
 name<-spec$model;age<-c(20,64);threshold<-if(name %in% c('threshold140','measured140'))140 else 130
 readings<-if(name=='readings23')2:3 else if(name=='readings1234')1:4 else 1:3
 phen<-rebuild_case(r,threshold,readings)
 if(name=='age20_59')age<-c(20,59)
 if(name=='age30_64')age<-c(30,64)
 case<-if(name %in% c('measured130','measured140'))phen$measured else phen$hypertension
 mask<-r$RIDAGEYR>=age[1]&r$RIDAGEYR<=age[2]&case==1
 if(name %in% c('bp_complete','two_readings','measured130','measured140'))mask<-mask&!is.na(phen$sbp)&!is.na(phen$dbp)
 if(name=='two_readings')mask<-mask&phen$ns>=2&phen$nd>=2
 if(name=='exclude_pregnant')mask<-mask&!(r$RIDEXPRG %in% 1)
 if(name=='insured_no_lapse')mask<-mask&(r$uninsured==1|(r$uninsured==0&r$HIQ210==2))
 vars<-all.vars(as.formula(spec$formula))
 if(name %in% c('M1_common','M2_common'))vars<-unique(c(vars,'uninsured','age10','sex','race','education','pir'))
 mask<-mask&complete.cases(r[,vars,drop=FALSE]);mask[is.na(mask)]<-FALSE
 mask
}
for(i in seq_len(nrow(specs))) {
 spec<-specs[i,];mask<-rebuild_mask(spec)
 domainchecks[[i]]<-data.frame(model=spec$model,n=sum(mask),matched_python=all(mask==(d[[spec$domain_column]]==1)))
 stopifnot(all(mask==(d[[spec$domain_column]]==1)))
 dd<-subset(full,mask)
 mod<-svyglm(as.formula(spec$formula),design=dd,family=quasibinomial(),control=glm.control(epsilon=1e-14,maxit=200))
 fits[[spec$model]]<-mod
 sm<-summary(mod);ct<-sm$coefficients
 rdf<-mod$df.residual;crit<-qt(.975,rdf)
 b<-coef(mod);se<-sqrt(diag(vcov(mod)))
 cv<-vcov(mod);cvrows<-expand.grid(term1=rownames(cv),term2=colnames(cv),stringsAsFactors=FALSE)
 cvrows$model<-spec$model;cvrows$covariance<-as.vector(cv);covariances[[i]]<-cvrows
 reg[[i]]<-data.frame(model=spec$model,term=names(b),beta=b,se=se,odds_ratio=exp(b),
 ci_low=exp(b-crit*se),ci_high=exp(b+crit*se),t=ct[,3],p=ct[,4],n=sum(mask),events=sum(d$awareness[mask]),
 design_df=degf(dd),residual_df=rdf,kind=spec$kind,row.names=NULL)
 diagnostics[[i]]<-data.frame(model=spec$model,n=sum(mask),rank=mod$rank,converged=mod$converged,
     design_df=degf(dd),residual_df=rdf,min_prediction=min(fitted(mod)),max_prediction=max(fitted(mod)))
}
reg<-do.call(rbind,reg)
write.csv(reg,file.path(out,'regression.csv'),row.names=FALSE)
write.csv(do.call(rbind,covariances),file.path(out,'r_covariance.csv'),row.names=FALSE)
write.csv(do.call(rbind,domainchecks),file.path(out,'r_domain_validation.csv'),row.names=FALSE)
# Reference-distribution sensitivity: identical coefficients/covariance, alternative df.
calibration<-list()
for(reference in c('residual','full_design')) {
 z<-subset(reg,term=='uninsured');z$reference<-reference
 z$inference_df<-if(reference=='residual')z$residual_df else z$design_df
 q<-qt(.975,z$inference_df);z$ci_low<-exp(z$beta-q*z$se);z$ci_high<-exp(z$beta+q*z$se)
 z$p<-2*pt(abs(z$beta/z$se),df=z$inference_df,lower.tail=FALSE)
 calibration[[reference]]<-z
}
write.csv(do.call(rbind,calibration),file.path(out,'inference_calibrations.csv'),row.names=FALSE)
write.csv(do.call(rbind,diagnostics),file.path(out,'r_diagnostics.csv'),row.names=FALSE)
write.csv(subset(reg,term %in% c('uninsured','no_usual_care')),file.path(out,'sensitivity.csv'),row.names=FALSE)

# Joint linearization of model fit AND weighted standardization population.
mod<-fits[['M3']];keep<-d$domain_m3==1;sub<-d[keep,]
x<-model.matrix(mod);y<-sub$awareness;w<-sub$WTMEC2YR
p<-as.numeric(fitted(mod));bread<-crossprod(x,x*as.numeric(w*p*(1-p)))
scores<-x*as.numeric(w*(y-p));beta_influence<-scores %*% solve(bread)
fullbeta<-matrix(0,nrow(d),ncol(x));fullbeta[keep,]<-beta_influence
mus<-numeric(2);infl<-list()
for(k in 1:2) {
 new<-sub;new$uninsured<-k-1
 xn<-model.matrix(delete.response(terms(mod)),new,contrasts.arg=mod$contrasts)
 pn<-plogis(xn %*% coef(mod));mu<-sum(w*pn)/sum(w)
 grad<-colSums(xn*as.numeric(w*pn*(1-pn)))/sum(w)
 inf<-as.numeric(fullbeta %*% grad);inf[keep]<-inf[keep]+w*(pn-mu)/sum(w)
 mus[k]<-mu;infl[[k]]<-inf
}
infl[[3]]<-infl[[2]]-infl[[1]];mus[3]<-mus[2]-mus[1]
marginal<-list()
for(k in 1:3) {
 # svytotal(w^-1*influence) gives full-design Taylor variance independently.
 dd<-full;dd$variables$lin<-infl[[k]]/d$WTMEC2YR
 se<-as.numeric(SE(svytotal(~lin,dd)));reference_df<-mod$df.residual;q<-qt(.975,reference_df)
 lo<-mus[k]-q*se;hi<-mus[k]+q*se;ci_method<-'Taylor t difference'
 if(k<=2){lo<-plogis(qlogis(mus[k])-q*se/(mus[k]*(1-mus[k])));hi<-plogis(qlogis(mus[k])+q*se/(mus[k]*(1-mus[k])));ci_method<-'logit-transformed Taylor t'}
 marginal[[k]]<-data.frame(estimand=c('Insured','Uninsured','Uninsured minus insured')[k],estimate=mus[k],se=se,
  ci_low=lo,ci_high=hi,design_df=design_df,inference_df=reference_df,ci_method=ci_method,n=sum(keep))
}
write.csv(do.call(rbind,marginal),file.path(out,'marginal_probabilities.csv'),row.names=FALSE)
saveRDS(fits,file.path(out,'r_model_objects.rds'))
capture.output(sessionInfo(),file=file.path(out,'R_sessionInfo.txt'))
receipt_paths<-c('r/survey_analysis.R','r/reliability.R','outputs/design_frame.csv','outputs/model_specifications.csv',paste0('data/raw/',files,'.xpt'),paste0('outputs/',c('regression.csv','descriptive.csv','table1.csv','marginal_probabilities.csv','r_covariance.csv','r_domain_validation.csv','r_raw_coding_validation.csv','inference_calibrations.csv')))
write.csv(data.frame(path=receipt_paths,md5=unname(tools::md5sum(file.path(root,receipt_paths)))),file.path(out,'r_reference_receipt.csv'),row.names=FALSE)
cat('R survey completed:',nrow(reg),'coefficient rows; full design df',design_df,'\n')
