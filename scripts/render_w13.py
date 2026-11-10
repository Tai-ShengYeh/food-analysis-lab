#!/usr/bin/env python3
"""Bilingual W13 course tours from original NB11 simulated data.
Requires NumPy/SciPy/scikit-learn/Pillow, ffmpeg and ElevenLabs takes in scripts/vo/ (voice IAN, eleven_v3).
"""
from pathlib import Path
import csv,json,math,subprocess,hashlib
import numpy as np
from scipy.spatial.distance import cdist
from scipy.signal import savgol_filter
from sklearn.cross_decomposition import PLSRegression
from sklearn.model_selection import LeaveOneGroupOut
import sys;sys.path.insert(0,str(Path(__file__).resolve().parent))
from course_video_common import vo_wav,cache_dir
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'labs/w13_pls_acetic/animations';CACHE=cache_dir('w13')
OUT.mkdir(exist_ok=True,parents=True);CACHE.mkdir(exist_ok=True,parents=True)
FONT=Path('/home/administrator/.local/share/fonts/hermes-food-tests/msjh.ttc')
if not FONT.exists():FONT=Path('/mnt/c/Windows/Fonts/msjh.ttc')
if not FONT.exists():FONT=Path('C:/Windows/Fonts/msjh.ttc')
F={n:ImageFont.truetype(str(FONT),n) for n in [18,20,22,24,26,28,30,34,40]}
rows=list(csv.DictReader((ROOT/'data/nb11_demo_spectra.csv').open()));fields=list(rows[0])[5:];axis=np.array(list(map(float,fields)));X=np.array([[float(r[f]) for f in fields] for r in rows]);y=np.array([float(r['acidity_pct']) for r in rows]);g=np.array([r['sample_id'] for r in rows]);ids=list(dict.fromkeys(g));pool=[s for s in ids if s!='VINEGAR_WHITE_W4REF'];means=np.array([X[g==s].mean(0) for s in pool]);D=cdist(means,means);a,b=np.unravel_index(D.argmax(),D.shape);chosen=[int(a),int(b)]
while len(chosen)<12:
 rem=[i for i in range(len(pool)) if i not in chosen];chosen.append(rem[np.argmax(D[np.ix_(rem,chosen)].min(1))])
calids=[pool[i] for i in chosen];cal=np.isin(g,calids)
preps={'raw':X,'SNV':(X-X.mean(1,keepdims=True))/X.std(1,keepdims=True),'SG':savgol_filter(X,9,2,deriv=1,axis=1)};curves={}
for name,Z in preps.items():
 values=[]
 for k in range(1,7):
  Zc=Z[cal];yc=y[cal];gc=g[cal];pred=np.zeros(len(yc))
  for tr,va in LeaveOneGroupOut().split(Zc,yc,gc):pred[va]=PLSRegression(n_components=k).fit(Zc[tr],yc[tr]).predict(Zc[va]).ravel()
  m=PLSRegression(n_components=k).fit(Zc,yc);values.append(dict(lv=k,rmsec=float(np.sqrt(np.mean((m.predict(Zc).ravel()-yc)**2))),rmsecv=float(np.sqrt(np.mean((pred-yc)**2)))))
  if name=='SNV' and k==2:model=m;cvpred=pred
 curves[name]=values
predtest=model.predict(preps['SNV'][~cal]).ravel();resid=predtest-y[~cal];rmsep=float(np.sqrt(np.mean(resid**2)));metrics=dict(rmsec=curves['SNV'][1]['rmsec'],rmsecv=curves['SNV'][1]['rmsecv'],rmsep=rmsep,bias=float(resid.mean()),r2=float(1-(resid**2).sum()/((y[~cal]-y[~cal].mean())**2).sum()),rpd=float(y[~cal].std(ddof=1)/rmsep))
(OUT/'pls-reference.json').write_text(json.dumps(dict(source='data/nb11_demo_spectra.csv',sha256=hashlib.sha256((ROOT/'data/nb11_demo_spectra.csv').read_bytes()).hexdigest(),calibration_ids=list(map(str,calids)),test_ids=list(map(str,dict.fromkeys(g[~cal]))),curves=curves,metrics=metrics,test_predictions=predtest.tolist(),test_residuals=resid.tolist()),indent=2))
scenes=[
['光譜儀怎麼知道醋酸濃度？','How does a spectrometer know acidity?', '光譜儀本身不知道濃度。它要靠一批有參考值的樣品，建立光譜與醋酸濃度的關係。本週用第四週滴定的觀念，練習 PLS 定量；本導覽使用 NB11 模擬資料，不是實測檢驗成績。','A spectrometer does not know concentration by itself. It learns a relationship from spectra paired with reference values. This week, connect titration to PLS regression. The tour uses NB11 simulated teaching data, not actual laboratory performance.','spectra','X 是光譜；y 是參考濃度；資料為教學模擬','X: spectra; y: reference concentration; simulated data'],
['先分組，再談模型好不好','Split by sample before evaluating a model','示範有十六個樣品，每個三次重裝。十二個樣品作校正，四個樣品作測試；白醋參考樣固定留在測試側。同一樣品的三條光譜，不能一部分進校正、一部分進測試。','The demo has sixteen samples with three reloads each. Twelve samples form calibration and four form the test set. The white-vinegar reference stays in the test set. All three replicates of one sample must remain on the same side.','split','12 校正樣品 / 4 測試樣品；重複不拆開','12 calibration / 4 test samples; keep replicates together'],
['PLS 與 PCA：有沒有使用答案？','PLS versus PCA: does the fit use y?', 'PCA 找光譜自己變異最大的方向。PLS 同時使用光譜與濃度，找跟答案一起變化的潛在變數。它能處理波長多又共線的情況，但不保證加入更多潛在變數，預測就會更好。','PCA seeks directions of variation in spectra alone. PLS uses spectra and reference concentrations to find latent variables related to the response. It handles many correlated wavelengths, but adding more latent variables does not guarantee better prediction.','supervised','PCA：只看 X；PLS：同時看 X 與 y','PCA uses X; PLS uses both X and y'],
['前處理與 Scale，分開確認','Separate spectral preprocessing from scaling','比較 raw、SNV 與 SG 一階導數時，要用相同的分組驗證。SNV 是逐條光譜標準化；PLS 的 Scale 則按波長欄位縮放。本課保留 Scale 預設開啟，而且每輪的平均與標準差只能用該輪訓練資料估計。','Compare raw spectra, SNV, and SG derivatives using the same grouped validation. SNV standardizes each spectrum; PLS scaling standardizes variables. Here Scale is on by default. Every fold must estimate its means and standard deviations from that fold\'s training data only.','preprocessing','SNV 按列；PLS Scale 按欄；每折重新估計','SNV by spectrum; Scale by variable; refit within each fold'],
['分組交叉驗證：每輪留下一整支樣品','Grouped CV: leave out one whole sample','每輪拿走一個樣品及其三次重裝，用其他十一個樣品建模，再預測被拿走的三條光譜。共輪流十二次，收集三十六個折外預測，計算 RMSECV。測試集完全不參與這個過程。','Leave one calibration sample and all three reloads out. Fit on the other eleven samples, then predict the held-out three spectra. Repeat twelve times to obtain thirty-six out-of-fold predictions and RMSECV. The test set does not participate.','cv','訓練 11 組 > 預測 1 組 > 輪流 12 次','Train 11 groups > predict 1 group > repeat 12 times'],
['用 RMSECV 選 LV，不看測試誤差','Choose LVs by RMSECV, not test error','增加 LV 往往讓校正誤差下降，卻可能開始配合雜訊。本資料用 SNV 時，兩個 LV 的 RMSECV 約零點四零零。這是目前資料算出的選擇，不是所有醋酸模型都應該用兩個 LV。','Adding latent variables can reduce calibration error while fitting noise. For these data, SNV with two latent variables gives RMSECV around zero point four zero zero. This is a result for this dataset, not a universal prescription for acidity models.','curve','SNV + 2 LV：RMSECV 0.400 % w/v','SNV + 2 LVs: RMSECV 0.400 % w/v'],
['資料外洩：模型可能認得重複樣品','Leakage: the model may recognize replicates','如果把同一樣品的重複分到訓練與驗證兩側，就不再是評估全新樣品。逐列切分可能給出偏樂觀的結果，但單一資料集不一定每次都更低。正確規則是依預期使用情境，保持樣品層級的獨立。','Splitting replicates between training and validation no longer tests a genuinely new sample. Row-wise splitting can look optimistic, although it need not give a lower error on every dataset. Keep sample-level independence aligned with the intended use.','leakage','分組避免同樣品重複洩漏；不要追求最低數字','Group replicates; do not chase the lowest reported number'],
['先鎖定流程，最後才打開測試集','Lock the pipeline before opening the test set','選好前處理、Scale 與 LV 後，先鎖定設定，再用全部校正資料建立最終模型。本示範測試 RMSEP 約零點四二七。若看過測試結果再回頭調參，這批測試集就不能再稱為未碰過的獨立驗證。','Lock preprocessing, scaling, and latent-variable count before fitting the final calibration model. The demonstration test RMSEP is about zero point four two seven. If you tune after seeing test results, that test set is no longer untouched independent validation.','prediction','4 個獨立測試樣品，不是 12 個獨立樣品','4 independent test samples, not 12 independent samples'],
['誤差成績單：RMSE、bias 與 RPD','Report RMSE, bias, and RPD together','RMSE 看整體誤差量級，bias 看平均偏高或偏低，兩者不能互相取代。RPD 是測試參考值的標準差除以 RMSEP，會受測試集濃度範圍影響。四個獨立樣品太少，不能只憑 RPD 三點九一就宣稱能上產線。','RMSE measures overall error; bias measures average signed error. Neither replaces the other. RPD divides the test reference standard deviation by RMSEP and depends on the test concentration spread. Four independent samples are too few to justify production use from RPD alone.','metrics','RMSEP 0.427；bias -0.054；RPD 3.91（本模擬）','RMSEP 0.427; bias -0.054; RPD 3.91 (this demo)'],
['參考值若有誤差，模型也會受影響','Reference errors affect calibration and validation','參考方法的系統性偏差，會帶進校正的濃度尺度。獨立隨機誤差會增加驗證殘差的變異，但不是每次都形成不可突破的硬下限。先確認滴定品質、單次或平均參考值，以及不確定度，才解讀模型誤差。','Systematic reference bias shifts the calibration scale. Independent random reference error contributes to validation residual variance, but is not an inviolable lower bound for every observed RMSE. Check titration quality, averaging, and uncertainty before interpreting model error.','reference','參考值也是量測，不是零誤差的答案','A reference value is a measurement, not an error-free truth'],
['適用範圍與實驗安全','Applicability and laboratory safety','本教學校正範圍是零到十百分比重量體積濃度的醋酸水溶液。範圍內也要留意基質與儀器差異，不能直接套到另一台儀器。配製時依實驗規範，在抽風櫃戴護目鏡與手套，緩慢把酸加入水，並遠離火源。','The teaching calibration covers zero to ten percent weight per volume aqueous acetic acid. Even inside that range, matrix and instrument changes matter. Do not transfer the model blindly. Follow the lab procedure: hood, goggles, gloves, slowly add acid to water, and keep away from ignition sources.','scope','0–10 % w/v；相同基質與量測條件仍需驗證','0–10 % w/v; matrix and instrument conditions still matter'],
['六幕實驗：交出可追溯的模型報告','Six-act lab: produce a traceable model report','進入互動實驗，從分組、前處理、交叉驗證到鎖定測試，逐幕預測並解釋。下載曲線、預測與模型紀錄。正式作業換成全班實測資料，報告適用範圍、六項指標與資料切分，並與其他組的儀器比較。','Explore the six-act lab from grouping and preprocessing to cross-validation and locked testing. Predict, operate, explain, and download curves, predictions, and the model record. For the assignment, use class measurements and report the split, applicability range, six metrics, and instrument comparison.','workflow','交付：分組、CV 曲線、六指標、適用範圍','Submit: split, CV curves, six metrics, applicability range']]
(OUT/'storyboard.json').write_text(json.dumps([dict(zip(['title_zh','title_en','narration_zh','narration_en','visual','takeaway_zh','takeaway_en'],s)) for s in scenes],ensure_ascii=False,indent=2))
colors=['#246bc4','#df7d23','#129785']
def wrap(text,width,font):
 words=text.split(' ') if all(ord(c)<128 for c in text) else list(text);sep=' ' if all(ord(c)<128 for c in text) else '';lines=[];line=''
 for w in words:
  s=line+sep+w if line else w
  if line and font.getlength(s)>width:lines.append(line);line=w
  else:line=s
 if line:lines.append(line)
 return lines

def frame(s,lang,progress):
 im=Image.new('RGB',(1280,720),'#edf6ff');d=ImageDraw.Draw(im);d.rounded_rectangle((24,18,1256,702),radius=24,fill='white');d.text((52,32),'FOOD ANALYSIS LAB / W13 / PLS REGRESSION',font=F[22],fill='#246bb2')
 for j,line in enumerate(wrap(s[0 if lang=='zh' else 1],1170,F[40])):d.text((52,75+j*46),line,font=F[40],fill='#173653')
 typ=s[4]
 def cards(entries):
  for j,(a,b) in enumerate(entries):
   yy=180+j*105;d.rounded_rectangle((65,yy,1215,yy+86),radius=12,fill='#eaf3ff');d.text((85,yy+20),a,font=F[28],fill=colors[j]);lines=wrap(b,760,F[24])
   for k,line in enumerate(lines):d.text((425,yy+15+k*29),line,font=F[24],fill='#173653')
 def linesplot(arrays,labels,xs,xlabel):
  L,T,R,B=85,210,1180,445;lo=min(float(np.min(a)) for a in arrays);hi=max(float(np.max(a)) for a in arrays);pad=(hi-lo)*.1 or .1;lo-=pad;hi+=pad
  for k in range(5):
   yy=T+k*(B-T)/4;d.line((L,yy,R,yy),fill='#dce8f2');d.text((28,yy-10),f'{hi-k*(hi-lo)/4:.2f}',font=F[18],fill='#62788c')
  for j,(a,label) in enumerate(zip(arrays,labels)):
   d.text((85+j*355,165),label,font=F[22],fill=colors[j]);pts=[(L+k*(R-L)/(len(a)-1),B-(v-lo)/(hi-lo)*(B-T)) for k,v in enumerate(a)];d.line(pts[:max(2,int(len(pts)*progress))],fill=colors[j],width=3)
  for k in [0,len(xs)//3,2*len(xs)//3,len(xs)-1]:d.text((L+k*(R-L)/(len(xs)-1)-15,450),str(round(xs[k])),font=F[20],fill='#62788c')
  d.text((860,480),xlabel,font=F[22],fill='#62788c')
 if typ=='spectra':linesplot([X[0],X[21],X[39]],['STD-00','STD-07','STD-13'],axis,'Wavelength (nm)')
 elif typ=='split':
  d.text((72,163),'16 samples x 3 reloads = 48 spectra / SIMULATED',font=F[26],fill='#246bb2')
  for j,sid in enumerate(ids):
   xx=75+(j%8)*146;yy=225+(j//8)*125;c='#246bc4' if sid in calids else '#df7d23';label=sid.replace('VINEGAR_WHITE_W4REF','WHITE').replace('VINEGAR_B_DEMO','VINEGAR_B');d.text((xx,yy),label,font=F[18],fill=c)
   for k in range(3):d.rounded_rectangle((xx+k*31,yy+35,xx+24+k*31,yy+75),radius=5,fill=c)
  d.text((75,480),'BLUE: calibration / ORANGE: test (all 3 replicates together)',font=F[22],fill='#62788c')
 elif typ=='supervised':cards([('PCA','X > maximum variance'),('PLS','X + y > latent variables > prediction'),('VALIDATE','New samples, not fitted training answers')])
 elif typ=='preprocessing':linesplot([[r['rmsecv'] for r in c] for c in curves.values()],['Raw CV','SNV CV','SG derivative CV'],np.arange(1,7),'Latent variables (LV)')
 elif typ=='cv':
  for row in range(5):
   d.text((65,185+row*57),f'Fold {row+1}',font=F[22],fill='#173653')
   for j in range(12):d.rounded_rectangle((200+j*81,185+row*57,266+j*81,225+row*57),radius=6,fill='#df7d23' if j==row else '#246bc4')
  d.text((200,480),'12 folds; 1 held-out sample with all 3 reloads per fold',font=F[22],fill='#62788c')
 elif typ=='curve':linesplot([[r['rmsec'] for r in curves['SNV']],[r['rmsecv'] for r in curves['SNV']]],['RMSEC (training)','RMSECV (grouped)'],np.arange(1,7),'Latent variables (LV)')
 elif typ=='leakage':cards([('GROUP SPLIT','Sample A: r1 + r2 + r3 stay together'),('ROW SPLIT','Same-sample replicates may cross folds'),('CHECK','Lower error does not prove better generalization')])
 elif typ=='prediction':
  L,T,R,B=140,205,1100,440;lo,hi=-.8,10.8
  px=lambda a:L+(a-lo)/(hi-lo)*(R-L)
  py=lambda b:B-(b-lo)/(hi-lo)*(B-T)
  for v in range(0,11,2):
   d.line((L,py(v),R,py(v)),fill='#e3ecf5');d.text((100,py(v)-10),str(v),font=F[18],fill='#62788c');d.text((px(v)-6,448),str(v),font=F[18],fill='#62788c')
  d.line((L,T,L,B,R,B),fill='#8fa4b8',width=2);d.line((L,B,R,T),fill='#b2c4d5',width=2)
  for ys,yp,c in [(y[cal],cvpred,colors[0]),(y[~cal],predtest,colors[1])]:
   for a,b in zip(ys,yp):
    xx=px(a);yy=py(b);d.ellipse((xx-5,yy-5,xx+5,yy+5),fill=c)
  d.text((85,165),'Calibration: CV predictions',font=F[22],fill=colors[0]);d.text((665,165),'Independent test predictions',font=F[22],fill=colors[1]);d.text((710,480),'Reference acidity (% w/v)',font=F[22],fill='#62788c');d.text((85,480),'Predicted acidity (% w/v)',font=F[22],fill='#62788c')
 elif typ=='metrics':cards([('CAL / CV',f"RMSEC {metrics['rmsec']:.3f} / RMSECV {metrics['rmsecv']:.3f}"),('TEST',f"RMSEP {rmsep:.3f} / bias {metrics['bias']:+.3f} % w/v"),('CONTEXT',f"R2 {metrics['r2']:.3f} / RPD {metrics['rpd']:.2f} / only 4 samples")])
 elif typ=='reference':cards([('SYSTEMATIC','Reference bias shifts the calibration scale'),('RANDOM','Independent reference noise adds residual variance'),('CHECK','Reference uncertainty and replicate averaging')])
 elif typ=='scope':cards([('DOMAIN','0-10 % w/v / aqueous acetic acid'),('TRANSFER','Instrument and matrix changes need validation'),('SAFETY','Hood + goggles + gloves / acid into water')])
 else:cards([('01 / DESIGN','Group split + reference method + range'),('02 / SELECT','Preprocess + grouped CV > lock settings'),('03 / REPORT','Final test + metrics + applicability')])
 take=s[5 if lang=='zh' else 6];assert F[24].getlength(take)<1150,take;d.rounded_rectangle((52,518,1228,565),radius=10,fill='#e7f6f1');d.text((68,528),take,font=F[24],fill='#17604e');text=s[2 if lang=='zh' else 3];font=F[26 if lang=='zh' else 24];lines=wrap(text,1150,font)
 if len(lines)>4:font=F[22];lines=wrap(text,1150,font)
 assert len(lines)<=4,(len(lines),text)
 for j,line in enumerate(lines):d.text((65,577+j*28),line,font=font,fill='#243c59')
 d.rectangle((52,694,52+1176*progress,699),fill='#246bdd');return im

def run(cmd):subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL)
def stamp(sec,sep=','):
 ms=round(sec*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000);return f'{h:02}:{m:02}:{s:02}{sep}{ms:03}'
def main():
 timing=[]
 for lang in ['zh','en']:
  offset=0;subs=[];vtt=['WEBVTT\n'];concat=[]
  for i,s in enumerate(scenes):
   txt=s[2 if lang=='zh' else 3];wav=vo_wav('w13',lang,i,txt,CACHE)
   audio=float(subprocess.check_output(['ffprobe','-v','quiet','-show_entries','format=duration','-of','csv=p=0',str(wav)]));dur=math.ceil((audio+.7)*12)/12;clip=CACHE/f'{lang}-{i}.mp4'
   proc=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r','12','-i','-','-i',str(wav),'-af','apad','-t',str(dur),'-c:v','libx264','-preset','fast','-crf','24','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart',str(clip)],stdin=subprocess.PIPE)
   states=[frame(s,lang,(k+1)/24).tobytes() for k in range(24)]
   for k in range(round(dur*12)):proc.stdin.write(states[min(23,int(k/(dur*12)*24))])
   proc.stdin.close();assert proc.wait()==0;concat.append("file '"+clip.as_posix()+"'");subs.append(f'{i+1}\n{stamp(offset)} --> {stamp(offset+audio)}\n{txt}\n');vtt.append(f'{stamp(offset,".")} --> {stamp(offset+audio,".")}\n{txt}\n');timing.append(dict(lang=lang,scene=i,start=offset,speech_duration=audio,scene_duration=dur));offset+=dur;print(lang,i,'speech',audio,'scene',dur,flush=True)
  lst=CACHE/f'{lang}-concat.txt';lst.write_text('\n'.join(concat));run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(lst),'-c','copy','-movflags','+faststart',str(OUT/f'w13_tour_{lang}.mp4')]);(OUT/f'w13_tour_{lang}.srt').write_text('\n'.join(subs));(OUT/f'w13_tour_{lang}.vtt').write_text('\n'.join(vtt));(OUT/f'narration_{lang}.txt').write_text('\n\n'.join(s[2 if lang=='zh' else 3] for s in scenes));frame(scenes[0],lang,.95).save(OUT/f'poster_{lang}.jpg')
 (OUT/'timing.json').write_text(json.dumps(timing,indent=2))
if __name__=='__main__':main()
