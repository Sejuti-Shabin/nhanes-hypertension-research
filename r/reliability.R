# Numeric NCHS proportion screen, not agency clearance or a regression criterion.
kg_interval <- function(p,se,n,df) {
 stopifnot(n>=2,df>0,p>=0,p<=1,se>=0)
 neff<-if(p==0||p==1||se==0)n else min(n,p*(1-p)/se^2)
 adjusted<-neff*(qt(.025,n-1)/qt(.025,df))^2
 ci<-if(p==0)c(0,qbeta(.975,1,adjusted)) else if(p==1)c(qbeta(.025,adjusted,1),1) else
    c(qbeta(.025,adjusted*p,adjusted*(1-p)+1),qbeta(.975,adjusted*p+1,adjusted*(1-p)))
 list(ci=ci,effective_n=neff,adjusted_effective_n=adjusted)
}
nchs_screen <- function(p,n,neff,ci,df) {
 width<-diff(ci)
 if(!is.finite(neff)||!all(is.finite(ci)))return('review: undefined precision')
 if(n<30||neff<30)return('suppress: n or effective n <30')
 if(width>=.30)return('suppress: CI width')
 if(p==0||p==1)return('review: boundary proportion')
 if(width>.05&&width/p>1.30)return('suppress: CI width')
 if(df<8)return('review: fewer than 8 df')
 'meets numeric screening'
}
