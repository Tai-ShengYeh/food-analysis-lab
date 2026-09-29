// 食品分析形成性評量 — Firebase / Supabase 共用模組（沿用 my-teaching-tools-517a0 / student_events）
//
// 設計：與既有 game_firebase.js 同一條資料管線
//   - 主儲存：Firestore collection `student_events`（schemaless，存完整富欄位）
//   - 鏡像  ：Supabase `student_events`（固定欄位，只送原有欄位，不送富欄位，避免 400）
//   - 富欄位（confidence / tier2_correct / bloom / qtype / misconception / topic）只進 Firestore
//
// 用法（評量引擎 / 投影片 quiz）：
//   <script type="module" src="assess_firebase.js"></script>
//   await window.AssessFB.init({ chapter:'L18', game:'assess' });   // 顯示學號 modal
//   window.AssessFB.log({ event_type:'answer', question_id:'L18-01', is_correct:true,
//                         confidence:3, qtype:'mcq', bloom:'理解', topic:'光子能量' });
//   window.AssessFB.log({ event_type:'attempt_complete', final_score:18, total:20 });

import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.13.0/firebase-app.js';
import { getFirestore, addDoc, collection, serverTimestamp }
  from 'https://www.gstatic.com/firebasejs/10.13.0/firebase-firestore.js';

// ── 設定 ─────────────────────────────────────────────────────────
// 先試 Hosting 的 /__/firebase/init.json；非 Hosting 環境用公開 config 後備（與 ch7 一致）。
const FALLBACK_CONFIG = {
  apiKey: "AIzaSyCTLhRf7jcJH_AwUzbV4MawkrKNPrIVG5Y",
  authDomain: "my-teaching-tools-517a0.firebaseapp.com",
  projectId: "my-teaching-tools-517a0",
  storageBucket: "my-teaching-tools-517a0.firebasestorage.app",
  messagingSenderId: "244288457011",
  appId: "1:244288457011:web:4b3ff8a846a6c50b169646"
};
const SUPABASE_URL = 'https://qmldcjkllisvfgegkfsz.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFtbGRjamtsbGlzdmZnZWdrZnN6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzExMjM5ODYsImV4cCI6MjA4NjY5OTk4Nn0.Bfj0W7HN_n_vcjGe5502Chamk0YV-de8a0fxF4Nyczk';

let db = null;
let readyResolve;
const ready = new Promise(r => { readyResolve = r; });

(async () => {
  let cfg = FALLBACK_CONFIG;
  try {
    const r = await fetch('/__/firebase/init.json');
    if (r.ok) cfg = await r.json();
  } catch (e) { /* 非 Hosting，用 fallback */ }
  try { db = getFirestore(initializeApp(cfg)); }
  catch (e) { console.warn('[AssessFB] Firestore 初始化失敗：', e.message); }
  readyResolve();
})();

// ── Session ─────────────────────────────────────────────────────
const COURSE_MAP = { 'fa':'4y_food_analysis','4y_fa':'4y_food_analysis',
  '5z_fa':'5z_food_analysis','fc':'4y_food_chem','vn':'vn_chinese','glp1':'glp1_chinese' };
const SESSION = { course_id:'4y_food_analysis', class_id:'A', chapter:null, game:'assess', ready:false };
const SID_KEY = 'food_analysis_student_id'; // 與 game_firebase.js 共用學號

export function getStudentId(){ return localStorage.getItem(SID_KEY) || null; }
export function setStudentId(id){ localStorage.setItem(SID_KEY, id); }
export function clearStudentId(){ localStorage.removeItem(SID_KEY); }

// ── Supabase 鏡像（只送原有固定欄位）────────────────────────────
function logToSupabase(p){
  fetch(`${SUPABASE_URL}/rest/v1/student_events`, {
    method:'POST', keepalive:true,
    headers:{ apikey:SUPABASE_ANON_KEY, Authorization:`Bearer ${SUPABASE_ANON_KEY}`,
      'Content-Type':'application/json', Prefer:'return=minimal' },
    body: JSON.stringify({
      student_id:p.student_id, course_id:p.course_id, class_id:p.class_id,
      chapter:p.chapter, game:p.game, event_type:p.event_type,
      question_id:p.question_id, is_correct:p.is_correct, attempts:p.attempts,
      final_score:p.final_score, user_agent:p.user_agent, client_ts:new Date().toISOString()
    })
  }).catch(()=>{});
}

// ── 寫入事件 ─────────────────────────────────────────────────────
export async function log(data){
  await ready;
  const sid = getStudentId();
  if(!SESSION.ready || !sid) return;
  const base = {
    student_id:sid, course_id:SESSION.course_id, class_id:SESSION.class_id,
    chapter:data.chapter ?? SESSION.chapter, game:SESSION.game,
    event_type:data.event_type,
    question_id:data.question_id ?? null,
    is_correct:data.is_correct === undefined ? null : data.is_correct,
    attempts:data.attempts ?? null,
    final_score:data.final_score ?? null,
    user_agent:(navigator.userAgent||'').slice(0,200),
  };
  // 原欄位 → Supabase
  logToSupabase(base);
  // 完整富欄位 → Firestore
  if(db){
    try{
      await addDoc(collection(db,'student_events'), {
        ...base,
        // 富欄位（Firestore 專屬）
        qtype:data.qtype ?? null,
        bloom:data.bloom ?? null,
        topic:data.topic ?? null,
        confidence:data.confidence ?? null,
        tier2_correct:data.tier2_correct === undefined ? null : data.tier2_correct,
        misconception:data.misconception ?? null,
        mode:data.mode ?? null,
        total:data.total ?? null,
        timestamp:serverTimestamp(),
      });
    }catch(e){ console.error('[AssessFB] Firestore 寫入失敗：', e); }
  }
}

// ── 學號 modal（亮色，配合 bright 主題）─────────────────────────
function injectModal(){
  if(document.getElementById('afb-style')) return;
  const css = `
  .afb-ov{position:fixed;inset:0;background:rgba(30,41,59,.55);backdrop-filter:blur(4px);
    display:none;align-items:center;justify-content:center;z-index:99999;padding:20px;
    font-family:'Noto Sans TC',sans-serif;}
  .afb-ov.show{display:flex;}
  .afb-card{background:#fff;border-radius:18px;max-width:420px;width:100%;padding:30px 26px;
    box-shadow:0 20px 60px rgba(0,0,0,.25);}
  .afb-card h2{font-size:1.3rem;margin:0 0 6px;color:#4f46e5;font-weight:900;}
  .afb-card .h{font-size:.86rem;color:#64748b;margin-bottom:16px;line-height:1.6;}
  .afb-card input{width:100%;padding:13px 15px;border:2px solid #e2e8f0;border-radius:11px;
    font-size:1.1rem;font-family:inherit;outline:none;box-sizing:border-box;}
  .afb-card input:focus{border-color:#6366f1;}
  .afb-err{color:#ef4444;font-size:.82rem;margin-top:8px;min-height:18px;}
  .afb-card button{margin-top:14px;width:100%;background:#6366f1;color:#fff;border:none;
    padding:13px;border-radius:11px;font-size:1rem;font-weight:700;cursor:pointer;font-family:inherit;}
  .afb-card button:hover{background:#4f46e5;}
  .afb-pill{position:fixed;top:10px;right:12px;background:#fff;border:1px solid #e2e8f0;
    color:#475569;padding:6px 13px;border-radius:100px;font-size:.78rem;z-index:9999;
    box-shadow:0 2px 10px rgba(0,0,0,.08);font-family:'Noto Sans TC',sans-serif;}
  .afb-pill .c{color:#94a3b8;margin-right:5px;}
  .afb-pill .ch{margin-left:8px;color:#6366f1;text-decoration:underline;cursor:pointer;}`;
  const s=document.createElement('style'); s.id='afb-style'; s.textContent=css; document.head.appendChild(s);
}
function showPill(sid){
  let p=document.getElementById('afb-pill');
  if(!p){ p=document.createElement('div'); p.className='afb-pill'; p.id='afb-pill'; document.body.appendChild(p); }
  p.innerHTML=`<span class="c">${SESSION.course_id.replace('4y_','4技').replace('5z_','5專').replace('food_analysis','食分')}·${SESSION.class_id}</span>🎓 ${sid} <span class="ch" id="afb-ch">更換</span>`;
  document.getElementById('afb-ch').onclick=()=>{ clearStudentId(); p.remove(); location.reload(); };
}
function ensureStudentId(){
  injectModal();
  return new Promise(resolve=>{
    const ex=getStudentId(); if(ex){ showPill(ex); resolve(ex); return; }
    const ov=document.createElement('div'); ov.className='afb-ov show'; ov.innerHTML=`
      <div class="afb-card"><h2>📝 請輸入學號</h2>
      <div class="h">用來記錄你的作答與學習進步。下次同系列不用重輸入。<br>例如 B11234567</div>
      <input id="afb-in" type="text" autocomplete="off" placeholder="例如 B11234567" maxlength="20">
      <div class="afb-err" id="afb-e"></div>
      <button id="afb-ok">確認</button></div>`;
    document.body.appendChild(ov);
    const inp=ov.querySelector('#afb-in'), err=ov.querySelector('#afb-e');
    setTimeout(()=>inp.focus(),100);
    function go(){ const v=inp.value.trim();
      if(!/^[A-Za-z0-9_\-]{1,20}$/.test(v)){ err.textContent='只能英文/數字/底線/連字號，1–20 字。'; return; }
      setStudentId(v); ov.remove(); showPill(v); resolve(v); }
    ov.querySelector('#afb-ok').onclick=go;
    inp.addEventListener('keydown',e=>{ if(e.key==='Enter')go(); });
  });
}

// ── 對外主 API ───────────────────────────────────────────────────
export async function init(opts={}){
  const params=new URLSearchParams(location.search);
  const classId=opts.class_id || params.get('class') || 'A';
  let course=opts.course || params.get('course');
  if(!course) course = classId==='B' ? '5z_food_analysis' : '4y_food_analysis';
  if(COURSE_MAP[course]) course=COURSE_MAP[course];
  SESSION.course_id=course; SESSION.class_id=classId;
  SESSION.chapter=opts.chapter || params.get('chapter') || 'L00';
  SESSION.game=opts.game || 'assess';
  SESSION.ready=true;
  await ensureStudentId();
  return SESSION;
}

// 同時掛到 window，讓非 module 的內嵌 <script> 也能呼叫
window.AssessFB = { init, log, getStudentId, setStudentId, clearStudentId, SESSION };

// 自動初始化（投影片用法）：
//   <script type="module" src="/assess_firebase.js" data-chapter="L34" data-game="minigame"></script>
// 有 data-chapter 屬性就自動開 session（顯示學號 modal）；assess.html 不帶此屬性，改為手動 init。
const _self = document.querySelector('script[src*="assess_firebase.js"][data-chapter]');
if (_self) init({ chapter: _self.dataset.chapter, game: _self.dataset.game || 'minigame' });
