#!/usr/bin/env python3
"""Verify exact W14 encoded bytes and real browser integration; --media-only for frames."""
from pathlib import Path
import hashlib,json,subprocess,threading,http.server,functools,sys,math
from playwright.sync_api import sync_playwright
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];ASSET=ROOT/'labs/w14_vip_plsda/animations';EVIDENCE=Path.home()/'.hermes/cache/scratch/w14-verification';EVIDENCE.mkdir(exist_ok=True,parents=True)
timing=json.loads((ASSET/'timing.json').read_text());report={'media':[],'browser':[]}
for lang in ['zh','en']:
 p=ASSET/f'w14_tour_{lang}.mp4';info=json.loads(subprocess.check_output(['ffprobe','-v','quiet','-show_format','-show_streams','-of','json',str(p)]));video=next(s for s in info['streams'] if s['codec_type']=='video');audio=next(s for s in info['streams'] if s['codec_type']=='audio');cues=[t for t in timing if t['lang']==lang];duration=float(info['format']['duration'])
 assert (video['width'],video['height'])==(1280,720) and len(cues)==13
 assert float(audio['duration'])>=sum(t['scene_duration'] for t in cues)-.1
 assert cues[-1]['start']+cues[-1]['speech_duration']<duration
 assert (ASSET/f'w14_tour_{lang}.vtt').read_text().count(' --> ')==13
 subprocess.run(['ffmpeg','-v','error','-i',str(p),'-f','null','-'],check=True)
 for i,t in enumerate(cues):subprocess.run(['ffmpeg','-y','-v','error','-ss',str(t['start']+.75*t['scene_duration']),'-i',str(p),'-frames:v','1',str(EVIDENCE/f'{lang}-{i}.jpg')],check=True)
 sheet=Image.new('RGB',(1280,math.ceil(len(cues)/2)*360),'white')
 for i in range(len(cues)):
  im=Image.open(EVIDENCE/f'{lang}-{i}.jpg');im.thumbnail((640,360));sheet.paste(im,((i%2)*640,(i//2)*360))
 sheet.save(EVIDENCE/f'frames-{lang}.jpg')
 report['media'].append(dict(lang=lang,duration=duration,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),full_decode='passed',complete_speech=True,resolution=[1280,720],captions=13))
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,format,*args):pass
if '--media-only' not in sys.argv:
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)));threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True,args=['--no-sandbox','--autoplay-policy=no-user-gesture-required'])
  for lang in ['zh','en']:
   suffix='' if lang=='zh' else '.en'
   for width,height in [(1280,900),(390,844)]:
    page=browser.new_page(viewport=dict(width=width,height=height));errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(base+'/labs/w14_vip_plsda/tour'+suffix+'.html');page.wait_for_function('document.querySelector("video").readyState>=2');page.evaluate('''async()=>{let v=document.querySelector('video');v.muted=true;v.textTracks[0].mode='hidden';await v.play()}''');page.wait_for_timeout(1000)
    assert page.evaluate('document.querySelector("video").currentTime')>.5
    page.wait_for_function('document.querySelector("video").textTracks[0].cues && document.querySelector("video").textTracks[0].cues.length===13')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');page.screenshot(path=str(EVIDENCE/f'player-{lang}-{width}.png'),full_page=True)
    page.goto(base+'/labs/w14_vip_plsda/index'+suffix+'.html#s2');page.wait_for_function('cur===2');page.wait_for_function('document.querySelector("video").readyState>=2');page.evaluate('''async()=>{let v=document.querySelector('video');v.muted=true;await v.play()}''');page.wait_for_timeout(700)
    page.locator('video').focus();page.keyboard.press('ArrowRight');assert page.evaluate('cur')==2
    bounds=page.locator('video').bounding_box();assert bounds['x']>=0 and bounds['x']+bounds['width']<=width+1
    page.evaluate('show(4)');page.wait_for_timeout(100);assert page.evaluate('document.querySelector("video").paused')
    page.evaluate('show(3)');page.wait_for_function('document.querySelector("iframe").contentDocument.querySelectorAll("button").length>0');page.wait_for_timeout(700);page.screenshot(path=str(EVIDENCE/f'integrated-{lang}-{width}.png'),full_page=True)
    page.goto(base+'/index'+suffix+'.html');assert page.locator('#w14 a[href$="tour'+suffix+'.html"]').count()==1;assert page.locator('#w14 a[href$="vip_plsda_lab'+suffix+'.html"]').count()==1
    page.goto(base+'/labs/w14_vip_plsda/vip_plsda_lab'+suffix+'.html');page.screenshot(path=str(EVIDENCE/f'lab-{lang}-{width}.png'),full_page=True)
    assert not errors,errors
    report['browser'].append(dict(lang=lang,width=width,playback='passed',vtt_cues=13,hidden_pause='passed',keyboard_isolation='passed',video_fit='passed',integrated_iframe='passed',home_links='passed',page_errors=errors));page.close()
  browser.close()
 server.shutdown();(ROOT/'scripts/w14-media-verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
