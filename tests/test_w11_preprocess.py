"""Repro: uv venv <venv>; uv pip install --python <venv>/bin/python playwright numpy scipy
<venv>/bin/python -m playwright install chromium
<venv>/bin/python tests/test_w11_preprocess.py
No server or network needed; opens file:// and blocks all HTTP requests.
"""
import json
from pathlib import Path
import tempfile
import numpy as np
from scipy.linalg import solve
from scipy.signal import savgol_filter
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
LAB=ROOT/'labs/w11_preprocess_similarity'
checks=0

def check(ok,message):
 global checks
 assert ok,message
 checks+=1

def numerical(page):
 y=np.sin(np.arange(51)*.21)+np.arange(51)*.025
 y[15]+=3
 actual=page.evaluate('(y)=>SpectraMath.als(y,1000,.01,20)',y.tolist())
 D=np.diff(np.eye(len(y)),n=2,axis=0);w=np.ones(len(y))
 for _ in range(20):
  z=solve(np.diag(w)+1000*D.T@D,w*y,assume_a='pos')
  w=np.where(y>z,.01,.99)
 err=float(np.max(np.abs(z-actual)))
 check(err<1e-8,f'ALS dense reference error {err}')
 print(f'ALS vs independent SciPy dense solve: max error {err:.3e}')
 for d in range(3):
  actual=page.evaluate('v=>SpectraMath.sg(v.y,9,3,v.d,5)',{'y':y.tolist(),'d':d})
  err=float(np.max(np.abs(np.array(actual)-savgol_filter(y,9,3,deriv=d,delta=5,mode='interp'))))
  check(err<1e-9,f'SG derivative {d}: {err}')
  print(f'SG d={d} vs SciPy (delta=5, including edges): max error {err:.3e}')
 check(page.evaluate('()=>{let y=[.2,.4,.9,.5,.3],z=SpectraMath.snv(y),w=SpectraMath.snv(y.map(v=>2*v+.1));return Math.abs(SpectraMath.mean(z))<1e-12&&Math.abs(SpectraMath.sd(z)-1)<1e-12&&z.every((v,i)=>Math.abs(v-w[i])<1e-12)}'),'SNV population invariance')
 check(page.evaluate('()=>SpectraMath.snv([1,1,1]).every(v=>v===0)'),'flat SNV')
 a=np.array([1.,3.,2.,6.]);b=np.array([2.,4.,1.,5.]);r=page.evaluate('v=>SpectraMath.metrics(v[0],v[1])',[a.tolist(),b.tolist()])
 co=float(a@b/np.linalg.norm(a)/np.linalg.norm(b))
 expected={'pearson':np.corrcoef(a,b)[0,1],'cosine':co,'sam':np.degrees(np.arccos(co)),'euclidean':np.linalg.norm(a-b)}
 for k in expected:check(abs(r[k]-expected[k])<1e-12,'metric '+k)
 check(page.evaluate('()=>{let r=SpectraMath.metrics([0,0],[1,1]);return r.pearson===null&&r.cosine===null&&r.sam===null}'),'undefined metrics')
 check(page.evaluate('()=>{let y=Array.from({length:31},(_,i)=>.3+.003*Math.sin(i));y[15]=3;let d=SpectraMath.despike(y);return d.indices.includes(15)&&Math.abs(d.y[15]-.3)<.01}'),'despike removes injected impulse')
 check(page.evaluate('()=>{let s={gain:1,offset:0,baseline:1,noise:.02,spike:2,sample:"0",seed:11};return JSON.stringify(SpectraMath.synthetic(s))===JSON.stringify(SpectraMath.synthetic(s))}'),'deterministic synthesis')

with sync_playwright() as pw:
 browser=pw.chromium.launch()
 for lang in ['zh','en']:
  for mobile in [False,True]:
   context=browser.new_context(viewport={'width':390 if mobile else 1440,'height':844 if mobile else 1000},accept_downloads=True,is_mobile=mobile,has_touch=mobile)
   context.route('http://**/*',lambda route:route.abort());context.route('https://**/*',lambda route:route.abort())
   page=context.new_page();errors=[]
   page.on('pageerror',lambda err:errors.append(str(err)))
   page.on('console',lambda msg:errors.append(msg.text) if msg.type=='error' else None)
   page.goto((LAB/('preprocess_lab.en.html' if lang=='en' else 'preprocess_lab.html')).as_uri())
   page.wait_for_selector('svg path')
   if lang=='zh' and not mobile:numerical(page)
   for i,answer in enumerate([1,0,1,0,1,1]):
    page.locator(f'[data-scene="{i}"]').click()
    check(page.locator('svg[role=img]').count()==1,f'chart scene {i}')
    check(page.locator('svg title').text_content()!='','SVG accessible title')
    page.locator(f'[data-answer="{1-answer}"]').click()
    check('bad' in page.locator('#feedback').get_attribute('class'),'immediate incorrect feedback')
    page.locator(f'[data-answer="{answer}"]').click()
    check('good' in page.locator('#feedback').get_attribute('class'),'immediate correct feedback')
    control=page.locator('[data-control]').first
    if control.get_attribute('type')=='range':
     control.focus();control.press('ArrowRight')
    else:control.select_option('mixed')
    page.locator('#reflection').fill(f'Observed response in scene {i}; explain parameter tradeoff.')
    check(page.evaluate('document.documentElement.scrollWidth<=innerWidth'),f'no horizontal overflow {lang}/{mobile}/{i}')
   check(page.locator('#progress').get_attribute('value')=='6','all six completed')
   # Exercise every visible control at both extremes / all option values.
   for i in range(6):
    page.locator(f'[data-scene="{i}"]').click()
    for c in page.locator('[data-control]').all():
     original=c.input_value()
     values=[c.get_attribute('min'),c.get_attribute('max')] if c.get_attribute('type')=='range' else c.locator('option').evaluate_all('(opts)=>opts.map(o=>o.value)')
     for value in values:
      c.evaluate('(el,v)=>{el.value=v;el.dispatchEvent(new Event("input",{bubbles:true}));}',value)
      check(page.evaluate('LabState.result.final.every(Number.isFinite)&&![...document.querySelectorAll("svg path")].some(p=>/NaN|Infinity/.test(p.getAttribute("d")))'),'control finite '+c.get_attribute('id')+'='+value)
     c.evaluate('(el,v)=>{el.value=v;el.dispatchEvent(new Event("input",{bubbles:true}));}',original)
   page.locator('[data-scene="5"]').click()
   check(page.locator('#rankingBody tr').count()==3,'top3 rows')
   page.locator('#sample').select_option('mixed')
   check(('Mixed' if lang=='en' else '混合') in page.locator('#warning').inner_text(),'mixed warning')
   page.locator('#sample').select_option('outside')
   check(('Out-of-library' if lang=='en' else '庫外') in page.locator('#warning').inner_text(),'outside warning')
   page.locator('#sample').select_option('0')
   check(('Ambiguity' if lang=='en' else '歧義') in page.locator('#warning').inner_text(),'near-duplicate warning')
   for metric in ['pearson','cosine','sam','euclidean']:
    page.locator('#metric').select_option(metric)
    scores=page.evaluate('LabState.result.ranks.map(r=>r[LabState.state.metric])')
    check(scores==sorted(scores,reverse=metric in ['pearson','cosine']),'ranking order '+metric)
   page.reload();page.wait_for_selector('svg path')
   check(page.locator('#progress').get_attribute('value')=='6','persistent progress')
   with page.expect_download() as info:page.locator('#csv').click()
   csv=Path(info.value.path()).read_text(encoding='utf-8-sig').strip().splitlines()
   check(len(csv)==282,'CSV 281 points + header')
   check(len(csv[0].split(','))==9,'CSV 9 columns')
   with page.expect_download() as info:page.locator('#record').click()
   record=json.loads(Path(info.value.path()).read_text(encoding='utf-8-sig'))
   check(len(record['scenes'])==6 and all(s['correct'] and s['operated'] and s['explanation'] for s in record['scenes']),'record complete')
   check(len(record['rankings'])==4,'record all candidates')
   if lang=='zh':page.screenshot(path=str(Path.home()/'.hermes/cache/scratch'/f'w11-{mobile}.png'),full_page=True)
   page.once('dialog',lambda d:d.accept());page.locator('#reset').click()
   check(page.locator('#progress').get_attribute('value')=='0','reset clears progress')
   check(page.locator('#gain').input_value()=='1.5','reset defaults')
   check(not errors,f'JS/console errors: {errors}')
   print(f'{lang} {"mobile 390×844" if mobile else "desktop 1440×1000"}: six scenes, controls, feedback, progress, reload, warnings, four metrics, exports, reset; 0 JS errors; offline PASS')
   context.close()
 browser.close()
print(f'PASS: {checks} assertions')
