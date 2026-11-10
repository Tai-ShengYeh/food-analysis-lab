#!/usr/bin/env python3
"""W15 bilingual preparation/QC tours. NB13 calibration design, no blind truths exported."""
from pathlib import Path
import csv,json,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from course_video_common import render,cache_dir
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'labs/w15_sweetener_prep/animations';OUT.mkdir(exist_ok=True,parents=True)
source=ROOT/'data/nb13_demo_spectra.csv';rows=list(csv.DictReader(source.open()));unique={r['sample_id']:r for r in rows if r['split']=='calibration'};design=[]
for sid,r in sorted(unique.items()):
 a=float(r['aspartame_pct']);s=float(r['sucralose_pct']);i=int(round(a/2.5));j=int(round(s/2.5));design.append(dict(sample_id=sid,aspartame_pct=a,sucralose_pct=s,erythritol_pct=float(r['erythritol_pct']),preparation_group=f'G{(j-i)%5+1}'))
A=np.array([r['aspartame_pct'] for r in design]);S=np.array([r['sucralose_pct'] for r in design]);corr=float(np.corrcoef(A,S)[0,1]);rank=int(np.linalg.matrix_rank(np.column_stack([np.ones(25),A,S])));m=np.array([.1523,.0997,1.7489]);total=float(m.sum());fractions=100*m/total;u=.0001/np.sqrt(3);J=100*(np.eye(3)*total-m[:,None])/total**2;uf=np.sqrt((J*J).sum(1))*u;qc5=np.array([102,98,105,95,100]);qc2=np.array([102,98]);sd5=float(qc5.std(ddof=1));sd2=float(qc2.std(ddof=1))
# Source-calibration-only data for the student bundle; never export NB13 blind labels.
with (OUT/'calibration-design.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(design[0]),lineterminator='\n');w.writeheader();w.writerows(design)
reference=dict(source='data/nb13_demo_spectra.csv',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),calibration_design=design,corr_AS=corr,design_rank_with_intercept=rank,actual_masses_g=m.tolist(),actual_total_g=total,actual_fractions_pct=fractions.tolist(),balance_half_width_mg=.1,assumed_rectangular_u_mg=float(u*1000),mass_relative_u_pct=(u/m*100).tolist(),fraction_u_pct_points=uf.tolist(),QC_example5=dict(values=qc5.tolist(),sample_SD=sd5,RSD_pct=sd5/100*100),QC_example2=dict(values=qc2.tolist(),sample_SD=sd2,RSD_pct=sd2/100*100),schedule=dict(bottles=32,stations=6,reloads=2,files=32*6*2,files_per_station=64,rack_sizes=[6,6,5,5,5,5],scan_minutes=1.5,reference_minutes_per_round=1,rounds=6,round_minutes=19,lockstep_minutes=114,per_station_work_minutes=102,available_minutes=115),blind_labels='withheld; IDs only BLIND-00..BLIND-06')
(OUT/'preparation-reference.json').write_text(json.dumps(reference,indent=2))
scenes=[
['先配對、量好，下一週模型才學得好','Good calibration starts before model fitting','包裝寫有阿斯巴甜或三氯蔗糖，不一定公開各自含量。本週不是先跑 PLS，而是設計並配製可靠的校正樣品，量好光譜、保留紀錄；第十六週才用這些資料建模。','A sweetener label may not disclose each ingredient\'s amount. This week is not about fitting PLS first. Design and prepare reliable calibration samples, collect spectra, and retain records. Modeling follows in week sixteen.','workflow','W15：設計、配製、量測與 QC；W16 才建模','W15: design, prepare, measure, QC; fit models in W16'],
['固體粉末路線，先確認可行性','Choose the powder route after checking feasibility','本課採固體混合粉末，避免溶解度與低濃度訊號不足的限制。但可不可以測到，仍取決於儀器、量測配置與方法的偵測能力。正式開做前，要由 TA 用空白與低濃度樣品確認可行性，不能把教材假設當成已完成的實測。','This course uses solid blends to address solubility and weak low-concentration signals. Feasibility still depends on the instrument, geometry, and method detection capability. Before starting, have the TA verify blanks and low-level samples. A teaching assumption is not evidence that a real pilot was performed.','feasibility','不預設通用 LOD；先確認本台儀器與量測配置','No universal LOD assumed; verify this instrument and geometry'],
['5×5 全因子，避免兩個濃度綁在一起','A 5 by 5 factorial separates concentration changes','兩種甜味劑各有零、二點五、五、七點五、十百分比五個水準。全部配對成二十五點，目標濃度相關係數等於零。若只配一比一的對角線，兩個濃度完全綁在一起；但零相關也不保證光譜一定能分辨兩種成分。','Each sweetener has five levels: zero, two point five, five, seven point five, and ten percent. All twenty-five combinations have zero target correlation. A one-to-one diagonal confounds the two concentrations. Zero correlation helps the design but does not guarantee spectral separability.','design','25 點 r=0；對角線 r=1；仍需足夠訊號與驗證','25-point r=0; diagonal r=1; signal and validation still matter'],
['拉丁方格分工：全班合起來才完整','Latin allocation: combine the whole class design','每組配五瓶，讓每組都涵蓋所有阿斯巴甜與三氯蔗糖水準。G1 雖然剛好拿到對角線，也不能只用自己五瓶建模。把全班二十五瓶合併，才保留完整的因子設計；填充劑比例是剩餘量，不是第三個獨立因子。','Each group prepares five bottles spanning all five levels of both sweeteners. G1 happens to receive the diagonal, but must not fit a model using only its own five bottles. Combine all twenty-five class preparations. Filler is the remainder, not a third independently controlled factor.','latin','配製可分工，校正設計不能分裂成各組自己的五瓶','Share preparation work, not five-bottle calibration subsets'],
['Y 要用實際秤重，不用目標值代替','Use actual weighed fractions as reference y','CAL-17 目標是阿斯巴甜七點五、三氯蔗糖五百分比。示例實際秤到零點一五二三、零點零九九七與一點七四八九克，總量二點零零零九克。阿斯巴甜實際是七點六一百分比，分母必須是實際總質量，不是目標兩克。','CAL-17 targets seven point five percent aspartame and five percent sucralose. The example weighs zero point one five two three, zero point zero nine nine seven, and one point seven four eight nine grams. Divide by the actual total, two point zero zero zero nine grams: aspartame is about seven point six one percent.','mass','CAL-17：實際 A = 7.6116% w/w；總質量 2.0009 g','CAL-17: actual A = 7.6116% w/w; total = 2.0009 g'],
['秤重不確定度，別和偏差混在一起','Distinguish uncertainty from a target deviation','若示意假設天平誤差在正負零點一毫克內呈矩形分布，標準不確定度是半寬除以根號三，約零點零五八毫克。這不是把天平顯示位數直接當規格。質量分率還共用分母，要一併傳播三個質量的不確定度。','Assuming a rectangular balance error bounded by plus or minus zero point one milligram, standard uncertainty is the half-width divided by square root three, about zero point zero five eight milligram. Readability alone does not establish that bound. Fraction uncertainty also includes the shared denominator and all three masses.','uncertainty','質量的相對 u，與質量分率的 u，不是同一個數字','Relative mass uncertainty differs from fraction uncertainty'],
['幾何稀釋：少量成分也要混得有代表性','Geometric dilution supports representative mixing','記錄三種成分後，先將少量粉末與相近量的填充劑混勻，再逐步加入其餘粉末。兩種甜味劑都必須加入並核對總量，研磨、過篩後立即封裝。這個流程能改善混合方式，但不能單靠步驟就證明均勻，還要看重裝變異。','After recording all masses, mix the smaller powder portions with comparable filler amounts, then add the remaining powder progressively. Include both sweeteners and check mass conservation. Grind, sieve, and seal promptly. Following the steps supports mixing but does not prove uniformity; assess reload variability.','mixing','記錄 > 幾何稀釋 > 過篩 > 密封；仍須 QC','Record > geometric dilution > sieve > seal; verify with QC'],
['隨機分架，降低時間與濃度綁定','Randomize racks to reduce time-concentration confounding','二十五瓶校正加七瓶盲樣，共三十二瓶，隨機分成六、六、五、五、五、五瓶的六架。照濃度排序可能把儀器漂移誤認為濃度效應；隨機化能打散這種綁定，但不能消除漂移，也不能取代白參考。','Randomize twenty-five calibration and seven blind bottles into racks of six, six, five, five, five, and five. Concentration-ordered runs can confound drift with concentration. Randomization reduces systematic alignment, but does not remove drift or replace white-reference checks.','random','隨機化不是漂移校正；白參考也不是取樣均勻保證','Randomization is not drift correction or a mixing guarantee'],
['六站輪轉：384 條檔案，一條都不能少','Six stations: keep all 384 measurement records','三十二瓶都要走過五台 NIR 與一個 Raman 站，每瓶每站重裝兩次，各自存檔，不先平均。每站六十四條，全班六站共三百八十四條。七瓶盲樣不進校正集，真實濃度由 TA 保管，第十六週才揭曉。','Every bottle visits five NIR stations and one Raman station. Save two separate reload spectra per bottle at each station, without averaging first. That is sixty-four spectra per station and three hundred eighty-four overall. Keep seven blind bottles out of calibration and their real concentrations with the TA until week sixteen.','rotation','32 瓶 × 6 站 × 2 重裝 = 384 個分開儲存的檔案','32 bottles x 6 stations x 2 reloads = 384 separate files'],
['時間試算：看最慢的那一架，不只看總量','Timing depends on the largest rack at each rotation','如果每條光譜一點五分鐘，每輪白參考一分鐘，最大六瓶一架要十九分鐘。六輪共一百一十四分鐘，只比一百一十五分鐘預算少一分鐘。若每條兩分鐘，就要一百五十分鐘。進度落後要找 TA，不可自行省略重裝或盲樣。','At one point five minutes per spectrum plus one minute for the reference each round, the largest six-bottle rack needs nineteen minutes. Six synchronized rounds take one hundred fourteen minutes, just under the one hundred fifteen minute budget. Two minutes per spectrum requires one hundred fifty minutes. Ask the TA if behind; do not skip reloads or blinds.','timing','1.5 分/條：114 分；2 分/條：150 分（含每輪參考）','1.5 min/spectrum: 114 min; 2 min: 150 min (with references)'],
['重裝 RSD：取樣是否蓋過濃度差？','Reload RSD: does sampling variation hide level differences?', '兩次重裝的樣本標準差，是兩值差的絕對值除以根號二。例如一零二與九十八，平均一百，RSD 約二點八三百分比。只有兩次重複很不穩定，要合看多瓶的瓶內變異，再和相鄰濃度的特徵差距比較，不能用不同濃度的混合標準差代替。','For two reloads, sample standard deviation is their absolute difference divided by square root two. Values one hundred two and ninety-eight have mean one hundred and RSD about two point eight three percent. Pool within-bottle variation across bottles, then compare it with adjacent-level feature differences; do not mix between-concentration variation into repeatability.','qc','同瓶重裝看精密度；不同濃度的差異不是重裝誤差','Within-bottle reloads assess precision; between-level differences do not'],
['交出完整資料，讓 W16 有可靠起點','Prepare a traceable handoff for W16','上傳實際質量分率、瓶號、配製組、儀器與重裝編號，並保留亂數種子、量測順序、白參考與 QC 紀錄。粉末避免吸入，不食用實驗樣品；Raman 由 TA 依安全規範操作。下一週再以整瓶分組驗證，建立並評估模型。','Upload actual fractions, bottle IDs, preparation groups, instruments, and reload numbers. Retain the random seed, run order, reference checks, and QC notes. Avoid inhaling powders or consuming lab samples; the TA follows Raman laser procedures. Next week, validate models with whole-bottle groups kept together.','workflow','交付：實際配方、384 檔案清單、順序與 QC 紀錄','Submit: actual recipes, 384-file manifest, run order and QC']]
FONT=Path('/home/administrator/.local/share/fonts/hermes-food-tests/msjh.ttc')
if not FONT.exists():FONT=Path('/mnt/c/Windows/Fonts/msjh.ttc')
if not FONT.exists():FONT=Path('C:/Windows/Fonts/msjh.ttc')
F={n:ImageFont.truetype(str(FONT),n) for n in [18,20,22,24,26,28,30,34,40]};colors=['#246bc4','#df7d23','#129785','#9b58b1','#ca5d70']
def wrap(text,width,font):
 words=text.split(' ') if all(ord(c)<128 for c in text) else list(text);sep=' ' if all(ord(c)<128 for c in text) else '';lines=[];line=''
 for w in words:
  s=line+sep+w if line else w
  if line and font.getlength(s)>width:lines.append(line);line=w
  else:line=s
 if line:lines.append(line)
 return lines

def frame(s,lang,progress):
 im=Image.new('RGB',(1280,720),'#edf6ff');d=ImageDraw.Draw(im);d.rounded_rectangle((24,18,1256,702),radius=24,fill='white');d.text((52,32),'FOOD ANALYSIS LAB / W15 / SWEETENER DESIGN + PREPARATION',font=F[22],fill='#246bb2')
 for j,line in enumerate(wrap(s[0 if lang=='zh' else 1],1170,F[40])):d.text((52,75+j*46),line,font=F[40],fill='#173653')
 typ=s[4]
 def cards(entries):
  for j,(a,b) in enumerate(entries):
   yy=180+j*105;d.rounded_rectangle((65,yy,1215,yy+86),radius=12,fill='#eaf3ff');d.text((85,yy+20),a,font=F[28],fill=colors[j]);lines=wrap(b,760,F[24])
   for kk,line in enumerate(lines):d.text((425,yy+15+kk*29),line,font=F[24],fill='#173653')
 if typ=='design':
  for panel in range(2):
   L=120+panel*590;T=220;R=L+420;B=440;d.line((L,T,L,B,R,B),fill='#9aabb9',width=2)
   points=list(zip(A,S)) if panel==0 else [(v,v) for v in [0,2.5,5,7.5,10]]
   for a,b in points:
    xx=L+a/10*(R-L);yy=B-b/10*(B-T);d.ellipse((xx-6,yy-6,xx+6,yy+6),fill=colors[panel])
   d.text((L,165),'25-point grid / r=0 / rank3' if panel==0 else 'Diagonal / r=1 / rank2',font=F[22],fill=colors[panel]);d.text((L+130,460),'Aspartame % w/w',font=F[22],fill='#62788c')
  d.text((75,485),'Y: sucralose % w/w / rank includes an intercept',font=F[20],fill='#62788c')
 elif typ=='latin':
  d.text((75,165),'Proposed preparation group / CAL ID matches NB13',font=F[26],fill='#246bb2')
  for i in range(5):
   for j in range(5):
    xx=120+i*215;yy=215+j*49;grp=(j-i)%5;d.rounded_rectangle((xx,yy,xx+198,yy+42),radius=6,fill=colors[grp]);d.text((xx+12,yy+7),f'CAL-{5*i+j:02} / G{grp+1}',font=F[22],fill='white')
  d.text((125,480),'Columns: A levels / rows: S levels / E = 100 - A - S',font=F[22],fill='#62788c')
 elif typ=='mass':cards([('ACTUAL MASS','A 0.1523 + S 0.0997 + E 1.7489 = 2.0009 g'),('ACTUAL A',f'{fractions[0]:.4f}% w/w (target 7.5%)'),('ACTUAL S / E',f'{fractions[1]:.4f}% / {fractions[2]:.4f}% w/w')])
 elif typ=='uncertainty':cards([('ASSUMPTION','Rectangular half-width a=0.1 mg, not a certificate'),('MASS u',f'a / sqrt(3) = {u*1000:.5f} mg / relative A {u/m[0]*100:.5f}%'),('FRACTION u',f'A fraction: {uf[0]:.5f} percentage points (3 masses)')])
 elif typ=='mixing':cards([('01 / RECORD','Record A, S and E masses; do not omit an ingredient'),('02 / MIX','Small portions + comparable filler; add progressively'),('03 / VERIFY','Sieve + seal + reload QC; no homogeneity guarantee')])
 elif typ=='random':
  d.text((75,165),'32 bottle IDs / six rack sizes: 6, 6, 5, 5, 5, 5',font=F[26],fill='#246bb2')
  for j,size in enumerate([6,6,5,5,5,5]):
   xx=90+j*195;d.text((xx,215),f'R{j+1}',font=F[28],fill=colors[j%5])
   for i in range(size):d.rounded_rectangle((xx,265+i*30,xx+140,288+i*30),radius=4,fill=colors[(i+j)%5])
  d.text((115,480),'Illustrative rack diagram; export a seeded manifest from the lab',font=F[22],fill='#62788c')
 elif typ=='rotation':
  d.text((75,165),'Five NIR stations + Raman 785 / each rack visits all six',font=F[24],fill='#246bb2')
  for station in range(6):d.text((150+station*170,205),f'NIR-G{station+1}' if station<5 else 'Raman',font=F[22],fill='#246bb2')
  round_=min(5,int(progress*6))
  for r in range(6):
   col=(r+round_)%6;xx=150+col*170;d.rounded_rectangle((xx,275,xx+140,355),radius=12,fill=colors[r%5]);d.text((xx+20,297),f'Rack {r+1}',font=F[24],fill='white')
  d.text((115,405),f'Round {round_+1}/6: keep the people, rotate the racks',font=F[28],fill='#173653');d.text((115,475),'Every bottle: rep1 + rep2 / never average before saving',font=F[22],fill='#62788c')
 elif typ=='timing':cards([('LARGEST RACK','6 bottles x 2 reloads x 1.5 min + 1 min reference'),('SYNCHRONIZED','19 min/round x 6 rounds = 114 min / budget 115'),('SLOWER SCANS','2 min/spectrum: (6 x 2 x 2 + 1) x 6 = 150 min')])
 elif typ=='qc':
  d.text((75,165),'Illustrative reload feature values / not measured spectra',font=F[24],fill='#246bb2')
  for j,val in enumerate(qc5):
   xx=135+j*215;top=450-(val-90)/20*210;d.rounded_rectangle((xx,top,xx+110,450),radius=8,fill=colors[j]);d.text((xx+25,top-35),str(val),font=F[26],fill='#173653');d.text((xx+15,463),f'rep{j+1}',font=F[22],fill='#62788c')
  d.text((780,204),f'5 reloads: SD={sd5:.3f}',font=F[22],fill='#173653');d.text((780,235),f'2 reloads (102,98): SD={sd2:.3f}',font=F[22],fill='#173653')
 elif typ=='feasibility':cards([('SIGNAL','Pilot blank + low level on each actual instrument'),('MODE','Confirm powder diffuse reflectance / Raman setup'),('SCOPE','Course preparation study, not a food authenticity test')])
 else:cards([('01 / DESIGN','25 full-factorial + 7 independently prepared blinds'),('02 / PREPARE','Actual masses > geometric dilution > sieve > seal'),('03 / MEASURE','Random racks > six stations > separate reload files')])
 take=s[5 if lang=='zh' else 6];assert F[24].getlength(take)<1150,take;d.rounded_rectangle((52,518,1228,565),radius=10,fill='#e7f6f1');d.text((68,528),take,font=F[24],fill='#17604e');text=s[2 if lang=='zh' else 3];font=F[26 if lang=='zh' else 24];lines=wrap(text,1150,font)
 if len(lines)>4:font=F[22];lines=wrap(text,1150,font)
 assert len(lines)<=4,(len(lines),text)
 for j,line in enumerate(lines):d.text((65,577+j*28),line,font=font,fill='#243c59')
 d.rectangle((52,694,52+1176*progress,699),fill='#246bdd');return im
if __name__=='__main__':render(scenes,OUT,cache_dir('w15'),'w15',frame)
