"""Reusable scene-aligned teaching-video renderer (Pillow/ffmpeg, ElevenLabs narration from scripts/vo/).
Public entry: render(scenes, out, cache, slug, frame). Frame is (scene,lang,progress).
Scenes are [title_zh,title_en,narration_zh,narration_en,visual,takeaway_zh,takeaway_en].
"""
from pathlib import Path
import hashlib,json,math,subprocess

def stamp(sec,sep=','):
 ms=round(sec*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000);return f'{h:02}:{m:02}:{s:02}{sep}{ms:03}'
def run(cmd):subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL)

VO_ROOT=Path(__file__).resolve().parent/'vo'
def vo_wav(slug,lang,i,text,cache):
 """ElevenLabs take scripts/vo/<slug>/<lang>-<ii>.mp3 (voice IAN, eleven_v3, same as W1) -> 44.1 kHz mono wav,
 slowed 5% with atempo like the W1 tour. Refuses a take whose script line has changed since it was generated."""
 d=VO_ROOT/slug;key=f'{lang}-{i:02d}';items={it['key']:it for it in json.loads((d/'texts.json').read_text(encoding='utf-8'))}
 if key not in items or items[key]['text']!=text:raise SystemExit(f'{slug} {key}: narration differs from scripts/vo/{slug}/texts.json; regenerate the ElevenLabs take first')
 wav=Path(cache)/f'{lang}-{i}.wav';run(['ffmpeg','-y','-v','error','-i',str(d/f'{key}.mp3'),'-af','atempo=0.95','-ar','44100','-ac','1',str(wav)]);return wav
def cache_dir(slug):
 import os;return Path(os.environ.get('COURSE_RENDER_CACHE',Path.home()/'.cache/course-video'))/f'{slug}-render'
def render(scenes,out,cache,slug,frame):
 out=Path(out);cache=Path(cache);out.mkdir(exist_ok=True,parents=True);cache.mkdir(exist_ok=True,parents=True)
 # Preflight every scene in every language before expensive speech/render loops.
 for lang in ['zh','en']:
  for s in scenes:frame(s,lang,.8)
 (out/'storyboard.json').write_text(json.dumps([dict(zip(['title_zh','title_en','narration_zh','narration_en','visual','takeaway_zh','takeaway_en'],s)) for s in scenes],ensure_ascii=False,indent=2))
 timing=[]
 for lang in ['zh','en']:
  offset=0;subs=[];vtt=['WEBVTT\n'];concat=[]
  for i,s in enumerate(scenes):
   text=s[2 if lang=='zh' else 3];wav=vo_wav(slug,lang,i,text,cache)
   audio=float(subprocess.check_output(['ffprobe','-v','quiet','-show_entries','format=duration','-of','csv=p=0',str(wav)]));dur=math.ceil((audio+.7)*12)/12;clip=cache/f'{lang}-{i}.mp4'
   proc=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r','12','-i','-','-i',str(wav),'-af','apad','-t',str(dur),'-c:v','libx264','-preset','fast','-crf','24','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart',str(clip)],stdin=subprocess.PIPE)
   assert proc.stdin is not None
   states=[frame(s,lang,(k+1)/24).tobytes() for k in range(24)]
   for k in range(round(dur*12)):proc.stdin.write(states[min(23,int(k/(dur*12)*24))])
   proc.stdin.close();assert proc.wait()==0;concat.append("file '"+clip.as_posix()+"'");subs.append(f'{i+1}\n{stamp(offset)} --> {stamp(offset+audio)}\n{text}\n');vtt.append(f'{stamp(offset,".")} --> {stamp(offset+audio,".")}\n{text}\n');timing.append(dict(lang=lang,scene=i,start=offset,speech_duration=audio,scene_duration=dur));offset+=dur;print(lang,i,'speech',audio,'scene',dur,flush=True)
  lst=cache/f'{lang}-concat.txt';lst.write_text('\n'.join(concat));run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(lst),'-c','copy','-movflags','+faststart',str(out/f'{slug}_tour_{lang}.mp4')]);(out/f'{slug}_tour_{lang}.srt').write_text('\n'.join(subs));(out/f'{slug}_tour_{lang}.vtt').write_text('\n'.join(vtt));(out/f'narration_{lang}.txt').write_text('\n\n'.join(s[2 if lang=='zh' else 3] for s in scenes));frame(scenes[0],lang,.95).save(out/f'poster_{lang}.jpg')
 (out/'timing.json').write_text(json.dumps(timing,indent=2))
