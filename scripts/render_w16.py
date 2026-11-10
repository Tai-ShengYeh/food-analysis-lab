#!/usr/bin/env python3
"""W16 independent NB13 reference computations and bilingual narrated tours."""
from pathlib import Path
import csv,json,hashlib
import numpy as np
from scipy import stats
from scipy.optimize import nnls
from sklearn.cross_decomposition import PLSRegression
from sklearn.decomposition import PCA
from sklearn.model_selection import LeaveOneGroupOut
from PIL import Image,ImageDraw,ImageFont
from course_video_common import render,cache_dir
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'labs/w16_sweetener_model/animations';OUT.mkdir(exist_ok=True,parents=True)
source=ROOT/'data/nb13_demo_spectra.csv';meta=list(csv.DictReader(source.open()));fields=[f for f in meta[0] if f.replace('.','',1).isdigit()];axis=np.array(list(map(float,fields)));X=np.array([[float(r[f]) for f in fields] for r in meta]);cal=np.array([r['split']=='calibration' for r in meta]);blind=np.array([r['split']=='blind_test' for r in meta]);query=np.array([r['role']=='unknown' for r in meta]);g=np.array([r['sample_id'] for r in meta])[cal];Y=np.array([[float(r[k]) for k in ['aspartame_pct','sucralose_pct']] for r in meta if r['split']=='calibration']);Yb=np.array([[float(r[k]) for k in ['aspartame_pct','sucralose_pct']] for r in meta if r['split']=='blind_test'])
def prep(Z):
 base=(Z[:,:5].mean(1,keepdims=True)+Z[:,-5:].mean(1,keepdims=True))/2;R=Z-base;return R/np.abs(R).sum(1,keepdims=True)
def vip(m):
 T=m.x_scores_;W=m.x_weights_;q=m.y_loadings_[0];ss=q*q*(T*T).sum(0);return np.sqrt(W.shape[0]*((W/np.linalg.norm(W,axis=0))**2@ss)/ss.sum())
curves={};models={};cvpreds={};preds={};metrics={};lods={}
for method,Z in [('raw',X),('baseline_absnorm',prep(X))]:
 curves[method]={}
 for target,key in enumerate(['A','S']):
  curve=[]
  for lv in range(1,9):
   cp=np.zeros(cal.sum())
   for tr,va in LeaveOneGroupOut().split(Z[cal],Y[:,target],g):cp[va]=PLSRegression(n_components=lv).fit(Z[cal][tr],Y[tr,target]).predict(Z[cal][va]).ravel()
   curve.append(dict(lv=lv,rmsecv=float(np.sqrt(np.mean((cp-Y[:,target])**2)))))
   if method=='raw' and lv==4:models[key]=PLSRegression(n_components=lv).fit(Z[cal],Y[:,target]);cvpreds[key]=cp
  curves[method][key]=curve
for j,key in enumerate(['A','S']):
 m=models[key];p=m.predict(X[blind]).ravel();preds[key]=p;err=p-Yb[:,j];rm=float(np.sqrt(np.mean(err**2)));metrics[key]=dict(LV=4,RMSEC=float(np.sqrt(np.mean((m.predict(X[cal]).ravel()-Y[:,j])**2))),RMSECV=curves['raw'][key][3]['rmsecv'],RMSEP=rm,bias=float(err.mean()),RPD=float(Yb[:,j].std(ddof=1)/rm));slope=float(np.polyfit(Y[:,j],cvpreds[key],1)[0]);sd0=float(cvpreds[key][Y[:,j]==0].std(ddof=1));lods[key]=dict(sd0=sd0,slope=slope,LOD=3.3*sd0/slope,LOQ=10*sd0/slope)
refs=[X[next(i for i,r in enumerate(meta) if r['role']=='library' and r['class']==c)] for c in ['aspartame','sucralose','erythritol']];R=np.column_stack(refs+[np.ones(len(axis))]);coef=np.array([nnls(R,row)[0] for row in X]);nnlsRMSE=np.sqrt(np.mean((100*coef[blind,:2]-Yb)**2,axis=0));pm=PCA(n_components=49).fit(X[cal]);k=3;n=int(cal.sum());score=pm.transform(X)[:,:k];recon=score@pm.components_[:k]+pm.mean_;t2=(score*score/pm.explained_variance_[:k]).sum(1);q=((X-recon)**2).sum(1);tail=pm.explained_variance_[k:];th1=tail.sum();th2=(tail*tail).sum();th3=(tail**3).sum();h=1-2*th1*th3/(3*th2*th2);ql=float(th1*(stats.norm.ppf(.95)*np.sqrt(2*th2*h*h)/th1+1+th2*h*(h-1)/(th1*th1))**(1/h));tl=float(k*(n-1)/(n-k)*stats.f.ppf(.95,k,n-k));qi=int(np.where(query)[0][0]);querypred={key:float(m.predict(X[query]).ravel()[0]) for key,m in models.items()};vips={key:vip(m) for key,m in models.items()}
reference=dict(source='data/nb13_demo_spectra.csv',sha256=hashlib.sha256(source.read_bytes()).hexdigest(),counts=dict(calibration_spectra=int(cal.sum()),calibration_bottles=len(set(g)),blind_spectra=int(blind.sum()),blind_bottles=len(set(r['sample_id'] for r in meta if r['split']=='blind_test'))),curves=curves,metrics=metrics,LOD=lods,VIP={key:v.tolist() for key,v in vips.items()},nnls=dict(rmsep=nnlsRMSE.tolist(),coefficients=coef.tolist(),column_order=['aspartame','sucralose','erythritol','offset'],constraints='all four coefficients nonnegative; no sum-to-one'),domain=dict(n=n,k=k,t2_training_limit=tl,t2_new_limit=tl*(n+1)/n,q_limit=ql,explained_variance_pct=float(pm.explained_variance_ratio_[:k].sum()*100),T2=t2.tolist(),Q=q.tolist()),query=dict(sample_id=meta[qi]['sample_id'],PLS_predictions=querypred,T2=float(t2[qi]),Q=float(q[qi]),report='outside modeled domain; numerical concentration withheld'))
(OUT/'model-reference.json').write_text(json.dumps(reference,indent=2))
scenes=[
['兩種算法，都能告訴你代糖含量嗎？','Can two different methods quantify the same sweetener?', '同一包粉末，PLS 用已知配方學習，NNLS 用純物質光譜擬合。兩種方法可能給出不同答案。本週要比較誤差與假設，還要學會辨認：即使模型吐出數字，也不一定能把它當成含量報告。','PLS learns from known blends; NNLS fits pure-reference spectra. The same powder can receive different answers. This week compares their errors and assumptions, then asks when a numerical prediction should not be reported as a concentration.','workflow','比較方法之前，先確認資料、假設與適用範圍','Check data, assumptions and applicability before comparing methods'],
['25 瓶、50 條校正光譜：按瓶分組','25 bottles, 50 calibration spectra: group by bottle','合併全班二十五瓶配方，每瓶兩條光譜，共五十條校正資料。交叉驗證每次留出一整瓶的兩條光譜，共二十五折。欄位 sample_id 是瓶號，group 是配製組，不能混用；七瓶盲樣的十四條光譜留到最後驗證。','Combine twenty-five formulations with two spectra per bottle. Leave one whole bottle out in each of twenty-five validation folds. Group by sample_id, not the preparation-group column. Reserve fourteen spectra from seven blind bottles for the final test.','groups','CV 分組用 sample_id；50 條光譜不是 50 瓶','CV groups use sample_id; 50 spectra are not 50 bottles'],
['兩個 PLS1，各自選 LV','Two PLS1 models, each with its own LV choice','阿斯巴甜和三氯蔗糖各建一個 PLS1，依校正組的分組 RMSECV 選 LV。示範兩者都選到四個，並不表示以後都一樣。PLS2 是另一種共同建模選項，本課沒有用這份結果證明 PLS1 或 PLS2 必然比較好。','Fit one PLS1 model for each sweetener and choose latent variables using calibration grouped RMSECV. Both select four in this demo, not by a universal rule. PLS2 is a separate joint-model option; these results do not establish that either approach always performs better.','curve','A 與 S 各自選 LV；PLS2 優劣須另做同條件比較','Select LVs per target; compare PLS2 separately under equal validation'],
['前處理不是做越多越好','More preprocessing is not automatically better','比較原始光譜與基線扣除加面積歸一化，兩條路都保留 PLS 的預設尺度化。阿斯巴甜原始路線最佳 RMSECV 約零點七一一，前處理路線約一點三零六；因此這份資料選原始路線。換資料時必須重新比較。','Compare raw spectra with baseline subtraction plus absolute-area normalization. Both retain default PLS scaling. Aspartame\'s best grouped RMSECV is about zero point seven one one for raw input versus one point three zero six after preprocessing. This dataset chooses raw; other data may differ.','preprocessing','依校正 CV 選擇，不用盲樣 RMSEP 調前處理','Select preprocessing by calibration CV, not blind-test RMSEP'],
['盲樣報告卡：誤差、偏差、樣本數一起看','Read errors, bias and sample count together','鎖定流程後才打開盲樣測試。PLS 的阿斯巴甜 RMSEP 約零點五五七、三氯蔗糖約零點五零三百分點；後者偏差約正零點四零五。RPD 與濃度範圍有關，只有七個獨立盲樣，不能單靠分級宣稱能上產線。','Reveal blind-test errors only after locking the pipeline. PLS test RMSE is about zero point five five seven for aspartame and zero point five zero three percentage points for sucralose; the latter has bias around plus zero point four zero five. Seven independent blind bottles and RPD bands do not establish production fitness.','metrics','14 條測試光譜來自 7 瓶；RPD 不是生產合格證','14 test spectra come from 7 bottles; RPD is not certification'],
['高 VIP 可能是填充劑的間接線索','High VIP may reflect the filler indirectly','赤藻糖醇比例等於一百減掉兩種甜味劑，所以阿斯巴甜增加時，填充劑一定減少。模型可能借用填充劑的波段預測，這是封閉性造成的間接線索，不是阿斯巴甜自己的峰，更不是因果證明；換填充劑就可能失效。','Erythritol is one hundred percent minus both sweeteners. When aspartame increases, filler decreases. The model can use filler bands as indirect clues through compositional closure. Those are not aspartame-specific peaks or causal proof; changing filler can break the relationship.','vip','VIP 要對照成分與封閉性；重要不等於專一或因果','Interpret VIP with composition; importance is not specificity or causality'],
['NNLS：純物質加起來，能重建未知光譜嗎？','NNLS: can pure references reconstruct the unknown spectrum?', 'NNLS 用三條純物質參考加上一條常數背景，找出非負係數，讓殘差平方和最小。本例沒有強迫係數總和等於一。係數先表示光譜貢獻，只有參考尺度、響應與線性混合假設合理時，才能討論如何換成質量比例。','NNLS combines three pure spectra and a constant offset using nonnegative coefficients to minimize squared residuals. This demo does not constrain their sum to one. Coefficients describe spectral contributions; mass interpretation requires compatible reference scales, responses, and linear mixing assumptions.','nnls','c >= 0 不代表 sum(c)=1，也不自動等於質量分率','Nonnegative coefficients do not automatically form mass fractions'],
['歸一化參考光譜，係數的意義也會改','Normalizing references changes coefficient interpretation','把每條參考光譜分別歸一化，最小平方仍可能重建得一樣好，但係數會跟著尺度改變。因此不能看到擬合很好，就把新的係數直接乘一百當質量百分比。缺少新成分參考時，NNLS 也可能用錯的成分硬湊答案。','Individually normalizing reference spectra can leave an equally good least-squares reconstruction while changing coefficient scales. A small residual does not justify multiplying the new coefficients by one hundred as mass percentages. Missing components can also force an inappropriate reference combination.','normalization','擬合好不等於成分對；參考尺度改變，係數也改變','A good fit need not identify the right components or mass fractions'],
['PLS 比 NNLS 好，是這份模擬的結果','PLS wins here, not by universal law','同一批十四條盲樣光譜，NNLS 的阿斯巴甜與三氯蔗糖 RMSEP 約零點九七八與零點七六八，比這份 PLS 模型高。但換了儀器、混合非線性、基質或參考品質，結果可能改變。方法比較必須使用相同的獨立樣品。','On the same fourteen blind spectra, NNLS test RMSE is about zero point nine seven eight for aspartame and zero point seven six eight for sucralose, higher than PLS here. Instruments, nonlinear mixing, matrices, and reference quality can change that result. Compare methods on the same independent samples.','compare','同一批盲樣公平比較；不能把本例勝負當成定律','Use the same blind samples; this ranking is not a universal law'],
['LOD／LOQ：用折外預測做簡化估計','LOD and LOQ: simplified estimates from out-of-fold predictions','取校正組中待測成分為零的十條光譜，用折外預測的標準差與預測對實際的斜率估計。阿斯巴甜 LOD 約二點六八、LOQ 約八點一二百分比。零成分樣品仍有另一種甜味劑干擾，這只是教學近似，不是正式方法確效。','Use out-of-fold predictions for the ten zero-analyte calibration spectra, their standard deviation, and the prediction-versus-reference slope. Aspartame LOD is about two point six eight percent and LOQ eight point one two percent. Those samples still contain the other sweetener; this is a teaching approximation, not formal method validation.','lod','簡化 LOD/LOQ 不是正式確效，也不是通用定量許可','Approximate LOD/LOQ is not formal validation or permission to quantify'],
['先過適用範圍，再談檢出與定量','Check model applicability before detection or quantification','市售挑戰樣品換了填充劑，PLS 竟預測約四十八點二百分比。T 平方約二百二十四，Q 約三點一三，都遠超模型界限。這時先寫超出模型適用範圍，不報含量；不能因包裝標示一點八，就直接改寫成低於 LOD。','The simulated commercial challenge changes filler, and PLS predicts about forty-eight point two percent. T squared around two hundred twenty-four and Q around three point one three exceed the model limits. Report outside the model domain and withhold concentration; the label value alone is not grounds for reporting below LOD.','domain','先查 T²/Q 與範圍；域外不報濃度數值','Check T-squared/Q and range first; withhold out-of-domain concentration'],
['把判讀規則寫進 W17 模型報告卡','Make reporting rules explicit in the W17 model card','域內樣品也要檢查預測是否低於 LOD、介於 LOD 與 LOQ，或超過校正範圍。保留方法、前處理、LV、誤差、VIP、NNLS 比較與判讀理由。進入六幕實驗操作並下載證據；正式報告換成本班實測與已驗證的方法。','For in-domain samples, check predictions against LOD, LOQ, and calibration range. Retain methods, preprocessing, latent variables, errors, VIP, NNLS comparison, and reporting rationale. Explore the six-act lab and download evidence; use class measurements and validated procedures for formal reporting.','workflow','交付：兩個 PLS1、VIP、NNLS、LOD 與域外判讀','Submit: two PLS1s, VIP, NNLS, LOD and applicability decisions']]
FONT=Path('/home/administrator/.local/share/fonts/hermes-food-tests/msjh.ttc')
if not FONT.exists():FONT=Path('/mnt/c/Windows/Fonts/msjh.ttc')
if not FONT.exists():FONT=Path('C:/Windows/Fonts/msjh.ttc')
F={n:ImageFont.truetype(str(FONT),n) for n in [18,20,22,24,26,28,30,34,40]};colors=['#246bc4','#df7d23','#129785']
def wrap(text,width,font):
 words=text.split(' ') if all(ord(c)<128 for c in text) else list(text);sep=' ' if all(ord(c)<128 for c in text) else '';lines=[];line=''
 for w in words:
  t=line+sep+w if line else w
  if line and font.getlength(t)>width:lines.append(line);line=w
  else:line=t
 if line:lines.append(line)
 return lines

def frame(s,lang,progress):
 im=Image.new('RGB',(1280,720),'#edf6ff');d=ImageDraw.Draw(im);d.rounded_rectangle((24,18,1256,702),radius=24,fill='white');d.text((52,32),'FOOD ANALYSIS LAB / W16 / PLS + NNLS + REPORTING',font=F[22],fill='#246bb2')
 for j,line in enumerate(wrap(s[0 if lang=='zh' else 1],1170,F[40])):d.text((52,75+j*46),line,font=F[40],fill='#173653')
 typ=s[4]
 def cards(entries):
  for j,(a,b) in enumerate(entries):
   yy=180+j*105;d.rounded_rectangle((65,yy,1215,yy+86),radius=12,fill='#eaf3ff');d.text((85,yy+20),a,font=F[28],fill=colors[j]);lines=wrap(b,760,F[24])
   for kk,line in enumerate(lines):d.text((425,yy+15+kk*29),line,font=F[24],fill='#173653')
 def lineplot(arrays,labels,xs,xlabel):
  L,T,Rt,B=85,210,1180,445;lo=min(float(np.min(a)) for a in arrays);hi=max(float(np.max(a)) for a in arrays);pad=(hi-lo)*.1 or .1;lo-=pad;hi+=pad
  for j in range(5):
   yy=T+j*(B-T)/4;d.line((L,yy,Rt,yy),fill='#dce8f2');d.text((25,yy-10),f'{hi-j*(hi-lo)/4:.2f}',font=F[18],fill='#62788c')
  for j,(a,label) in enumerate(zip(arrays,labels)):
   d.text((85+j*505,165),label,font=F[22],fill=colors[j]);pts=[(L+kk*(Rt-L)/(len(a)-1),B-(v-lo)/(hi-lo)*(B-T)) for kk,v in enumerate(a)];d.line(pts[:max(2,int(len(pts)*progress))],fill=colors[j],width=3)
  for k_ in [0,len(xs)//3,2*len(xs)//3,len(xs)-1]:d.text((L+k_*(Rt-L)/(len(xs)-1)-15,450),str(round(xs[k_])),font=F[20],fill='#62788c')
  d.text((850,480),xlabel,font=F[22],fill='#62788c')
 if typ=='groups':cards([('CALIBRATION','25 bottles x 2 reloads = 50 spectra'),('GROUPED CV','Leave 1 bottle out / 25 folds / sample_id'),('BLIND TEST','7 bottles x 2 reloads = 14 spectra')])
 elif typ=='curve':lineplot([[r['rmsecv'] for r in curves['raw'][key]] for key in ['A','S']],['Aspartame / grouped CV','Sucralose / grouped CV'],np.arange(1,9),'Latent variables')
 elif typ=='preprocessing':lineplot([[r['rmsecv'] for r in curves[name]['A']] for name in ['raw','baseline_absnorm']],['Raw + PLS autoscale','Baseline + absolute-area normalization'],np.arange(1,9),'Latent variables')
 elif typ=='metrics':cards([('ASPARTAME',f"RMSEC/CV/EP: {metrics['A']['RMSEC']:.3f}/{metrics['A']['RMSECV']:.3f}/{metrics['A']['RMSEP']:.3f}"),('SUCRALOSE',f"RMSEC/CV/EP: {metrics['S']['RMSEC']:.3f}/{metrics['S']['RMSECV']:.3f}/{metrics['S']['RMSEP']:.3f}"),('CONTEXT','Errors: w/w percentage points / only 7 test bottles')])
 elif typ=='vip':lineplot([vips['A'],np.ones(len(axis))],['Aspartame VIP','VIP = 1 heuristic'],axis,'Raman shift (cm-1)')
 elif typ=='nnls':
  idx=int(np.where(blind)[0][0]);lineplot([X[idx],R@coef[idx]],['Blind example raw spectrum','NNLS reconstruction'],axis,'Raman shift (cm-1)')
 elif typ=='normalization':cards([('REFERENCES','Independent scaling changes coefficient units'),('RECONSTRUCT','Same spectral span can give the same residual'),('REPORT','No sum-to-one constraint; no automatic mass fraction')])
 elif typ=='compare':cards([('PLS1',f"Blind RMSEP A/S: {metrics['A']['RMSEP']:.3f} / {metrics['S']['RMSEP']:.3f}"),('NNLS',f'Blind RMSEP A/S: {nnlsRMSE[0]:.3f} / {nnlsRMSE[1]:.3f}'),('QUALIFY','Same 14 spectra / 7 bottles / simulated, not universal')])
 elif typ=='lod':cards([('ASPARTAME',f"sd0 {lods['A']['sd0']:.4f} / slope {lods['A']['slope']:.4f}"),('APPROXIMATE',f"LOD {lods['A']['LOD']:.2f}% / LOQ {lods['A']['LOQ']:.2f}%"),('LIMITATION','OOF zero-analyte samples still contain interferent')])
 elif typ=='domain':cards([('RAW PLS',f"Commercial simulation: predicted A {querypred['A']:.1f}%"),('DOMAIN',f'T2 {t2[qi]:.1f} vs {tl:.3f}; Q {q[qi]:.2f} vs {ql:.5f}'),('REPORT','Outside model domain: concentration withheld')])
 else:cards([('01 / FIT','Whole-bottle CV > select preprocessing/LVs > lock'),('02 / COMPARE','PLS1 + VIP / raw reference NNLS + residuals'),('03 / REPORT','Domain first > LOD/LOQ > evidence + limitations')])
 take=s[5 if lang=='zh' else 6];assert F[24].getlength(take)<1150,take;d.rounded_rectangle((52,518,1228,565),radius=10,fill='#e7f6f1');d.text((68,528),take,font=F[24],fill='#17604e');text=s[2 if lang=='zh' else 3];font=F[26 if lang=='zh' else 24];lines=wrap(text,1150,font)
 if len(lines)>4:font=F[22];lines=wrap(text,1150,font)
 assert len(lines)<=4,(len(lines),text)
 for j,line in enumerate(lines):d.text((65,577+j*28),line,font=font,fill='#243c59')
 d.rectangle((52,694,52+1176*progress,699),fill='#246bdd');return im
if __name__=='__main__':render(scenes,OUT,cache_dir('w16'),'w16',frame)
