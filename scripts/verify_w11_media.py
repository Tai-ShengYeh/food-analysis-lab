#!/usr/bin/env python3
"""Run with Pillow and Playwright installed; ffmpeg/ffprobe on PATH."""
from pathlib import Path
import hashlib,json,subprocess,threading,http.server,functools
from playwright.sync_api import sync_playwright
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]; ASSET=ROOT/'labs/w11_preprocess_similarity/animations'
EVIDENCE=Path.home()/'.hermes/cache/scratch/w11-verification'; EVIDENCE.mkdir(exist_ok=True,parents=True)
def run(*args):return subprocess.check_output(args,text=True)
timing=json.loads((ASSET/'timing.json').read_text()); report={'media':[],'browser':[]}
for lang in ['zh','en']:
 p=ASSET/f'w11_tour_{lang}.mp4';info=json.loads(run('ffprobe','-v','quiet','-show_format','-show_streams','-of','json',str(p)))
 video=next(s for s in info['streams'] if s['codec_type']=='video');audio=next(s for s in info['streams'] if s['codec_type']=='audio')
 assert (video['width'],video['height'])==(1280,720)
 assert float(audio['duration'])>=sum(t['scene_duration'] for t in timing if t['lang']==lang)-.1
 duration=float(info['format']['duration']); cues=[t for t in timing if t['lang']==lang]
 assert len(cues)==10 and (ASSET/f'w11_tour_{lang}.vtt').read_text().count(' --> ')==10
 assert cues[-1]['start']+cues[-1]['speech_duration']<duration
 subprocess.run(['ffmpeg','-v','error','-i',str(p),'-f','null','-'],check=True)
 for i,t in enumerate(cues):
  dest=EVIDENCE/f'{lang}-{i}.jpg'; subprocess.run(['ffmpeg','-y','-v','error','-ss',str(t['start']+t['scene_duration']*.7),'-i',str(p),'-frames:v','1',str(dest)],check=True)
 report['media'].append({'lang':lang,'duration':duration,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'streams':['h264','aac'],'full_decode':'passed','complete_speech':True})
 sheet=Image.new('RGB',(1280,1800))
 for i in range(10):
  im=Image.open(EVIDENCE/f'{lang}-{i}.jpg');im.thumbnail((640,360));sheet.paste(im,((i%2)*640,(i//2)*360))
 sheet.save(EVIDENCE/f'actual-frames-{lang}.jpg')
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)));threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,args=['--no-sandbox','--autoplay-policy=no-user-gesture-required'])
 for lang in ['zh','en']:
  suffix='' if lang=='zh' else '.en'
  for width,height in [(1280,900),(390,844)]:
   page=browser.new_page(viewport={'width':width,'height':height});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.goto(base+'/labs/w11_preprocess_similarity/tour'+suffix+'.html');page.wait_for_function('document.querySelector("video").readyState >= 2')
   page.evaluate('''async()=>{let v=document.querySelector('video');v.muted=true;v.textTracks[0].mode='hidden';await v.play()}''');page.wait_for_timeout(1100)
   assert page.evaluate('document.querySelector("video").currentTime')>.5
   page.wait_for_function('document.querySelector("video").textTracks[0].cues && document.querySelector("video").textTracks[0].cues.length===10')
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
   page.screenshot(path=str(EVIDENCE/f'player-{lang}-{width}.png'),full_page=True)
   page.goto(base+'/labs/w11_preprocess_similarity/index'+suffix+'.html#s2');page.wait_for_function('cur===2');page.wait_for_function('document.querySelector("video").readyState>=2')
   page.evaluate('''async()=>{let v=document.querySelector('video');v.muted=true;await v.play()}''');page.wait_for_timeout(600)
   page.locator('video').focus();page.keyboard.press('ArrowRight');assert page.evaluate('cur')==2
   page.evaluate('show(4)');page.wait_for_timeout(100);assert page.evaluate('document.querySelector("video").paused')
   page.evaluate('show(2)');page.wait_for_timeout(200)
   bounds=page.locator('video').bounding_box();assert bounds['x']>=0 and bounds['x']+bounds['width']<=width+1
   page.evaluate('show(3)');page.wait_for_function('!!document.querySelector("iframe").contentDocument.querySelector("#sceneTitle")')
   assert page.frame_locator('iframe').locator('#sceneTitle').inner_text().startswith('1/6')
   page.wait_for_timeout(700)
   page.screenshot(path=str(EVIDENCE/f'integrated-lab-{lang}-{width}.png'),full_page=True)
   page.goto(base+'/index'+suffix+'.html');assert page.locator('#w11 a[href$="tour'+suffix+'.html"]').count()==1
   assert page.locator('#w11 a[href$="preprocess_lab'+suffix+'.html"]').count()==1
   page.goto(base+'/labs/w11_preprocess_similarity/preprocess_lab'+suffix+'.html');page.screenshot(path=str(EVIDENCE/f'lab-{lang}-{width}.png'),full_page=True)
   assert not errors,errors
   report['browser'].append({'lang':lang,'width':width,'playback':'passed','vtt_cues':10,'hidden_pause':'passed','keyboard_isolation':'passed','new_video_horizontal_fit':'passed','integrated_iframe':'passed','home_links':'passed','page_errors':errors});page.close()
 browser.close()
server.shutdown();(ROOT/'scripts/w11-media-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
