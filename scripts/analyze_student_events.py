#!/usr/bin/env python3
"""分析互動實驗室的學生作答紀錄（student_events），產生各週學習狀況報告。

資料來源（三選一）：
  1. Firestore（完整富欄位：topic / misconception / bloom / 用時 / 提示）
       pip install firebase-admin
       python scripts/analyze_student_events.py --firestore 服務帳戶金鑰.json
     金鑰：Firebase 主控台 → 專案設定 → 服務帳戶 → 產生新的私密金鑰。
  2. Supabase（只有基本欄位：題號、對錯、嘗試次數、分數）
       SUPABASE_KEY=<service_role key> python scripts/analyze_student_events.py --supabase
  3. 已匯出的檔案（.csv / .json / .ndjson / .xlsx，欄位名稱同 student_events）
       python scripts/analyze_student_events.py --file student_events.csv

常用選項：
  --chapters LAB-W01,LAB-W02,LAB-W03,LAB-W04   要分析的週（預設 W1–W4）
  --since 2026-09-01                           只看這天之後的紀錄
  --exclude 'test|demo|^T'                     排除測試學號（正規表示式，不分大小寫）
  --out teacher/student_events_report          輸出資料夾（teacher/ 已在 .gitignore）

輸出：
  report.md          各週摘要：參與/完成、最難的題目、最常見的迷思、需關注的學生
  student_events_report.xlsx   概覽、題目、主題、迷思、學生、需關注、原始資料

報告含學號，請勿 commit 或放到公開網站（本 repo 會發布到 GitHub Pages）。
"""
import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

DEFAULT_CHAPTERS = ['LAB-W01', 'LAB-W02', 'LAB-W03', 'LAB-W04']
WEEK_NAME = {'LAB-W01': 'W1 容量器具校正', 'LAB-W02': 'W2 水分與水活性',
             'LAB-W03': 'W3 灰分與鈉', 'LAB-W04': 'W4 滴定'}
SUPABASE_URL = 'https://qmldcjkllisvfgegkfsz.supabase.co'
FIELDS = ['student_id', 'course_id', 'class_id', 'chapter', 'game', 'event_type',
          'question_id', 'is_correct', 'attempts', 'final_score', 'total',
          'qtype', 'bloom', 'topic', 'confidence', 'misconception',
          'elapsed_sec', 'hints_used', 'hint_level', 'ts']


# ── 讀取 ─────────────────────────────────────────────────────────
def load_firestore(key_path, chapters):
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
    except ImportError:
        sys.exit('需要 firebase-admin：pip install firebase-admin')
    firebase_admin.initialize_app(credentials.Certificate(key_path))
    col = firestore.client().collection('student_events')
    rows = []
    for doc in col.where('chapter', 'in', chapters).stream():
        d = doc.to_dict()
        d['ts'] = d.pop('timestamp', None)
        d.pop('detail', None)  # 自由格式（如學生寫的結論），不進統計
        rows.append(d)
    return pd.DataFrame(rows)


def load_supabase(chapters):
    key = os.environ.get('SUPABASE_KEY')
    if not key:
        sys.exit('請設定環境變數 SUPABASE_KEY（service_role key；anon key 通常被 RLS 擋住讀取）')
    q = urllib.parse.quote(','.join(chapters))
    rows, step = [], 1000
    while True:
        url = (f'{SUPABASE_URL}/rest/v1/student_events?select=*'
               f'&chapter=in.({q})&order=id&limit={step}&offset={len(rows)}')
        req = urllib.request.Request(url, headers={'apikey': key, 'Authorization': f'Bearer {key}'})
        with urllib.request.urlopen(req, timeout=60) as r:
            page = json.load(r)
        rows += page
        if len(page) < step:
            break
    df = pd.DataFrame(rows)
    if len(df):
        df['ts'] = df['created_at'] if 'created_at' in df else df.get('client_ts')
    return df


def load_file(path):
    p = Path(path)
    if p.suffix == '.csv':
        df = pd.read_csv(p)
    elif p.suffix in ('.xlsx', '.xls'):
        df = pd.read_excel(p)
    elif p.suffix == '.ndjson':
        df = pd.read_json(p, lines=True)
    else:
        data = json.loads(p.read_text(encoding='utf-8'))
        if isinstance(data, dict):  # {doc_id: {...}} 或 {"documents": [...]}
            data = data.get('documents', list(data.values()))
        df = pd.DataFrame(data)
    if 'ts' not in df:
        for c in ('timestamp', 'created_at', 'client_ts'):
            if c in df:
                df['ts'] = df[c]
                break
    return df


# ── 清理 ─────────────────────────────────────────────────────────
def to_bool(s):
    return s.map(lambda v: None if pd.isna(v) else
                 v if isinstance(v, bool) else str(v).strip().lower() in ('true', '1', 't', 'yes'))


def clean(df, chapters, since, exclude):
    for c in FIELDS:
        if c not in df:
            df[c] = None
    df = df[FIELDS].copy()
    df['student_id'] = df['student_id'].astype(str).str.strip().str.upper()
    df = df[~df['student_id'].isin(['', 'NONE', 'NAN'])]
    if exclude:
        df = df[~df['student_id'].str.contains(exclude, case=False, regex=True)]
    df = df[df['chapter'].isin(chapters)]
    df['ts'] = pd.to_datetime(df['ts'], utc=True, errors='coerce', format='mixed')
    if since:
        df = df[df['ts'] >= pd.Timestamp(since, tz='UTC')]
    df['is_correct'] = to_bool(df['is_correct'])
    for c in ('attempts', 'final_score', 'total', 'confidence', 'elapsed_sec', 'hints_used'):
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df['week'] = df['chapter'].map(WEEK_NAME).fillna(df['chapter'])
    # 同一學生同一題若時間缺漏，用頁面內的 attempts 序號排序
    return df.sort_values(['student_id', 'ts', 'attempts'], na_position='last').reset_index(drop=True)


# ── 分析 ─────────────────────────────────────────────────────────
def per_item(df):
    """每位學生 × 每題：第一次是否答對、最後有沒有答對、答對前試了幾次。"""
    a = df[(df['event_type'] == 'answer') & df['question_id'].notna() & df['is_correct'].notna()]
    rows = []
    for (sid, ch, game, qid), g in a.groupby(['student_id', 'chapter', 'game', 'question_id'], sort=False):
        ok = g['is_correct'].tolist()
        first_ok = ok.index(True) + 1 if True in ok else None
        mis = g.loc[g['is_correct'] == False, 'misconception'].dropna().tolist()  # noqa: E712
        rows.append({'student_id': sid, 'chapter': ch, 'game': game, 'question_id': qid,
                     'topic': g['topic'].dropna().iloc[0] if g['topic'].notna().any() else None,
                     'qtype': g['qtype'].dropna().iloc[0] if g['qtype'].notna().any() else None,
                     'first_correct': ok[0], 'ever_correct': first_ok is not None,
                     'tries_to_correct': first_ok, 'n_tries': len(ok),
                     'misconceptions': ';'.join(mis)})
    return pd.DataFrame(rows)


def summarize(df, items, chapters):
    comp = df[df['event_type'] == 'attempt_complete']
    best = (comp.sort_values('final_score').groupby(['student_id', 'chapter', 'game']).tail(1)
            if len(comp) else comp)

    overview = []
    for ch in chapters:
        d, it, b = df[df['chapter'] == ch], items[items['chapter'] == ch] if len(items) else items, \
            best[best['chapter'] == ch] if len(best) else best
        for game in sorted(d['game'].dropna().unique()) or [None]:
            dg = d[d['game'] == game] if game else d
            ig = it[it['game'] == game] if game and len(it) else it
            bg = b[b['game'] == game] if game and len(b) else b
            n = dg['student_id'].nunique()
            overview.append({
                '週': WEEK_NAME.get(ch, ch), 'chapter': ch, '活動': game or '（無紀錄）',
                '參與人數': n, '完成人數': bg['student_id'].nunique() if len(bg) else 0,
                '完成率%': round(100 * bg['student_id'].nunique() / n, 1) if n and len(bg) else None,
                '題數': ig['question_id'].nunique() if len(ig) else 0,
                '首答正確率%': round(100 * ig['first_correct'].mean(), 1) if len(ig) else None,
                '最終答對率%': round(100 * ig['ever_correct'].mean(), 1) if len(ig) else None,
                '平均分數': round(bg['final_score'].mean(), 1) if len(bg) else None,
                '滿分': bg['total'].max() if len(bg) else None,
                '平均用時(分)': round(bg['elapsed_sec'].mean() / 60, 1) if len(bg) and bg['elapsed_sec'].notna().any() else None,
                '平均提示次數': round(bg['hints_used'].mean(), 1) if len(bg) and bg['hints_used'].notna().any() else None,
                '最早紀錄': dg['ts'].min(), '最晚紀錄': dg['ts'].max(),
            })
    overview = pd.DataFrame(overview)

    if not len(items):
        empty = pd.DataFrame()
        return overview, empty, empty, empty, empty

    question = (items.groupby(['chapter', 'game', 'question_id'])
                .agg(topic=('topic', 'first'), 作答人數=('student_id', 'nunique'),
                     首答正確率=('first_correct', 'mean'), 最終答對率=('ever_correct', 'mean'),
                     平均嘗試次數=('n_tries', 'mean'))
                .reset_index())
    for c in ('首答正確率', '最終答對率'):
        question[c] = (100 * question[c]).round(1)
    question['平均嘗試次數'] = question['平均嘗試次數'].round(2)
    question = question.sort_values(['chapter', '首答正確率'])

    topic = (items.dropna(subset=['topic']).groupby(['chapter', 'topic'])
             .agg(題數=('question_id', 'nunique'), 作答人次=('student_id', 'size'),
                  首答正確率=('first_correct', 'mean'))
             .reset_index())
    topic['首答正確率'] = (100 * topic['首答正確率']).round(1)
    topic = topic.sort_values(['chapter', '首答正確率'])

    wrong = df[(df['event_type'] == 'answer') & (df['is_correct'] == False) & df['misconception'].notna()]  # noqa: E712
    mis = (wrong.groupby(['chapter', 'misconception'])
           .agg(題號=('question_id', lambda s: ', '.join(sorted(set(s.dropna())))),
                次數=('student_id', 'size'), 學生數=('student_id', 'nunique'))
           .reset_index())
    n_week = df.groupby('chapter')['student_id'].nunique()
    mis['佔參與學生%'] = (100 * mis['學生數'] / mis['chapter'].map(n_week)).round(1)
    mis = mis.sort_values(['chapter', '學生數'], ascending=[True, False])

    student = (items.groupby(['student_id', 'chapter'])
               .agg(作答題數=('question_id', 'nunique'), 首答正確率=('first_correct', 'mean'),
                    答錯總次數=('n_tries', lambda s: int((s - 1).sum())))
               .reset_index())
    student['首答正確率'] = (100 * student['首答正確率']).round(1)
    if len(best):
        sc = best.groupby(['student_id', 'chapter']).agg(完成活動=('game', lambda s: ', '.join(sorted(s))),
                                                         最佳分數=('final_score', 'max'))
        student = student.merge(sc.reset_index(), on=['student_id', 'chapter'], how='left')
    else:
        student['完成活動'], student['最佳分數'] = None, None
    return overview, question, topic, mis, student


def flag_students(df, student, chapters):
    """需關注：有參與但沒完成、首答正確率在該週後 20%、或缺席後面幾週。"""
    flags = []
    all_ids = sorted(df['student_id'].unique())
    for ch in chapters:
        s = student[student['chapter'] == ch] if len(student) else student
        here = set(df.loc[df['chapter'] == ch, 'student_id'])
        if not here:
            continue
        cut = s['首答正確率'].quantile(0.2) if len(s) >= 5 else None
        for sid in all_ids:
            r = s[s['student_id'] == sid]
            why = []
            if sid not in here:
                why.append('本週沒有紀錄')
            else:
                if r.empty or pd.isna(r['完成活動'].iloc[0]):
                    why.append('有開始但沒有完成')
                if cut is not None and len(r) and r['首答正確率'].iloc[0] <= cut:
                    why.append(f'首答正確率 {r["首答正確率"].iloc[0]}%（本週後 20%）')
            if why:
                flags.append({'student_id': sid, '週': WEEK_NAME.get(ch, ch), '原因': '；'.join(why)})
    f = pd.DataFrame(flags)
    if len(f):
        cnt = f.groupby('student_id').size().rename('被標記週數')
        f = f.merge(cnt, on='student_id').sort_values(['被標記週數', 'student_id'], ascending=[False, True])
    return f


# ── 輸出 ─────────────────────────────────────────────────────────
def md_table(d, cols, n=None):
    d = d[cols].head(n) if n else d[cols]
    if not len(d):
        return '（無）\n'
    fmt = lambda v: '' if pd.isna(v) else (f'{v:g}' if isinstance(v, float) else str(v))
    lines = ['| ' + ' | '.join(cols) + ' |', '|' + '---|' * len(cols)]
    lines += ['| ' + ' | '.join(fmt(v) for v in row) + ' |' for row in d.itertuples(index=False)]
    return '\n'.join(lines) + '\n'


def tw(t):
    return '?' if pd.isna(t) else t.tz_convert('Asia/Taipei').strftime('%Y-%m-%d %H:%M')


def write_report(out, df, overview, question, topic, mis, student, flags, chapters, source):
    out.mkdir(parents=True, exist_ok=True)
    L = [f'# 互動實驗室學習狀況報告（{", ".join(chapters)}）', '',
         f'資料來源：{source}；事件 {len(df)} 筆、學生 {df["student_id"].nunique()} 人；'
         f'紀錄期間 {tw(df["ts"].min())} – {tw(df["ts"].max())}（台北時間）', '',
         '首答正確率＝學生第一次作答就答對的比例（最能反映理解程度）；'
         '最終答對率＝看過提示、重試後有答對的比例。', '',
         '## 各週概覽', '',
         md_table(overview, ['週', '活動', '參與人數', '完成人數', '完成率%', '首答正確率%',
                             '最終答對率%', '平均分數', '滿分', '平均用時(分)', '平均提示次數'])]
    for ch in chapters:
        L += [f'## {WEEK_NAME.get(ch, ch)}', '']
        if not (df['chapter'] == ch).any():
            L += ['本週沒有任何紀錄（頁面可能沒有接 assess_firebase.js，或學生沒有登入學號）。', '']
            continue
        if len(question):
            L += ['**最難的 5 題（首答正確率最低）**', '',
                  md_table(question[question['chapter'] == ch],
                           ['game', 'question_id', 'topic', '作答人數', '首答正確率', '最終答對率', '平均嘗試次數'], 5)]
        if len(topic):
            L += ['**各主題首答正確率**', '',
                  md_table(topic[topic['chapter'] == ch], ['topic', '題數', '作答人次', '首答正確率'])]
        if len(mis):
            L += ['**最常見的迷思（答錯時記錄的代碼）**', '',
                  md_table(mis[mis['chapter'] == ch], ['misconception', '題號', '學生數', '佔參與學生%', '次數'], 8)]
    L += ['## 需關注的學生', '',
          md_table(flags, ['student_id', '週', '原因', '被標記週數']) if len(flags) else '（無）\n']
    (out / 'report.md').write_text('\n'.join(L), encoding='utf-8')

    xlsx = out / 'student_events_report.xlsx'
    raw = df.copy()
    raw['ts'] = raw['ts'].dt.tz_convert('Asia/Taipei').dt.tz_localize(None)
    ov = overview.copy()
    for c in ('最早紀錄', '最晚紀錄'):
        ov[c] = pd.to_datetime(ov[c]).dt.tz_convert('Asia/Taipei').dt.tz_localize(None)
    with pd.ExcelWriter(xlsx, engine='openpyxl') as w:
        for name, d in [('概覽', ov), ('題目', question), ('主題', topic), ('迷思', mis),
                        ('學生', student), ('需關注', flags), ('原始資料', raw)]:
            (d if len(d) else pd.DataFrame({'說明': ['無資料']})).to_excel(w, sheet_name=name, index=False)
            ws = w.sheets[name]
            ws.freeze_panes = 'A2'
            for col in ws.columns:
                width = max(len(str(c.value or '')) for c in col[:200])
                ws.column_dimensions[col[0].column_letter].width = min(max(8, width * 1.3), 50)
    return out / 'report.md', xlsx


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')  # Windows 主控台預設 cp950
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument('--firestore', metavar='KEY.json', help='Firebase 服務帳戶金鑰')
    src.add_argument('--supabase', action='store_true', help='從 Supabase 讀（需 SUPABASE_KEY）')
    src.add_argument('--file', help='已匯出的 .csv / .json / .ndjson / .xlsx')
    ap.add_argument('--chapters', default=','.join(DEFAULT_CHAPTERS))
    ap.add_argument('--since', help='只看此日期之後，例如 2026-09-01')
    ap.add_argument('--exclude', help='排除學號的正規表示式，例如 "test|demo"')
    ap.add_argument('--out', default='teacher/student_events_report')
    a = ap.parse_args()

    chapters = [c.strip() for c in a.chapters.split(',') if c.strip()]
    if a.firestore:
        raw, source = load_firestore(a.firestore, chapters), 'Firestore'
    elif a.supabase:
        raw, source = load_supabase(chapters), 'Supabase（無 topic / 迷思 / 用時欄位）'
    else:
        raw, source = load_file(a.file), a.file
    if not len(raw):
        sys.exit('沒有讀到任何紀錄。')

    df = clean(raw, chapters, a.since, a.exclude)
    if not len(df):
        sys.exit('篩選後沒有紀錄，請檢查 --chapters / --since / --exclude。')
    items = per_item(df)
    overview, question, topic, mis, student = summarize(df, items, chapters)
    flags = flag_students(df, student, chapters)
    md, xlsx = write_report(Path(a.out), df, overview, question, topic, mis, student, flags, chapters, source)
    print(overview[['週', '活動', '參與人數', '完成人數', '首答正確率%', '最終答對率%']].to_string(index=False))
    print(f'\n報告：{md}\nExcel：{xlsx}')


if __name__ == '__main__':
    main()
