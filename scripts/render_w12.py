#!/usr/bin/env python3
"""Render bilingual W12 PCA tours from the exact course demonstration CSV.
Requires Python/Pillow/NumPy, ffmpeg/ffprobe and ElevenLabs takes in scripts/vo/ (voice IAN, eleven_v3).
"""
from pathlib import Path
import csv,json,math,subprocess,hashlib
import numpy as np
import sys;sys.path.insert(0,str(Path(__file__).resolve().parent))
from course_video_common import vo_wav,cache_dir
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'labs/w12_pca/animations';CACHE=cache_dir('w12')
OUT.mkdir(exist_ok=True,parents=True);CACHE.mkdir(exist_ok=True,parents=True)
FONT=Path('/home/administrator/.local/share/fonts/hermes-food-tests/msjh.ttc')
if not FONT.exists():FONT=Path('/mnt/c/Windows/Fonts/msjh.ttc')
if not FONT.exists():FONT=Path('C:/Windows/Fonts/msjh.ttc')
F={n:ImageFont.truetype(str(FONT),n) for n in [18,20,22,24,26,28,30,34,40]}
rows=list(csv.reader((ROOT/'data/nb10_demo_spectra.csv').open()));axis=np.array(list(map(float,rows[0][6:])));X=np.array([list(map(float,r[6:])) for r in rows[1:]]);ids=[r[0] for r in rows[1:]];groups=[r[4] for r in rows[1:]];unique=list(dict.fromkeys(groups));colors=['#1e70cb','#e68023','#139885','#9a50b6','#cd4e68','#697b13'];col={g:colors[i] for i,g in enumerate(unique)}
def pca(x):
 mean=x.mean(0);u,s,v=np.linalg.svd(x-mean,full_matrices=False)
 for k in range(len(s)):
  if v[k,np.argmax(abs(v[k]))]<0:v[k]*=-1;u[:,k]*=-1
 return dict(mean=mean,scores=u*s,loadings=v,eigenvalues=s*s/(len(x)-1),ratio=s*s/(s*s).sum()*100)
full=pca(X);mask=np.array([s!='PEA_r3' for s in ids]);clean=pca(X[mask]);outidx=ids.index('PEA_r3');share=full['scores'][outidx,1]**2/(full['scores'][:,1]**2).sum()*100
scenes=[
['貼錯標籤的油，PCA 看得出來嗎？','Can PCA spot a mislabeled oil?', '一瓶標成橄欖油的樣品，真的是橄欖油嗎？本週用光譜與主成分分析找線索。但分群漂亮不等於證明真偽，還要檢查前處理、特徵波段與量測品質。','Is a bottle labeled olive oil really olive oil? This week, explore spectra with principal component analysis. Clear clusters are clues, not proof of authenticity. Check preprocessing, spectral features, and measurement quality.','spectra','PCA 是探索工具，不是真偽認證','PCA explores variation; it does not certify authenticity'],
['先看懂 X：18 個樣品 × 60 個波數','Read X: 18 samples by 60 spectral variables','本課資料有六種油，每種三次重複，共十八條光譜。每列是一個樣品，每欄是一個波數。導覽與互動實驗共用原課程的模擬資料，不是實際食品檢驗結果。','The course dataset has six oils with three replicates each: eighteen spectra and sixty spectral variables. Rows are samples and columns are wavenumbers. Both this tour and the interactive lab use the original simulated course data, not laboratory test results.','matrix','一列一樣品，一欄一波數；資料為教學模擬','One sample per row, one variable per column; simulated data'],
['轉動投影方向：尋找最大變異','Rotate the projection: find maximum variance','先只看兩個波數，轉動投影方向。點雲投影越分散，代表保留的變異越多。PCA 找出最大變異的第一方向，再找與它垂直的第二方向；計算過程不使用油品標籤。','Start with two spectral variables and rotate the projection. A more spread-out projection preserves more variance. PCA finds the first direction of maximum variance, then an orthogonal second direction. Oil labels are not used to fit the model.','projection','PCA 不看類別標籤；顏色只是協助判讀','Labels color the plot; they do not train PCA'],
['中心化與 autoscale，不是同一件事','Centering and autoscaling are different','中心化是每個波數減去所有樣品在這一欄的平均。autoscale 還要再除以該欄的樣本標準差。本課預設只中心化，避免把低變異雜訊抬高成同樣重要；是否縮放仍要看分析目的。','Centering subtracts each variable\'s mean across samples. Autoscaling also divides by that variable\'s sample standard deviation. This lesson starts with centering only, so low-variance noise is not automatically given equal weight. Scaling remains a choice tied to the analytical objective.','scaling','中心化按欄；SNV 按列，兩者不要混淆','Centering acts by column; SNV acts by spectrum'],
['Scores：樣品在新座標的位置','Scores: sample positions in new coordinates','分數圖上的一點就是一條光譜。同色三點代表同一種油的重複，先看它們是否靠近。選擇不同主成分可能改變看到的分離；兩群重疊，也不代表原始光譜完全相同。','Each point in the score plot is a spectrum. Three points of the same color are replicate measurements of one oil; check their consistency first. Changing the displayed components changes the view. Overlapping groups do not necessarily have identical spectra.','scores','Scores 看樣品；重複性先於分群故事','Scores describe samples; inspect replicates before clusters'],
['Loadings：哪些波數驅動分離','Loadings: which variables drive separation','loading 是每個波數的權重。中心化光譜乘上這些權重再加總，就是 score。必須一起看原始光譜、loading 與量測紀錄。整個主成分的正負號可同時翻轉，並不改變科學結論。','Loadings are the weights on spectral variables. Multiply the centered spectrum by those weights and sum to obtain a score. Interpret loadings together with raw spectra and measurement records. Flipping a component\'s scores and loadings together does not change the result.','loadings','Score = centered spectrum dot loading；正負號可整體翻轉','Score = centered spectrum dot loading; signs are arbitrary'],
['解釋變異，不是分類正確率','Explained variance is not classification accuracy','這份模擬資料的前三個主成分，分別解釋約四十六點三、二十八點三與二十三點零百分比。合計約九十七點七，代表保留大多數變異，不是辨認油品有九十七點七的正確率。','For this simulated dataset, the first three components explain about forty-six point three, twenty-eight point three, and twenty-three point zero percent. Together they retain about ninety-seven point seven percent of variance. That is not classification accuracy.','scree','解釋變異看資料壓縮；不能當成辨識準確度','Variance retention measures compression, not accuracy'],
['警訊：一個離群點綁架 PC2','Warning: one outlier dominates PC2','含全部樣品時，花生油第三次重複，貢獻了約百分之七十四的 PC2 分數平方和。PC2 最大 loading 落在約一一五九波數附近。先回頭查原始光譜，不能把量測異常講成油品的化學特徵。','With all samples included, the third peanut-oil replicate contributes about seventy-four percent of the PC2 score sum of squares. Its largest loading is near eleven fifty-nine inverse centimeters. Inspect the raw spectrum before treating an artifact as an oil characteristic.','outlier','PEA_r3：先查光譜與紀錄，不要直接刪點','PEA_r3: inspect spectra and records before exclusion'],
['有理由才排除，然後重新 fit','Document a reason, then refit','本教學案例確認了人工加入的量測異常後，才排除花生油第三次重複並重做 PCA。新的 PC1 與 PC2 約為六十三點五與三十三點二百分比。PC2 權重主峰改到約一五二五，說明原本的故事真的改變了。','In this teaching case, exclude the third peanut replicate only after documenting its injected measurement artifact, then fit PCA again. The new PC1 and PC2 explain about sixty-three point five and thirty-three point two percent. The dominant PC2 loading shifts near fifteen twenty-five inverse centimeters.','refit','重新 fit 才是比較；不能只把圖上的點藏起來','Refit the model; do not merely hide the plotted point'],
['Orange 與 Colab：走同一條分析路徑','Orange and Colab: follow the same reasoning','在 Orange 將油品設為類別，波數欄設為特徵。PCA 取消 Normalize variables，用 Data 輸出接分數圖，Components 接 Spectra 看 loading。進階使用者可開啟 NB10，比較中心化、前處理與離群點重算結果。','In Orange, use oil type as the target and wavenumber columns as features. Turn off Normalize variables in PCA. Connect its Data output to the score plot and Components to Spectra for loadings. Advanced users can reproduce preprocessing and outlier comparisons in notebook NB10.','workflow','PCA Data > Scatter Plot；Components > Spectra','PCA Data > Scatter Plot; Components > Spectra'],
['帶著四份證據完成 W12','Finish W12 with four pieces of evidence','進入六幕互動實驗，先預測，再操作與解釋。最後交出分數圖、loading 與約略波段指認、解釋變異，以及離群點重算前後比較。正式作業請換成全班實測資料，並保留排除理由。','Enter the six-act interactive lab: predict, operate, and explain. Submit a score plot, loadings with tentative band assignments, explained variance, and an outlier comparison before and after refitting. For the assignment, use class measurements and retain the reason for every exclusion.','workflow','交付：scores、loadings、變異、QC 前後比較','Submit: scores, loadings, variance, and a QC comparison']]
(OUT/'storyboard.json').write_text(json.dumps([dict(zip(['title_zh','title_en','narration_zh','narration_en','visual','takeaway_zh','takeaway_en'],s)) for s in scenes],ensure_ascii=False,indent=2))
(OUT/'pca-reference.json').write_text(json.dumps({'source':'data/nb10_demo_spectra.csv','sha256':hashlib.sha256((ROOT/'data/nb10_demo_spectra.csv').read_bytes()).hexdigest(),'full_explained_percent':full['ratio'].tolist(),'refit_explained_percent':clean['ratio'].tolist(),'PEA_r3_PC2_sum_squares_percent':share,'full_PC2_maxabs_wavenumber':float(axis[np.argmax(abs(full['loadings'][1]))]),'refit_PC2_maxabs_wavenumber':float(axis[np.argmax(abs(clean['loadings'][1]))])},indent=2))
def wrap(text,width,font):
 words=text.split(' ') if all(ord(c)<128 for c in text) else list(text);sep=' ' if all(ord(c)<128 for c in text) else '';lines=[];line=''
 for w in words:
  s=line+sep+w if line else w
  if line and font.getlength(s)>width:lines.append(line);line=w
  else:line=s
 if line:lines.append(line)
 return lines

def frame(s,lang,progress):
 im=Image.new('RGB',(1280,720),'#edf6ff');d=ImageDraw.Draw(im);d.rounded_rectangle((24,18,1256,702),radius=24,fill='white')
 d.text((52,32),'FOOD ANALYSIS LAB / W12 / PCA',font=F[22],fill='#246bb2')
 for j,line in enumerate(wrap(s[0 if lang=='zh' else 1],1170,F[40])):d.text((52,75+j*46),line,font=F[40],fill='#173653')
 typ=s[4]
 def lineplot(arrays,labels,units='Raman shift (cm-1)',xs=axis):
  L,T,R,B=85,205,1180,445;lo=min(float(np.min(a)) for a in arrays);hi=max(float(np.max(a)) for a in arrays);pad=(hi-lo)*.1 or .1;lo-=pad;hi+=pad
  for j in range(5):
   y=T+j*(B-T)/4;d.line((L,y,R,y),fill='#e0eaf5');d.text((30,y-10),f'{hi-j*(hi-lo)/4:.2f}',font=F[18],fill='#62788c')
  for j,(a,label) in enumerate(zip(arrays,labels)):
   c=colors[j%6];d.text((85+j*355,167),label,font=F[22],fill=c);pts=[(L+k*(R-L)/(len(a)-1),B-(v-lo)/(hi-lo)*(B-T)) for k,v in enumerate(a)];d.line(pts[:max(2,int(len(pts)*progress))],fill=c,width=3)
  for k in [0,len(xs)//3,2*len(xs)//3,len(xs)-1]:d.text((L+k*(R-L)/(len(xs)-1)-20,451),str(round(xs[k])),font=F[20],fill='#62788c')
  d.text((835,480),units,font=F[20],fill='#62788c')
 def scatter(model,selected=False,subset=mask):
  scores=model['scores'];g=groups if len(scores)==18 else [v for v,keep in zip(groups,subset) if keep];L,T,R,B=100,205,1150,443
  xx=scores[:,0];yy=scores[:,1];xmin,xmax=xx.min()-.4,xx.max()+.4;ymin,ymax=yy.min()-.4,yy.max()+.4
  d.line((L,T,L,B,R,B),fill='#7490a8',width=2)
  for i,(a,b) in enumerate(zip(xx,yy)):
   px=L+(a-xmin)/(xmax-xmin)*(R-L);py=B-(b-ymin)/(ymax-ymin)*(B-T);rad=7 if not selected or i!=outidx else 12
   d.ellipse((px-rad,py-rad,px+rad,py+rad),fill=col[g[i]])
   if selected and i==outidx:d.text((px-105,py-33),'PEA_r3',font=F[24],fill='#a03737')
  for j,grp in enumerate(unique):d.text((85+j*185,164),grp,font=F[22],fill=col[grp])
  d.text((850,465),f"PC1 {model['ratio'][0]:.1f}%",font=F[24],fill='#173653');d.text((92,470),f"PC2 {model['ratio'][1]:.1f}%",font=F[24],fill='#173653')
 if typ=='spectra':lineplot([X[0],X[6],X[12]],['EVOO_r1','SOY_r1','COC_r1'])
 elif typ=='matrix':
  d.text((70,165),'18 SAMPLES  x  60 VARIABLES',font=F[30],fill='#246bb2')
  for i in range(7):
   d.text((72,215+i*37),ids[i],font=F[22],fill='#173653')
   for j in range(9):
    v=X[i,j+20];c=(int(238-v*100),int(247-v*55),255);d.rounded_rectangle((245+j*100,210+i*37,338+j*100,242+i*37),radius=4,fill=c);d.text((252+j*100,213+i*37),f'{v:.2f}',font=F[18],fill='#173653')
  d.text((280,480),'Rows = samples / Columns = spectral variables',font=F[24],fill='#62788c')
 elif typ=='projection':
  Z=X[:,[24,49]];Z=Z-Z.mean(0);Z=Z/np.max(abs(Z));angle=progress*math.pi;vec=np.array([math.cos(angle),math.sin(angle)]);L,T,R,B=340,200,890,470;cx,cy=615,335
  d.line((L,cy,R,cy),fill='#cbdceb');d.line((cx,T,cx,B),fill='#cbdceb')
  for v,g in zip(Z,groups):
   px=cx+v[0]*240;py=cy-v[1]*120;d.ellipse((px-6,py-6,px+6,py+6),fill=col[g]);u=np.dot(v,vec)*vec;qx=cx+u[0]*240;qy=cy-u[1]*120;d.line((px,py,qx,qy),fill='#aec2d6')
  d.line((cx-vec[0]*265,cy+vec[1]*132,cx+vec[0]*265,cy-vec[1]*132),fill='#e68023',width=4)
  d.text((75,165),'1266 & 1647 cm-1 / 2-variable projection',font=F[26],fill='#246bb2');d.text((75,480),'Exploration only / not the full 60-variable PCA',font=F[22],fill='#62788c')
 elif typ=='scaling':
  cards=[('MEAN CENTER','x - column mean','每欄平均變成 0' if lang=='zh' else 'Each column has mean zero'),('AUTOSCALE','(x - mean) / sample SD','低變異欄位也變成單位變異' if lang=='zh' else 'Low-variance columns gain unit variance'),('SNV','(spectrum - mean) / SD','每條光譜內標準化，與中心化不同' if lang=='zh' else 'Within-spectrum scaling, not column centering')]
  for j,(a,b,c) in enumerate(cards):
   y=175+j*105;d.rounded_rectangle((65,y,1215,y+92),radius=12,fill='#eaf3ff');d.text((85,y+10),a,font=F[26],fill=colors[j]);d.text((410,y+9),b,font=F[26],fill='#173653');d.text((410,y+48),c,font=F[22],fill='#62788c')
 elif typ=='scores':scatter(full)
 elif typ=='outlier':scatter(full,True)
 elif typ=='refit':
  scatter(clean);d.text((390,494),'18 samples > document > refit 17 samples',font=F[18],fill='#62788c')
 elif typ=='loadings':lineplot([full['loadings'][0],full['loadings'][1]],['PC1 loading','PC2 loading'])
 elif typ=='scree':
  for j,v in enumerate(full['ratio'][:5]):
   x=110+j*220;top=440-v/50*220*progress;d.rounded_rectangle((x,top,x+135,440),radius=8,fill=colors[j]);d.text((x+15,top-36),f'{v:.1f}%',font=F[26],fill='#173653');d.text((x+35,455),f'PC{j+1}',font=F[24],fill='#62788c')
  d.text((85,165),'Explained variance / NOT classification accuracy',font=F[26],fill='#246bb2')
 elif typ=='workflow':
  cs=[('01 / DATA','六種油 × 3 重複' if lang=='zh' else 'Six oils x three replicates'),('02 / PCA','中心化 > scores / loadings / scree' if lang=='zh' else 'Center > scores / loadings / scree'),('03 / QC','查光譜 > 記錄理由 > 重新 fit' if lang=='zh' else 'Inspect > document > refit')]
  for j,(a,b) in enumerate(cs):
   y=180+j*105;d.rounded_rectangle((65,y,1215,y+85),radius=12,fill='#eaf3ff');d.text((85,y+19),a,font=F[30],fill=colors[j]);d.text((400,y+24),b,font=F[26],fill='#173653')
 d.rounded_rectangle((52,518,1228,565),radius=10,fill='#e7f6f1');take=s[5 if lang=='zh' else 6];d.text((68,528),take,font=F[24],fill='#17604e')
 narration=s[2 if lang=='zh' else 3];font=F[26 if lang=='zh' else 24];lines=wrap(narration,1150,font)
 if len(lines)>4:font=F[22];lines=wrap(narration,1150,font)
 assert len(lines)<=4,(len(lines),narration)
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
   txt=s[2 if lang=='zh' else 3];wav=vo_wav('w12',lang,i,txt,CACHE)
   audio=float(subprocess.check_output(['ffprobe','-v','quiet','-show_entries','format=duration','-of','csv=p=0',str(wav)]));dur=math.ceil((audio+.7)*12)/12;clip=CACHE/f'{lang}-{i}.mp4'
   proc=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r','12','-i','-','-i',str(wav),'-af','apad','-t',str(dur),'-c:v','libx264','-preset','fast','-crf','24','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart',str(clip)],stdin=subprocess.PIPE)
   states=[frame(s,lang,(k+1)/24).tobytes() for k in range(24)]
   for k in range(round(dur*12)):proc.stdin.write(states[min(23,int(k/(dur*12)*24))])
   proc.stdin.close();assert proc.wait()==0;concat.append("file '"+clip.as_posix()+"'");subs.append(f'{i+1}\n{stamp(offset)} --> {stamp(offset+audio)}\n{txt}\n');vtt.append(f'{stamp(offset,".")} --> {stamp(offset+audio,".")}\n{txt}\n');timing.append(dict(lang=lang,scene=i,start=offset,speech_duration=audio,scene_duration=dur));offset+=dur;print(lang,i,'speech',audio,'scene',dur,flush=True)
  lst=CACHE/f'{lang}-concat.txt';lst.write_text('\n'.join(concat));run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(lst),'-c','copy','-movflags','+faststart',str(OUT/f'w12_tour_{lang}.mp4')]);(OUT/f'w12_tour_{lang}.srt').write_text('\n'.join(subs));(OUT/f'w12_tour_{lang}.vtt').write_text('\n'.join(vtt));(OUT/f'narration_{lang}.txt').write_text('\n\n'.join(s[2 if lang=='zh' else 3] for s in scenes));frame(scenes[0],lang,.95).save(OUT/f'poster_{lang}.jpg')
 (OUT/'timing.json').write_text(json.dumps(timing,indent=2))
if __name__=='__main__':main()
