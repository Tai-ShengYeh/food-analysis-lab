/* Offline PCA: cyclic Jacobi diagonalisation of the symmetric sample Gram.
 * Only numeric features enter fit. Autoscale uses sample SD (ddof=1), matching the W12 lesson.
 * Eigenvalues use n-1; null components are omitted. No canned PCA arrays.
 */
(function(root){
'use strict';
const dot=(a,b)=>a.reduce((s,x,i)=>s+x*b[i],0);
function eigenSymmetric(input){
 const a=input.map(r=>r.slice()),n=a.length,v=Array.from({length:n},(_,i)=>Array.from({length:n},(_,j)=>+(i===j)));
 const scale=Math.max(...a.map((r,i)=>Math.abs(r[i])),1);
 let converged=false;
 for(let sweep=0;sweep<100;sweep++){
  let off=0;
  for(let p=0;p<n;p++)for(let q=p+1;q<n;q++){
   const apq=a[p][q];off=Math.max(off,Math.abs(apq));if(Math.abs(apq)<scale*1e-14)continue;
   const tau=(a[q][q]-a[p][p])/(2*apq),t=(tau>=0?1:-1)/(Math.abs(tau)+Math.sqrt(1+tau*tau)),c=1/Math.sqrt(1+t*t),s=t*c;
   a[p][p]-=t*apq;a[q][q]+=t*apq;a[p][q]=a[q][p]=0;
   for(let k=0;k<n;k++){
    if(k!==p&&k!==q){const x=a[k][p],y=a[k][q];a[k][p]=a[p][k]=c*x-s*y;a[k][q]=a[q][k]=s*x+c*y;}
    const x=v[k][p],y=v[k][q];v[k][p]=c*x-s*y;v[k][q]=s*x+c*y;
   }
  }
  if(off<scale*1e-12){converged=true;break;}
 }
 if(!converged)throw Error('Jacobi eigensolver did not converge');
 return a.map((r,i)=>({value:r[i],vector:v.map(row=>row[i])})).sort((a,b)=>b.value-a.value);
}
function fit(X,mode='center',axis=[]){
 if(X.length<2||!X[0].length||X.some(r=>r.length!==X[0].length||r.some(x=>!Number.isFinite(x))))throw Error('Finite rectangular numeric matrix required');
 const n=X.length,p=X[0].length,mean=Array.from({length:p},(_,j)=>X.reduce((s,r)=>s+r[j],0)/n);
 const sd=mean.map((m,j)=>Math.sqrt(X.reduce((s,r)=>s+(r[j]-m)**2,0)/(n-1)));
 const scale=sd.map(s=>mode==='autoscale'&&s>1e-14?s:1);
 const Z=X.map(r=>r.map((x,j)=>(x-mean[j])/scale[j]));
 const gram=Z.map(a=>Z.map(b=>dot(a,b))),eig=eigenSymmetric(gram),cut=Math.max(eig[0].value*1e-11,1e-14);
 const eigenvalues=[],loadings=[];
 eig.filter(e=>e.value>cut).forEach((e,k)=>{
  const loading=mean.map((_,j)=>Z.reduce((s,r,i)=>s+r[j]*e.vector[i],0)/Math.sqrt(e.value));
  let anchor=loading.reduce((best,x,j)=>Math.abs(x)>Math.abs(loading[best])?j:best,0);
  if(axis.length&&k<2){const target=k===0?1655:1520;anchor=axis.reduce((best,x,j)=>Math.abs(x-target)<Math.abs(axis[best]-target)?j:best,0);}
  if(loading[anchor]<0)for(let j=0;j<p;j++)loading[j]*=-1;
  loadings.push(loading);eigenvalues.push(e.value/(n-1));
 });
 const scores=Z.map(r=>loadings.map(l=>dot(r,l))),total=eigenvalues.reduce((s,x)=>s+x,0);
 return {n,p,mode,mean,scale,Z,eigenvalues,loadings,scores,explained:eigenvalues.map(x=>x/total),rank:eigenvalues.length};
}
function project(model,X){return X.map(r=>model.loadings.map(l=>dot(r.map((x,j)=>(x-model.mean[j])/model.scale[j]),l)));}
function reconstruct(model,k,scores=model.scores){return scores.map(t=>model.mean.map((m,j)=>m+model.scale[j]*model.loadings.slice(0,k).reduce((s,l,a)=>s+t[a]*l[j],0)));}
function error(X,Y){return Math.sqrt(X.reduce((s,r,i)=>s+r.reduce((s,x,j)=>s+(x-Y[i][j])**2,0),0)/(X.length*X[0].length));}
const api={dot,eigenSymmetric,fit,project,reconstruct,error};root.PCAMath=api;if(typeof module!=='undefined')module.exports=api;
})(typeof window!=='undefined'?window:globalThis);
