#!/usr/bin/env python3
"""Render W11 bilingual narrated course tours. Requires Pillow/numpy/scipy, ffmpeg,
and Windows System.Speech voices Hanhan/Zira (WSL). Run with Python 3.12+.
Audio intermediates live in HERMES scratch, not in the repository.
"""
from pathlib import Path
import json, subprocess, math, textwrap, os, hashlib
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve
from scipy.signal import savgol_filter, medfilt
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'labs/w11_preprocess_similarity/animations'
CACHE=Path.home()/'.hermes/cache/scratch/w11-render'
OUT.mkdir(parents=True,exist_ok=True); CACHE.mkdir(parents=True,exist_ok=True)
FONT='/home/administrator/.local/share/fonts/hermes-food-tests/msjh.ttc'
if not Path(FONT).exists(): FONT='/mnt/c/Windows/Fonts/msjh.ttc'
scenes=[
('白色粉末，光譜能認出來嗎？','Can spectra identify a white powder?', '本週要用光譜辨認代糖盲樣。先別急著看第一名：背景、散射和強度差異，都可能讓同一物質看起來不一樣。','This week, identify an unknown sweetener using spectra. Do not trust the top match immediately. Background, scattering, and intensity changes can make the same material look different.','raw','先排除量測差異，再比較化學訊號','Remove measurement effects before comparing chemistry'),
('先確認光譜能不能比較','Make spectra comparable first','先確認波數軸、單位與量測模式一致。光譜庫和未知樣品，要用相同的區間與前處理流程；示範曲線是模擬數據，不是實測化合物指紋。','First check the axis, units, and measurement mode. Use the same spectral region and preprocessing for references and unknowns. These curves are simulated teaching data, not measured chemical fingerprints.','raw','相同座標、相同區間、相同流程','Same axis, same region, same pipeline'),
('第一步：辨認異常尖峰','Step 1: inspect isolated spikes','拉曼光譜的單點突刺可能是宇宙射線。中值濾波可協助找出異常，但真正的窄峰也可能被誤刪。先看重複掃描，再決定是否修正。','An isolated Raman spike may be a cosmic ray. A median filter can help detect it, but a real narrow peak can also be erased. Inspect replicate scans before correcting suspicious points.','despike','突刺不是都能刪：先看重複掃描','Do not erase every sharp peak; check replicates'),
('第二步：ALS 扣除寬廣基線','Step 2: remove broad baseline with ALS','不對稱最小平方法，用平滑曲線估計背景。lambda 控制平滑度，p 控制不對稱權重。課堂從一百萬與零點零一開始，但不能把預設值當成通用答案。','Asymmetric least squares estimates a smooth background. Lambda controls smoothness and p controls asymmetric weights. Start with one million and zero point zero one, but these are starting values, not universal settings.','als','ALS 起點：lambda=1e6，p=0.01','ALS starting point: lambda=1e6, p=0.01'),
('第三步：SNV 校正平移與縮放','Step 3: SNV removes offset and scaling','SNV 將每條光譜減去自己的平均，再除以自己的母體標準差。同一形狀若只是正倍數縮放與常數平移，處理後會重合；但任意彎曲的背景不會自動消失。','SNV subtracts each spectrum\'s own mean and divides by its population standard deviation. Positive scaling and constant offsets then disappear. An arbitrary curved background does not.','snv','SNV = (y - mean) / population SD','SNV = (y - mean) / population SD'),
('第四步：SG 平滑與導數','Step 4: SG smoothing and derivatives','SG 在滑動視窗內擬合多項式。導數能凸顯重疊峰，也會放大雜訊。比較不同視窗，保留有意義的峰形；導數計算必須使用實際的波長或波數間距。','Savitzky Golay fits a polynomial inside a moving window. Derivatives reveal overlapping features but can amplify noise. Compare window sizes, preserve meaningful peaks, and use the actual axis spacing when computing derivatives.','sg','視窗太寬會失去細節；太窄難抑制雜訊','Wide windows lose detail; narrow windows retain noise'),
('第五步：選對相似度指標','Step 5: choose a similarity metric','Pearson 看去平均後的形狀，餘弦看向量方向，光譜角越小越相似。原始歐氏距離對尺度敏感。注意：餘弦不怕正倍數縮放，卻仍會受常數平移影響。','Pearson compares centered shapes. Cosine compares vector directions, and smaller spectral angles mean closer directions. Raw Euclidean distance is scale sensitive. Cosine ignores positive scaling, but remains sensitive to offsets.','metrics','r / cosine 越大越像；SAM / 距離越小越像','Higher r / cosine; lower SAM / distance'),
('第六步：回報 top-3 與不確定性','Step 6: report top three and uncertainty','同時呈現前三名與疊圖，檢查特徵峰和前兩名的差距。高分不是身分證，沒有通用的相似度門檻。混合物可能只配到主要成分，必須補量測或做其他確認。','Report the top three candidates and overlay their spectra. Check diagnostic features and the gap between the leading matches. A high score is not proof of identity. No universal threshold applies, and mixtures may match only their dominant component.','library','高分不等於確認；混合物尤其要小心','A high score is not confirmation, especially for mixtures'),
('六幕互動：先預測，再操作','Six interactive acts: predict, then test','打開互動實驗室，依序調整尖峰、基線、散射與 SG 參數，再改變指標與盲樣。每幕先預測、後觀察並解釋。下載光譜與實驗紀錄，記下你選擇參數的理由。','Open the interactive lab. Explore spikes, baseline, scattering, and SG settings, then change the metric and unknown sample. Predict before observing, explain the result, and download spectra and your experiment record with parameter choices.','workflow','預測 > 操作 > 觀察 > 解釋 > 記錄','Predict > operate > observe > explain > record'),
('帶著證據完成本週任務','Finish this week with evidence','用本班第十週量到的純物質建立光譜庫。繳交前處理參數、前三名分數、疊圖及模糊案例討論。若做 NNLS，正規化後的係數不能直接當成質量分率。','Build a reference library from your week ten measurements. Submit preprocessing settings, top three scores, overlays, and a discussion of an ambiguous case. For NNLS, coefficients after normalization are not automatically mass fractions.','workflow','交付：參數、top-3、疊圖、模糊案例','Submit: settings, top three, overlays, ambiguous case')]
(OUT/'storyboard.json').write_text(json.dumps([dict(zip(['title_zh','title_en','narration_zh','narration_en','visual','takeaway_zh','takeaway_en'],s)) for s in scenes],ensure_ascii=False,indent=2))
x=np.linspace(400,1800,281); t=(x-400)/1400
p=np.exp(-.5*((x-780)/24)**2)+.72*np.exp(-.5*((x-1100)/38)**2)+.85*np.exp(-.5*((x-1510)/30)**2)
b=.25+.6*np.sin(t*np.pi)+.15*t
rng=np.random.default_rng(11); raw=p+b+rng.normal(0,.012,len(x)); raw[60]+=1.3
clean=raw.copy(); clean[60]=np.median(raw[57:64])
D=sparse.diags([np.ones(len(x)-2),-2*np.ones(len(x)-2),np.ones(len(x)-2)],[0,1,2],shape=(len(x)-2,len(x)))
w=np.ones(len(x))
for _ in range(12):
  z=spsolve((sparse.diags(w)+1e6*(D.T@D)).tocsc(),w*clean); w=np.where(clean>z,.01,.99)
corrected=clean-z
FONTS={sz:ImageFont.truetype(FONT,sz) for sz in [20,22,24,26,28,30,34,40,44]}
def wrap(s,width,font):
 lines=[]; line=''
 # Preserve English words; CJK text wraps at character boundaries.
 words=s.split(' ') if all(ord(c)<128 for c in s) else list(s)
 joiner=' ' if all(ord(c)<128 for c in s) else ''
 for word in words:
  candidate=line+joiner+word if line else word
  if line and font.getlength(candidate)>width:
   lines.append(line.rstrip()); line=word
  else: line=candidate
 if line: lines.append(line.rstrip())
 return lines

def frame(scene,lang,progress):
 title=scene[0 if lang=='zh' else 1]; narration=scene[2 if lang=='zh' else 3]; typ=scene[4]; takeaway=scene[5 if lang=='zh' else 6]
 im=Image.new('RGB',(1280,720),'#edf6ff'); d=ImageDraw.Draw(im)
 d.rounded_rectangle((24,18,1256,702),radius=24,fill='white')
 d.text((52,34),'FOOD ANALYSIS LAB / W11 / '+('課前導覽' if lang=='zh' else 'COURSE TOUR'),font=FONTS[22],fill='#2670bf')
 titlelines=wrap(title,1170,FONTS[40]);
 for i,line in enumerate(titlelines): d.text((52,77+i*46),line,font=FONTS[40],fill='#173453')
 colors=['#246bdd','#e88326','#129b83']
 def plot(arrays,labels):
  left,top,right,bot=82,202,1190,445
  lo=min(float(np.min(a)) for a in arrays); hi=max(float(np.max(a)) for a in arrays); pad=(hi-lo)*.1 or .1;lo-=pad;hi+=pad
  for k in range(5):
   yy=top+k*(bot-top)/4;d.line((left,yy,right,yy),fill='#e1eaf4',width=1);d.text((35,yy-10),f'{hi-k*(hi-lo)/4:.1f}',font=FONTS[20],fill='#63758a')
  d.line((left,top,left,bot,right,bot),fill='#6e8298',width=2)
  for a,c,label in zip(arrays,colors,labels):
   pts=[(left+j*(right-left)/(len(a)-1),bot-(float(y)-lo)/(hi-lo)*(bot-top)) for j,y in enumerate(a)]
   n=max(2,int(len(pts)*progress)); d.line(pts[:n],fill=c,width=3)
  for j,label in enumerate(labels): d.text((85+j*360,165),label,font=FONTS[22],fill=colors[j])
  for val in [400,800,1200,1800]:d.text((left+(val-400)/1400*(right-left)-20,450),str(val),font=FONTS[20],fill='#63758a')
  d.text((870,478),'Raman shift (cm-1)',font=FONTS[22],fill='#63758a')
  d.text((80,478),'模擬光譜 / SIMULATED' ,font=FONTS[20],fill='#63758a')
 if typ=='raw':plot([raw,p,b],['原始 / Raw','訊號 / Signal','背景 / Baseline'])
 elif typ=='despike':plot([raw,clean],['原始 / Raw','修正 / Despiked'])
 elif typ=='als':plot([clean,z,corrected],['原始 / Raw','ALS baseline','扣基線 / Corrected'])
 elif typ=='snv':
  a=2*p+.4; c=.7*p-.2
  if progress<.5:plot([p,a,c],['原始 / Raw 1','原始 / Raw 2','原始 / Raw 3'])
  else: plot([(v-v.mean())/v.std() for v in [p,a,c]],['SNV 1','SNV 2','SNV 3'])
 elif typ=='sg':plot([savgol_filter(clean-z,15,2,deriv=2,delta=5),savgol_filter(clean-z,5,2,deriv=2,delta=5)],['SG 15 / second derivative','SG 5 / second derivative'])
 elif typ in ['metrics','library','workflow']:
  if typ=='metrics': cards=[('Pearson r','平移與縮放不敏感' if lang=='zh' else 'Offset / scale invariant'),('cosine / SAM','縮放不敏感；平移敏感' if lang=='zh' else 'Scale invariant; offset sensitive'),('Euclidean','原始距離對尺度敏感' if lang=='zh' else 'Raw distance is scale sensitive')]
  elif typ=='library':cards=[('01 / TOP 1','比對特徵峰' if lang=='zh' else 'Check diagnostic features'),('02 / TOP 2','檢查排名差距' if lang=='zh' else 'Check the ranking gap'),('03 / TOP 3','考慮混合物與庫外樣品' if lang=='zh' else 'Consider mixtures / missing references')]
  else:cards=[('01 / PREPROCESS','尖峰、ALS、SNV、SG' if lang=='zh' else 'Spikes, ALS, SNV, SG'),('02 / COMPARE','相同流程、top-3、疊圖' if lang=='zh' else 'Same pipeline, top three, overlays'),('03 / EXPLAIN','預測、證據、不確定性' if lang=='zh' else 'Prediction, evidence, uncertainty')]
  for j,(a,c) in enumerate(cards):
   yy=180+j*103;d.rounded_rectangle((65,yy,1215,yy+87),radius=13,fill='#eaf3ff');d.text((88,yy+15),a,font=FONTS[30],fill=colors[j]); d.text((430,yy+24),c,font=FONTS[26],fill='#173453')
 d.rounded_rectangle((52,518,1228,565),radius=10,fill='#e7f6f1');d.text((68,526),takeaway,font=FONTS[24],fill='#17604e')
 # Complete narration is visible, wrapped in the caption-safe region.
 f=FONTS[26 if lang=='zh' else 24]; lines=wrap(narration,1150,f)
 if len(lines)>4: f=FONTS[22];lines=wrap(narration,1150,f)
 assert len(lines)<=4,(len(lines),narration)
 for j,line in enumerate(lines):d.text((65,577+j*28),line,font=f,fill='#243c59')
 d.rectangle((52,694,52+1176*progress,699),fill='#246bdd')
 return im

def run(cmd):subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL)
def stamp(sec,sep=','):
 ms=round(sec*1000); h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000);return f'{h:02}:{m:02}:{s:02}{sep}{ms:03}'

def main():
 manifest=[]
 for lang,voice in [('zh','Microsoft Hanhan Desktop'),('en','Microsoft Zira Desktop')]:
  subs=[]; vtt=['WEBVTT\n']; offset=0; concat=[]
  for i,s in enumerate(scenes):
   text=s[2 if lang=='zh' else 3]; wav=CACHE/f'{lang}-{i}.wav'; txt=CACHE/f'{lang}-{i}.txt'
   signature=CACHE/f'{lang}-{i}.sha256'; digest=hashlib.sha256((voice+'\n'+text).encode()).hexdigest()
   valid=signature.exists() and signature.read_text()==digest
   txt.write_text(text,encoding='utf-8-sig')
   def winpath(p):return subprocess.check_output(['wslpath','-w',str(p)],text=True).strip()
   if not wav.exists() or not valid:
    ps=f"Add-Type -AssemblyName System.Speech; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.SelectVoice('{voice}'); $s.Rate=0; $s.SetOutputToWaveFile('{winpath(wav)}'); $s.Speak([System.IO.File]::ReadAllText('{winpath(txt)}')); $s.Dispose()"
    run(['powershell.exe','-NoProfile','-Command',ps]); signature.write_text(digest)
   audio=float(subprocess.check_output(['ffprobe','-v','quiet','-show_entries','format=duration','-of','csv=p=0',str(wav)]));dur=math.ceil((audio+.7)*12)/12
   clip=CACHE/f'{lang}-{i}.mp4'
   cmd=['ffmpeg','-y','-v','error','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r','12','-i','-','-i',str(wav),'-af','apad','-t',str(dur),'-c:v','libx264','-preset','fast','-crf','24','-pix_fmt','yuv420p','-c:a','aac','-b:a','96k','-movflags','+faststart',str(clip)]
   proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
   # Cache 24 draw states: motion is a graph reveal, not a static slide export.
   states=[frame(s,lang,(k+1)/24).tobytes() for k in range(24)]
   for k in range(round(dur*12)):proc.stdin.write(states[min(23,int(k/(dur*12)*24))])
   proc.stdin.close();assert proc.wait()==0
   concat.append("file '"+str(clip)+"'")
   subs.append(f'{i+1}\n{stamp(offset)} --> {stamp(offset+audio)}\n{text}\n')
   vtt.append(f'{stamp(offset,".")} --> {stamp(offset+audio,".")}\n{text}\n')
   frame(s,lang,.75).save(CACHE/f'{lang}-scene-{i}.jpg')
   manifest.append(dict(lang=lang,scene=i,start=offset,speech_duration=audio,scene_duration=dur));offset+=dur
   print(lang,i,'audio',audio,'duration',dur,flush=True)
  lst=CACHE/f'{lang}-concat.txt';lst.write_text('\n'.join(concat))
  dest=OUT/f'w11_tour_{lang}.mp4';run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(lst),'-c','copy','-movflags','+faststart',str(dest)])
  (OUT/f'w11_tour_{lang}.srt').write_text('\n'.join(subs));(OUT/f'w11_tour_{lang}.vtt').write_text('\n'.join(vtt))
  frame(scenes[0],lang,.85).save(OUT/f'poster_{lang}.jpg')
  (OUT/f'narration_{lang}.txt').write_text('\n\n'.join(s[2 if lang=='zh' else 3] for s in scenes))
 (OUT/'timing.json').write_text(json.dumps(manifest,indent=2))
 # A contact sheet covering every scene in both language versions.
 sheet=Image.new('RGB',(1280,720*5))
 for i in range(10):
  for j,lang in enumerate(['zh','en']):
   im=Image.open(CACHE/f'{lang}-scene-{i}.jpg');im.thumbnail((640,360));sheet.paste(im,(j*640,i*360))
 sheet.save(CACHE/'contact.jpg')
if __name__=='__main__':main()
