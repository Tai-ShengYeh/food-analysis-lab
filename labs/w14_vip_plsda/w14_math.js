/* NIPALS PLS2, regression deflation, scale=False. No fitted arrays. */
(function(root){'use strict';
const dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0),sum=a=>a.reduce((s,v)=>s+v,0),mean=a=>sum(a)/a.length;
const rows=(X,idx)=>idx.map(i=>X[i]),cols=(X,mask)=>X.map(r=>mask.map(j=>r[j]));
function solve(A,b){A=A.map((r,i)=>[...r,b[i]]);const n=b.length;for(let k=0;k<n;k++){let p=k;for(let i=k+1;i<n;i++)if(Math.abs(A[i][k])>Math.abs(A[p][k]))p=i;[A[k],A[p]]=[A[p],A[k]];let v=A[k][k];if(Math.abs(v)<1e-14)throw Error('Singular latent system');for(let j=k;j<=n;j++)A[k][j]/=v;for(let i=0;i<n;i++)if(i!==k){v=A[i][k];for(let j=k;j<=n;j++)A[i][j]-=v*A[k][j];}}return A.map(r=>r[n]);}
function fit(X,Y,lv){const n=X.length,p=X[0].length,q=Y[0].length;if(lv<1||lv>Math.min(n-1,p))throw Error('LV exceeds training rank bound');const xm=X[0].map((_,j)=>mean(X.map(r=>r[j]))),ym=Y[0].map((_,j)=>mean(Y.map(r=>r[j])));let E=X.map(r=>r.map((v,j)=>v-xm[j])),F=Y.map(r=>r.map((v,j)=>v-ym[j])),W=[],P=[],Q=[],T=[];
for(let a=0;a<lv;a++){
 for(let j=0;j<q;j++)if(F.every(r=>Math.abs(r[j])<10*Number.EPSILON))F.forEach(r=>r[j]=0);
 let j0=F[0].findIndex((_,j)=>F.some(r=>Math.abs(r[j])>Number.EPSILON));if(j0<0)break;
 let u=F.map(r=>r[j0]),old=Array(p).fill(100),w,t,c;
 for(let it=0;it<500;it++){let uu=dot(u,u);w=xm.map((_,j)=>sum(E.map((r,i)=>r[j]*u[i]))/uu);let norm=Math.sqrt(dot(w,w))+Number.EPSILON;w=w.map(v=>v/norm);t=E.map(r=>dot(r,w));let tt=dot(t,t);c=ym.map((_,j)=>sum(F.map((r,i)=>r[j]*t[i]))/tt);u=F.map(r=>dot(r,c)/(dot(c,c)+Number.EPSILON));if(dot(w.map((v,j)=>v-old[j]),w.map((v,j)=>v-old[j]))<1e-6||q===1)break;old=w.slice();}
 let anchor=w.reduce((b,v,j)=>Math.abs(v)>Math.abs(w[b])?j:b,0);if(w[anchor]<0){w=w.map(v=>-v);t=t.map(v=>-v);c=c.map(v=>-v);}
 let tt=dot(t,t);if(tt<1e-28)break;let load=xm.map((_,j)=>sum(E.map((r,i)=>r[j]*t[i]))/tt);W.push(w);P.push(load);Q.push(c);T.push(t);E=E.map((r,i)=>r.map((v,j)=>v-t[i]*load[j]));F=F.map((r,i)=>r.map((v,j)=>v-t[i]*c[j]));
}
if(!W.length)throw Error('No nonzero response covariance');let A=P.map(p=>W.map(w=>dot(p,w))),C=ym.map((_,j)=>solve(A,Q.map(r=>r[j]))),coef=xm.map((_,j)=>ym.map((_,b)=>sum(W.map((w,a)=>w[j]*C[b][a]))));return {xm,ym,W,P,Q,T,coef,lv:W.length};}
function predict(m,X){return X.map(r=>m.ym.map((v,b)=>v+sum(r.map((x,j)=>(x-m.xm[j])*m.coef[j][b]))));}
function vip(m,bug=false){let p=m.W[0].length,s=m.T.map((t,a)=>dot(t,t)*dot(m.Q[a],m.Q[a])),total=sum(s);return Array.from({length:p},(_,j)=>Math.sqrt(p*sum(s.map((v,a)=>v*(bug?1:m.W[a][j]**2/dot(m.W[a],m.W[a]))))/total));}
function rmse(Y,P){return Math.sqrt(mean(Y.flatMap((r,i)=>r.map((v,j)=>(v-P[i][j])**2))));}
function cv(X,Y,folds,lv,selector=null){let pred=Array(Y.length),details=[];for(let f of folds){let A=rows(X,f.train),B=rows(X,f.valid),y=rows(Y,f.train),mask=selector?selector(A,y):X[0].map((_,j)=>j);if(mask.length<lv)return {rmse:null,pred:[],details,invalid:'Too few selected variables'};let model=fit(cols(A,mask),y,lv),v=predict(model,cols(B,mask));f.valid.forEach((idx,i)=>pred[idx]=v[i]);details.push({train:f.train,valid:f.valid,mask});}return {rmse:rmse(Y,pred),pred,details};}
function curve(X,Y,folds,lo=1,hi=8){return Array.from({length:Math.max(0,Math.min(hi,X[0].length)-lo+1)},(_,i)=>({lv:i+lo,rmse:cv(X,Y,folds,i+lo).rmse}));}
const best=c=>c.filter(r=>r.rmse!==null).reduce((a,b)=>a.rmse<b.rmse?a:b);
function regression(D,threshold=1,fullLV=4,selectedLV=3){let X=rows(D.X,D.train),Y=rows(D.Y,D.train),full=fit(X,Y,fullLV),v=vip(full),mask=v.flatMap((v,j)=>v>threshold?[j]:[]),fullCurve=curve(X,Y,D.folds),selectedCurve=mask.length?curve(cols(X,mask),Y,D.folds):[];let selected=mask.length>=selectedLV?fit(cols(X,mask),Y,selectedLV):null;
let fixed=selected?cv(cols(X,mask),Y,D.folds,selectedLV):null;
let nested=cv(X,Y,D.folds,selectedLV,(A,B)=>vip(fit(A,B,Math.min(fullLV,A[0].length))).flatMap((v,j)=>v>threshold?[j]:[]));
return {full,vip:v,mask,selected,fullCurve,selectedCurve,fixed,nested,threshold,fullLV,selectedLV};}
function classification(D,lv){let X=rows(D.X,D.train),Y=rows(D.Y,D.train),model=fit(X,Y,lv),cvCurve=curve(X,Y,D.folds,2,8);return {model,cvCurve};}
const argmax=r=>r.reduce((b,v,j)=>v>r[b]?j:b,0);
function confusion(Y,P){let n=Y[0].length,cm=Array.from({length:n},()=>Array(n).fill(0));Y.forEach((r,i)=>cm[argmax(r)][argmax(P[i])]++);let total=Y.length,correct=sum(cm.map((r,i)=>r[i]));return {cm,accuracy:correct/total,perClass:cm.map((r,i)=>{let TP=r[i],FN=sum(r)-TP,FP=sum(cm.map(r=>r[i]))-TP,TN=total-TP-FN-FP;return {TP,FN,FP,TN,sensitivity:TP+FN?TP/(TP+FN):null,specificity:TN+FP?TN/(TN+FP):null,accuracy:(TP+TN)/total};})};}
// Regularised incomplete beta, continued fraction; numerical F(.95) inversion.
function logGamma(z){const p=[676.5203681218851,-1259.1392167224028,771.3234287776531,-176.6150291621406,12.507343278686905,-.13857109526572012,9.984369578019572e-6,1.5056327351493116e-7];if(z<.5)return Math.log(Math.PI)-Math.log(Math.sin(Math.PI*z))-logGamma(1-z);z--;let x=.9999999999998099;p.forEach((v,i)=>x+=v/(z+i+1));let t=z+7.5;return .5*Math.log(2*Math.PI)+(z+.5)*Math.log(t)-t+Math.log(x);}
function betaCF(a,b,x){let qab=a+b,qap=a+1,qam=a-1,c=1,d=1-qab*x/qap;if(Math.abs(d)<1e-30)d=1e-30;d=1/d;let h=d;for(let m=1;m<=200;m++){let m2=2*m,aa=m*(b-m)*x/((qam+m2)*(a+m2));d=1+aa*d;if(Math.abs(d)<1e-30)d=1e-30;c=1+aa/c;if(Math.abs(c)<1e-30)c=1e-30;d=1/d;h*=d*c;aa=-(a+m)*(qab+m)*x/((a+m2)*(qap+m2));d=1+aa*d;if(Math.abs(d)<1e-30)d=1e-30;c=1+aa/c;if(Math.abs(c)<1e-30)c=1e-30;d=1/d;let delta=d*c;h*=delta;if(Math.abs(delta-1)<3e-14)break;}return h;}
function ibeta(x,a,b){if(x<=0)return 0;if(x>=1)return 1;let bt=Math.exp(logGamma(a+b)-logGamma(a)-logGamma(b)+a*Math.log(x)+b*Math.log1p(-x));return x<(a+1)/(a+b+2)?bt*betaCF(a,b,x)/a:1-bt*betaCF(b,a,1-x)/b;}
function f95(d1,d2){let lo=0,hi=1;while(ibeta(d1*hi/(d1*hi+d2),d1/2,d2/2)<.95)hi*=2;for(let i=0;i<80;i++){let m=(lo+hi)/2;if(ibeta(d1*m/(d1*m+d2),d1/2,d2/2)<.95)lo=m;else hi=m;}return (lo+hi)/2;}
function limits(model,k){let n=model.n,tail=model.eigenvalues.slice(k),t1=sum(tail),t2=sum(tail.map(v=>v*v)),t3=sum(tail.map(v=>v**3)),h=1-2*t1*t3/(3*t2*t2),z=1.6448536269514722,base=z*Math.sqrt(2*t2*h*h)/t1+1+t2*h*(h-1)/(t1*t1),Q=t1*Math.pow(base,1/h),T2=k*(n-1)/(n-k)*f95(k,n-k);return {T2,newT2:T2*(n+1)/n,Q,theta:[t1,t2,t3],h};}
function diagnose(model,x,k,inject=false){let z=x.map((v,j)=>v-model.mean[j]);if(inject){let d=x.map((_,j)=>Math.sin(j*1.37));model.loadings.slice(0,k).forEach(l=>{let t=dot(d,l);d=d.map((v,j)=>v-t*l[j]);});let norm=Math.sqrt(dot(d,d));z=z.map((v,j)=>v+.2*d[j]/norm);}
let scores=model.loadings.slice(0,k).map(l=>dot(z,l)),projected=z.map((_,j)=>sum(scores.map((t,a)=>t*model.loadings[a][j]))),residual=z.map((v,j)=>v-projected[j]);return {scores,T2:sum(scores.map((t,a)=>t*t/model.eigenvalues[a])),Q:dot(residual,residual),original:z.map((v,j)=>v+model.mean[j]),reconstruction:projected.map((v,j)=>v+model.mean[j]),residual,inject};}
const api={dot,sum,mean,rows,cols,solve,fit,predict,vip,rmse,cv,curve,best,regression,classification,argmax,confusion,f95,limits,diagnose};root.W14Math=api;if(typeof module!=='undefined')module.exports=api;
})(typeof window!=='undefined'?window:globalThis);
