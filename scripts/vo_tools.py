#!/usr/bin/env python3
"""ElevenLabs narration helpers for the W11–W16 tours (voice IAN, eleven_v3).

  python scripts/vo_tools.py fetch scripts/vo/w11 urls.json      # {"zh-00": "https://…", "zh-06b": "https://…"}
  python scripts/vo_tools.py check scripts/vo/w11 [zh-06 en-03b …]

texts.json lists every take key (lang-scene) with the subtitle text and, for Chinese,
an optional `tts` field: homophones sent to the voice (譜→普, 波→玻, 週→周, 擬→你) because
IAN misreads the original characters; also 確認→卻任, 計算→記蒜, 門檻→門砍, 濾→綠, 突→凸, 軸→妯. Subtitles always use `text`.

check: Chinese takes go through the code-animation-explainer pron_check (tone-aware CTC);
English takes are transcribed with faster-whisper and word-diffed against the script.
Both also flag a speaking rate far above the week's median (a sign of clipped audio).
Retakes are named <key>b, <key>c …; the renderer uses <key>.mp3, so copy the chosen take there.
"""
import difflib, json, os, re, statistics, subprocess, sys, urllib.request

PC = os.path.expanduser('~/.claude/skills/code-animation-explainer/scripts/pron_check.py')


def dur(p):
    return float(subprocess.check_output(['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]))


def units(lang, t):
    return len(re.sub(r'[\s，。、；：「」？！,.;:?!()（）]', '', t)) if lang == 'zh' else len(t.split())


def fetch(d, urls):
    for k, u in json.load(open(urls, encoding='utf-8')).items():
        p = os.path.join(d, k + '.mp3')
        urllib.request.urlretrieve(u, p)
        print(k, os.path.getsize(p))


_whisper = None


def en_diff(path, text):
    global _whisper
    if _whisper is None:
        from faster_whisper import WhisperModel
        _whisper = WhisperModel('small.en', device='cpu', compute_type='int8')
    segs, _ = _whisper.transcribe(path, language='en', beam_size=5)
    heard = ' '.join(s.text for s in segs)
    norm = lambda s: re.findall(r"[a-z0-9']+", s.lower().replace('-', ' '))
    a, b = norm(text), norm(heard)
    miss = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if op in ('delete', 'replace') and i2 - i1 >= 3:
            miss.append(' '.join(a[i1:i2]))
    return miss, heard


def check(d, only):
    items = {it['key']: it for it in json.load(open(os.path.join(d, 'texts.json'), encoding='utf-8'))}
    files = sorted(f[:-4] for f in os.listdir(d) if f.endswith('.mp3'))
    rates = {}
    for k in files:
        base = re.sub(r'[b-z]$', '', k)
        if base in items:
            it = items[base]
            rates.setdefault(it['lang'], []).append(units(it['lang'], it['text']) / dur(os.path.join(d, k + '.mp3')))
    med = {l: statistics.median(v) for l, v in rates.items()}
    bad = 0
    for k in files:
        base = re.sub(r'[b-z]$', '', k)
        if base not in items or (only and k not in only):
            continue
        it, p = items[base], os.path.join(d, k + '.mp3')
        sec = dur(p); rate = units(it['lang'], it['text']) / sec
        flags = []
        if rate > 1.2 * med[it['lang']]:
            flags.append(f'FAST {rate:.2f}/s vs median {med[it["lang"]]:.2f}')
        if it['lang'] == 'zh':
            r = subprocess.run([sys.executable, PC, p, it.get('tts', it['text'])], capture_output=True, text=True,
                               encoding='utf-8', env={**os.environ, 'PYTHONUTF8': '1'})
            errs = [l.strip() for l in r.stdout.splitlines() if l.strip().startswith('讀錯') and '應為' in l]
            unheard = sum('沒聽到' in l for l in errs)
            if errs:
                flags.append(f'{len(errs)} 讀錯' + (f'（{unheard} 沒聽到）' if unheard else '') + ': ' +
                             ' / '.join(re.sub(r'\s*應為.*', '', e.replace('讀錯', '').strip()) for e in errs[:6]))
        else:
            miss, heard = en_diff(p, it['text'])
            if miss:
                flags.append('MISSING: ' + ' | '.join(miss))
        bad += bool(flags)
        print(f'{k}\t{sec:5.2f}s\t' + ('OK' if not flags else '  '.join(flags)), flush=True)
    print(f'{bad} take(s) flagged')


if __name__ == '__main__':
    cmd, d, *rest = sys.argv[1:]
    fetch(d, rest[0]) if cmd == 'fetch' else check(d, set(rest))
