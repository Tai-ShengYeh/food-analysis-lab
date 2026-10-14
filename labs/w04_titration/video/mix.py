#!/usr/bin/env python3
"""混音：每幕配音放在 幕開始＋LEAD 秒（和 build.py／字幕同一套時間），配樂壓在人聲下，loudnorm −16 LUFS → out/mix.wav"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.environ.get('CAE_SCRIPTS', os.path.expanduser('~/.claude/skills/code-animation-explainer/scripts'))
LEAD = 0.5
tl = json.load(open(os.path.join(HERE, 'captions', 'timeline.json'), encoding='utf-8'))
T = open(os.path.join(HERE, 'compositions', 'timing.js'), encoding='utf-8').read()
total = json.loads(T[T.index('{'):T.rindex('}') + 1])['total']
out = os.path.join(HERE, 'out'); os.makedirs(out, exist_ok=True)
bgm = os.path.join(out, 'bgm.wav')
subprocess.run([sys.executable, os.path.join(SCRIPTS, 'bgm.py'), str(int(total) + 2), bgm], check=True)
ins, flt = [], []
for i, s in enumerate(tl):
    ins += ['-i', os.path.join(HERE, 'vo', f"{s['id']}.wav")]
    ms = int((s['start'] + LEAD) * 1000)
    flt.append(f'[{i}:a]adelay={ms}|{ms},aformat=channel_layouts=mono[v{i}]')
n = len(tl)
flt.append(''.join(f'[v{i}]' for i in range(n)) + f'amix=inputs={n}:normalize=0,apad=whole_dur={total:.2f},asplit[voice][key]')
flt.append(f'[{n}:a]volume=0.55,afade=t=out:st={total - 3:.2f}:d=3,aformat=channel_layouts=mono[m]')
flt.append('[m][key]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[duck]')
flt.append(f'[voice][duck]amix=inputs=2:normalize=0,atrim=0:{total:.2f},loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[out]')
subprocess.run(['ffmpeg', '-v', 'error', '-y', *ins, '-i', bgm, '-filter_complex', ';'.join(flt), '-map', '[out]', '-ac', '2',
                os.path.join(out, 'mix.wav')], check=True)
print('→ out/mix.wav', total, '秒')
