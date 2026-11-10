#!/usr/bin/env python3
"""W14 narrated tours with independent sklearn/SciPy references for all 3 CSVs."""
from pathlib import Path
import csv,json,hashlib
import numpy as np
from scipy import stats
from sklearn.cross_decomposition import PLSRegression
from sklearn.decomposition import PCA
from sklearn.model_selection import train_test_split,KFold
from sklearn.metrics import confusion_matrix
from PIL import Image,ImageDraw,ImageFont
from course_video_common import render,cache_dir
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'labs/w14_vip_plsda/animations';OUT.mkdir(exist_ok=True,parents=True)
def load(name):
 path=ROOT/f'data/nb12_demo_spectra_{name}.csv';meta=list(csv.DictReader(path.open()));keys=list(meta[0])[5:];return meta,np.array([[float(r[k]) for k in keys] for r in meta]),np.array(list(map(float,keys))),hashlib.sha256(path.read_bytes()).hexdigest()
def vip(m):
 T=m.x_scores_;W=m.x_weights_;q=m.y_loadings_[0];ssy=q*q*(T*T).sum(0);return np.sqrt(W.shape[0]*((W/np.linalg.norm(W,axis=0))**2@ssy)/ssy.sum())
def cvcurve(X,Y,components,seed):
 out=[]
 for k in components:
  errs=[]
  for tr,va in KFold(5,shuffle=True,random_state=seed).split(X):
   m=PLSRegression(n_components=k,scale=False).fit(X[tr],Y[tr]);errs.extend(((m.predict(X[va])-Y[va].reshape(m.predict(X[va]).shape))**2).ravel())
  out.append(dict(lv=k,rmsecv=float(np.sqrt(np.mean(errs)))))
 return out
mv,Xv,wv,hv=load('vip');yv=np.array([float(r['acidity_pct']) for r in mv]);vi,vte=train_test_split(np.arange(len(yv)),test_size=.25,random_state=14);vc=cvcurve(Xv[vi],yv[vi],range(1,9),14);vk=min(vc,key=lambda r:r['rmsecv'])['lv'];vm=PLSRegression(n_components=vk,scale=False).fit(Xv[vi],yv[vi]);VIP=vip(vm);sel=VIP>1;sc=cvcurve(Xv[vi][:,sel],yv[vi],range(1,min(8,int(sel.sum()))+1),14);sk=min(sc,key=lambda r:r['rmsecv'])['lv'];sm=PLSRegression(n_components=sk,scale=False).fit(Xv[vi][:,sel],yv[vi]);vrm=float(np.sqrt(np.mean((vm.predict(Xv[vte]).ravel()-yv[vte])**2)));srm=float(np.sqrt(np.mean((sm.predict(Xv[vte][:,sel]).ravel()-yv[vte])**2)))
mo,Xo,wo,ho=load('oils');classes=sorted(set(r['oil'] for r in mo));yo=np.array([classes.index(r['oil']) for r in mo]);Y=np.eye(6)[yo];oi,ote=train_test_split(np.arange(len(yo)),test_size=.3,random_state=1,stratify=yo);oc=cvcurve(Xo[oi],Y[oi],range(2,9),1);ok=min(oc,key=lambda r:r['rmsecv'])['lv'];om=PLSRegression(n_components=ok,scale=False).fit(Xo[oi],Y[oi]);op=om.predict(Xo[ote]);cm=confusion_matrix(yo[ote],op.argmax(1),labels=range(6));acc=float(np.trace(cm)/cm.sum())
md,Xd,wd,hd=load('outlier');dc=np.array([r['role']=='calibration' for r in md]);pc=PCA(n_components=39).fit(Xd[dc]);n=int(dc.sum());k=2;ds=pc.transform(Xd)[:,:k];recon=ds@pc.components_[:k]+pc.mean_;T2=(ds*ds/pc.explained_variance_[:k]).sum(1);Q=((Xd-recon)**2).sum(1);tl=float(k*(n-1)/(n-k)*stats.f.ppf(.95,k,n-k));tn=tl*(n+1)/n;e=pc.explained_variance_[k:];t1=e.sum();t2=(e*e).sum();t3=(e**3).sum();h=1-2*t1*t3/(3*t2*t2);ql=float(t1*(stats.norm.ppf(.95)*np.sqrt(2*t2*h*h)/t1+1+t2*h*(h-1)/(t1*t1))**(1/h))
reference=dict(sources={'vip':hv,'oils':ho,'outlier':hd},vip=dict(train=vi.tolist(),test=vte.tolist(),curve=vc,lv=vk,VIP=VIP.tolist(),mean_vip_squared=float(np.mean(VIP**2)),selected_count=int(sel.sum()),selected_wavelengths=wv[sel].tolist(),selected_curve_fixed_training_mask=sc,selected_lv=sk,full_rmsep=vrm,selected_rmsep=srm),classification=dict(classes=classes,train=oi.tolist(),test=ote.tolist(),curve=oc,lv=ok,confusion=cm.tolist(),accuracy=acc,predicted_scores=op.tolist()),diagnostics=dict(k=k,n=n,t2_training_limit=tl,t2_new_limit=tn,q_limit=ql,T2=T2.tolist(),Q=Q.tolist(),roles=[r['role'] for r in md]))
(OUT/'numerical-reference.json').write_text(json.dumps(reference,indent=2))
scenes=[
['VIP 全部一樣，你還會相信排名嗎？','All VIP values match. Would you trust the ranking?', '模型說某個波長很重要，先別照抄排名。本週從一個多寫總和的 VIP 錯誤開始，學會驗證重要性、判讀分類，並用兩種離群診斷檢查模型是否認得新樣品。三組資料都來自 NB12 教學模擬。','Before trusting a wavelength ranking, verify the calculation. This week starts with an extra-sum VIP bug, then explores classification and two complementary outlier diagnostics. All three datasets are the original NB12 teaching simulations, not real inspection results.','bug','先驗算，再解釋；模擬資料不是檢驗證明','Check calculations before interpretation; simulated data only'],
['VIP：用 y 的解釋量加權波長貢獻','VIP weights wavelength contributions by explained y','每個潛在變數有一組波長權重，VIP 把權重平方，按照該方向解釋的 y 變異加權。正確公式會讓全部波長的 VIP 平方平均等於一；但只抽幾個波長來平均，就不一定是一。','Each latent variable has a vector of wavelength weights. VIP combines their squared contributions, weighted by explained response variation. Correct VIP has mean squared value one across all variables, but that identity need not hold for a small selected subset.','vip','mean(VIP²)=1 只適用全部變數，不適用任意子集','mean(VIP squared)=1 applies to all variables, not subsets'],
['不變量能抓錯，但不是正確保證','An invariant detects errors, not all possible bugs','本例有八十一個波長。若錯把每個波長的貢獻提早加成總和，所有 VIP 都變成九，平方平均變成八十一。反過來說，全部填成一也會通過平均檢查，所以還要比對波形、程式與合理性。','This example has eighty-one variables. Prematurely summing the wavelength contributions makes every buggy VIP equal nine, with mean square eighty-one. But filling every VIP with one would pass the mean-square check. Also inspect the curve, implementation, and scientific context.','bug','公式不變量是必要檢查，不是充分證明','An invariant is a necessary check, not sufficient proof'],
['VIP 說重要性，係數才有方向','VIP indicates importance; coefficients carry direction','VIP 是非負的重要性指標，不表示因果，也不告訴你濃度往哪裡變。迴歸係數才有正負方向，而且必須連同前處理與共線性解讀。VIP 大於一只是高於平均的常用經驗規則，不是顯著性檢定。','VIP is nonnegative importance, not causality or a direction of concentration change. Regression coefficients carry signs, interpreted in the context of preprocessing and collinearity. VIP above one is a common above-average heuristic, not a significance test.','direction','VIP >= 0；係數可正可負；高 VIP 不等於因果','VIP is nonnegative; coefficients are signed; neither proves causality'],
['先選波長再評分，小心選擇偏誤','Beware selecting variables before scoring the same folds','示範用六十個訓練樣品選出十八個 VIP 波長，另有二十個測試樣品。若先用全部訓練資料選波長，再在同批資料交叉驗證，驗證折已參與選擇。公平比較要在每折內重新選波長，或保留未碰過的外部測試。','The demo selects eighteen VIP variables from sixty training samples, with twenty samples held out. Selecting on all training data before cross-validation lets validation folds influence selection. Reselect within each fold, or evaluate once on untouched external samples.','selection','篩選也屬於建模；每折內重選才避免選擇洩漏','Variable selection is part of fitting; repeat it inside each fold'],
['測試變好，不代表篩選必然更好','A better test result is not a universal win','這批資料全波段測試誤差約零點一六六，篩選後約零點一三三，但固定遮罩的交叉驗證誤差反而增加。兩種指標不一致，加上測試只有二十個樣品，不能只挑好看的數字；更不能看過測試結果再調門檻。','For these data, test RMSE falls from about zero point one six six to zero point one three three after selection, while fixed-mask CV error rises. With only twenty test samples, do not cherry-pick the favorable metric or retune the threshold after seeing test results.','compare','RMSEP：0.166 > 0.133；仍需獨立確認與不確定度','RMSEP: 0.166 > 0.133; further independent validation is needed'],
['PLS-DA：one-hot 迴歸，再取最大值','PLS-DA: regress one-hot targets, then take argmax','六種油編碼成六欄零與一，PLS 同時對這六欄建模。新樣品得到六個預測分數，選最大的那類。這些分數不是機率，可能小於零或大於一，也不保證總和是一。','Encode six oil classes as six columns of zeros and ones. PLS jointly regresses those targets. For a new sample, choose the class with the largest predicted score. These scores are not calibrated probabilities: they can be negative or exceed one.','onehot','one-hot > PLS2 > 六個分數 > argmax；分數不是機率','One-hot > PLS2 > six scores > argmax; scores are not probabilities'],
['混淆矩陣：整體準，不代表每類都準','Overall accuracy can hide weak class sensitivity','NB12 由訓練資料選出六個 LV，獨立測試二十七個樣品，判對二十四個，約百分之八十八點九。精製橄欖油四個只抓到兩個，敏感度零點五；特異度雖是一，也不能說這一類都辨認得很好。','Training CV chooses six latent variables. The independent test classifies twenty-four of twenty-seven samples correctly, about eighty-eight point nine percent. Refined olive oil has only two true positives out of four: sensitivity one half. Perfect specificity does not repair those missed positives.','confusion','列是實際，欄是預測；敏感度與特異度一起看','Rows: actual; columns: predicted; inspect sensitivity and specificity'],
['T² 與 Q：平面內遠，還是平面外遠？','T squared and Q: far within or far outside the model?', 'T 平方用各主成分的變異當尺，描述樣品在模型平面內離中心多遠。Q 是光譜與重建光譜的殘差平方和，描述模型沒解釋的部分。兩個值來自同一個校正 PCA，但回答不同問題，不能只看其中一個。','T squared scales score distance by each retained component\'s variance. Q is the squared reconstruction residual, measuring variation outside the retained model. Both use the same calibration PCA, but answer different questions. Inspect them together.','influence','T²：模型內的距離；Q：重建不了的變異','T squared: score-space distance; Q: unexplained variation'],
['換儀器可能 T² 正常，Q 卻很高','A new instrument may have ordinary T squared but high Q','本例只用四十個校正樣品建立兩成分 PCA。槓桿樣品 T 平方約二十八點四，但 Q 未超標；換儀器的模擬樣品，T 平方看似普通，Q 卻約為界限三十三倍。分數圖看不出異常，不等於模型真的適用。','Fit a two-component PCA using only forty calibration samples. The leverage example has T squared about twenty-eight point four but Q below its limit. Simulated instrument-shift samples have ordinary T squared yet Q about thirty-three times its limit. An ordinary score plot does not establish applicability.','influence','不能把「分數圖正常」當成「模型適用」','Ordinary scores do not establish model applicability'],
['95% 界限是近似，不是合格保證','Approximate limits are not acceptance guarantees','T 平方與 Q 的界限依同一校正模型估計，不可拿別個模型的數字套用。兩成分例的校正內 T 平方界限約六點六六，新樣品近似約六點八三。分布假設、樣本數與多重比較都會影響誤報，超線應先調查，不要自動刪除。','Limits belong to the fitted calibration model, not every instrument or dataset. For this two-component example, the approximate training T-squared limit is six point six six, and the new-sample limit six point eight three. Assumptions and sample size matter. Investigate flagged points; do not delete automatically.','limits','T² 界限：校正內 6.66；新樣品 6.83（近似）','Approximate T-squared limits: training 6.66; new sample 6.83'],
['Orange 與 NB12：不同路徑要說清楚','Distinguish the Orange and NB12 modeling routes','Orange 入門用 PCA 加邏輯斯迴歸，不是本頁的 PLS-DA。若 PCA 先用全部資料 fit 再做分類交叉驗證，也會有洩漏；正式流程要把 PCA 放進每一折。Apply Domain 可看投影，但完整 Q 診斷要用 NB12 或本互動實驗。','The Orange route uses PCA plus logistic regression, not the PLS-DA model shown here. Fitting PCA on all data before classifier CV leaks information; fit PCA inside each fold instead. Apply Domain shows projections, while full Q diagnostics require NB12 or this interactive lab.','workflow','PCA + logistic 不等於 PLS-DA；降維也須折內 fit','PCA plus logistic is not PLS-DA; fit preprocessing inside folds'],
['六幕操作：把模型結論變成可查證證據','Six acts: make model conclusions auditable','進入六幕實驗，切換正確與錯誤 VIP、比較篩選流程，判讀分類分數與混淆矩陣，再操作 T 平方與 Q。下載證據與調查紀錄。正式作業換成本班實測資料，說明限制、保留離群原因，不把模擬成績當食品真偽認證。','Explore correct and buggy VIP, compare selection workflows, inspect classification scores and confusion matrices, then vary T squared and Q. Download evidence and investigation notes. Use class measurements for the assignment, retain reasons for flagged samples, and do not treat simulation results as food-authenticity certification.','workflow','交付：VIP 驗算、混淆矩陣、T²/Q、調查紀錄','Submit: VIP checks, confusion matrix, T-squared/Q, investigation notes']]
FONT=Path('/home/administrator/.local/share/fonts/hermes-food-tests/msjh.ttc')
if not FONT.exists():FONT=Path('/mnt/c/Windows/Fonts/msjh.ttc')
if not FONT.exists():FONT=Path('C:/Windows/Fonts/msjh.ttc')
F={n:ImageFont.truetype(str(FONT),n) for n in [18,20,22,24,26,28,30,34,40]};colors=['#246bc4','#df7d23','#129785']
def wrap(text,width,font):
 words=text.split(' ') if all(ord(c)<128 for c in text) else list(text);sep=' ' if all(ord(c)<128 for c in text) else '';lines=[];line=''
 for w in words:
  s=line+sep+w if line else w
  if line and font.getlength(s)>width:lines.append(line);line=w
  else:line=s
 if line:lines.append(line)
 return lines

def frame(s,lang,progress):
 im=Image.new('RGB',(1280,720),'#edf6ff');d=ImageDraw.Draw(im);d.rounded_rectangle((24,18,1256,702),radius=24,fill='white');d.text((52,32),'FOOD ANALYSIS LAB / W14 / VIP + PLS-DA + DIAGNOSTICS',font=F[22],fill='#246bb2')
 for j,line in enumerate(wrap(s[0 if lang=='zh' else 1],1170,F[40])):d.text((52,75+j*46),line,font=F[40],fill='#173653')
 typ=s[4]
 def cards(entries):
  for j,(a,b) in enumerate(entries):
   yy=180+j*105;d.rounded_rectangle((65,yy,1215,yy+86),radius=12,fill='#eaf3ff');d.text((85,yy+20),a,font=F[28],fill=colors[j]);lines=wrap(b,760,F[24])
   for kk,line in enumerate(lines):d.text((425,yy+15+kk*29),line,font=F[24],fill='#173653')
 def lineplot(arrays,labels):
  L,T,R,B=85,210,1180,445;lo=min(float(np.min(a)) for a in arrays);hi=max(float(np.max(a)) for a in arrays);pad=(hi-lo)*.1 or .1;lo-=pad;hi+=pad
  for j in range(5):
   yy=T+j*(B-T)/4;d.line((L,yy,R,yy),fill='#dce8f2');d.text((28,yy-10),f'{hi-j*(hi-lo)/4:.1f}',font=F[18],fill='#62788c')
  for j,(a,label) in enumerate(zip(arrays,labels)):
   d.text((85+j*505,165),label,font=F[22],fill=colors[j]);pts=[(L+kk*(R-L)/(len(a)-1),B-(v-lo)/(hi-lo)*(B-T)) for kk,v in enumerate(a)];d.line(pts[:max(2,int(len(pts)*progress))],fill=colors[j],width=3)
  for val in [900,1100,1300,1500,1700]:d.text((L+(val-900)/800*(R-L)-20,450),str(val),font=F[20],fill='#62788c')
  d.text((890,480),'Wavelength (nm)',font=F[22],fill='#62788c')
 if typ=='bug':lineplot([VIP,np.full(81,9.)],['Correct VIP','Extra-sum bug: every VIP = 9'])
 elif typ=='vip':lineplot([VIP,np.ones(81)],['Computed VIP / 81 variables','Heuristic VIP = 1'])
 elif typ=='direction':cards([('1200 nm',f'VIP {VIP[30]:.2f} / coefficient {vm.coef_.ravel()[30]:+.2f}'),('1450 nm',f'VIP {VIP[55]:.2f} / coefficient {vm.coef_.ravel()[55]:+.2f}'),('INTERPRET','Importance is not direction, significance or causality')])
 elif typ=='selection':cards([('FIT SELECT','60 training samples > 81 variables > 18 VIP hits'),('CV CAUTION','Global training mask uses held-fold labels'),('FOLD-LOCAL','Refit PLS + VIP + mask inside each fold')])
 elif typ=='compare':cards([('ALL 81',f'LV{vk} / CV {min(r["rmsecv"] for r in vc):.4f} / test {vrm:.4f}'),('VIP > 1',f'{int(sel.sum())} variables / LV{sk} / CV {min(r["rmsecv"] for r in sc):.4f} / test {srm:.4f}'),('QUALIFY','Fixed-mask CV is selection-biased; test n=20')])
 elif typ=='onehot':
  i=int(np.where(yo[ote]==1)[0][0]);vals=op[i];d.text((70,165),'Actual COC / predicted scores (not probabilities)',font=F[26],fill='#246bb2')
  for j,(c,v) in enumerate(zip(classes,vals)):
   xx=85+j*190;top=440-max(0,v)*190;d.rectangle((xx,top,xx+110,440),fill=colors[0] if j!=int(vals.argmax()) else colors[2]);d.text((xx,205),f'{v:+.2f}',font=F[26],fill='#173653');d.text((xx,462),c,font=F[24],fill='#62788c')
 elif typ=='confusion':
  left,top,cw,ch=235,210,125,39
  for j,c in enumerate(classes):d.text((left+j*cw+35,top-35),c,font=F[22],fill='#246bb2')
  for i,c in enumerate(classes):
   d.text((left-100,top+i*ch+5),c,font=F[22],fill='#173653')
   for j,v in enumerate(cm[i]):
    xx=left+j*cw;yy=top+i*ch;d.rounded_rectangle((xx,yy,xx+116,yy+33),radius=5,fill='#dbf0e8' if i==j else '#fce8e8' if v else '#edf4fb');d.text((xx+47,yy+3),str(v),font=F[22],fill='#173653')
  d.text((200,470),f'Actual rows / predicted columns / {np.trace(cm)}/{cm.sum()} = {acc*100:.1f}%',font=F[24],fill='#62788c')
 elif typ=='influence':
  L,T,R,B=110,220,1160,440;xmax=max(T2)*1.08;ylo,yhi=-5.2,-1;xx=lambda v:L+v/xmax*(R-L);yy=lambda v:B-(np.log10(v)-ylo)/(yhi-ylo)*(B-T)
  for power in [-5,-4,-3,-2,-1]:d.line((L,yy(10.**power),R,yy(10.**power)),fill='#e0eaf5');d.text((45,yy(10.**power)-10),f'1e{power}',font=F[18],fill='#62788c')
  d.line((xx(tl),T,xx(tl),B),fill='#889aaa',width=2);d.line((L,yy(ql),R,yy(ql)),fill='#889aaa',width=2)
  for a,b,r in zip(T2,Q,md):
   c={'calibration':colors[0],'new_normal':colors[2],'leverage_outlier':colors[1],'cross_instrument':'#c74661'}[r['role']];px,py=xx(a),yy(b);d.ellipse((px-5,py-5,px+5,py+5),fill=c)
  d.text((75,165),'Blue: calibration / orange: leverage / red: instrument shift',font=F[22],fill='#246bb2');d.text((85,475),'Q residual (log scale)',font=F[22],fill='#62788c');d.text((870,475),'Hotelling T squared',font=F[22],fill='#62788c')
 elif typ=='limits':cards([('T2 TRAIN',f'{tl:.3f} / n={n}, k=2 / approximate F limit'),('T2 NEW',f'{tn:.3f} / training limit x (n+1)/n'),('Q (JM)',f'{ql:.6f} / discarded eigenvalue approximation')])
 else:cards([('01 / VIP','Verify formula + fold-local variable selection'),('02 / CLASSIFY','One-hot PLS-DA > argmax > confusion matrix'),('03 / DOMAIN','Calibration-only PCA > T squared + Q > investigate')])
 take=s[5 if lang=='zh' else 6];assert F[24].getlength(take)<1150,take;d.rounded_rectangle((52,518,1228,565),radius=10,fill='#e7f6f1');d.text((68,528),take,font=F[24],fill='#17604e');text=s[2 if lang=='zh' else 3];font=F[26 if lang=='zh' else 24];lines=wrap(text,1150,font)
 if len(lines)>4:font=F[22];lines=wrap(text,1150,font)
 assert len(lines)<=4,(len(lines),text)
 for j,line in enumerate(lines):d.text((65,577+j*28),line,font=font,fill='#243c59')
 d.rectangle((52,694,52+1176*progress,699),fill='#246bdd');return im
if __name__=='__main__':render(scenes,OUT,cache_dir('w14'),'w14',frame)
