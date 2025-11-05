# click_fusion_streamlit_app.py
# Streamlit + Web Audio: Two-burst fusion test
# - Tone（推奨 / 1 kHz / Hann）と Click（ノイズ・バースト）を切替可
# - iPhone/ヘッドホン挿抜でも鳴るように Web Audio を堅牢化
#   * AudioContext: sampleRate固定を撤廃（ハードに委譲）
#   * 再生直前に await resume()
#   * devicechange で close→再生成（route切替時の無音対策）

import json
from textwrap import dedent
import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Two-Burst Fusion (Tone/Click)", page_icon="🎧", layout="centered")
st.title("🎧 Two-Burst Fusion (Tone / Click) — Streamlit")

st.markdown("""
**使い方（必読）**
- 有線・密閉型ヘッドホン必須（Bluetooth/スピーカー不可）
- **臨床運用はトーン 1 kHz / Hann 7 ms 固定を推奨**（スライダは研究用）
- レベル（音量）は**各耳で固定**（SRT + 40–50 dB SL または MCL）
- iPhoneは **EQ/空間/ヘッドフォン調整/サウンドチェック=OFF**、**モノラル=OFF**、L/Rバランス中央
""")

# ---------------- Streamlit UI ----------------
stim_mode = st.radio("刺激タイプ", ["Tone（推奨）", "Click（ノイズ・バースト）"], index=0, horizontal=True)
ear  = st.radio("Ear（片耳/両耳）", ["R", "L", "Both"], index=0, horizontal=True)
gap  = st.slider("Gap (ms)", 1.0, 20.0, 10.0, 0.5)

colA, colB = st.columns(2)
with colA:
    dur  = st.slider("Tone-burst 長さ (ms, Hann) — ※臨床は 7 ms 固定推奨", 3.0, 12.0, 7.0, 0.5)
with colB:
    click_ms = st.slider("Click 長さ (ms, Hann)", 0.1, 2.0, 0.6, 0.05)
rove = st.checkbox("±3 dB ロービング（研究用。通常はOFF）", value=False)

cfg = {
    "stim": "tone" if stim_mode.startswith("Tone") else "click",
    "gap": gap, "dur": dur, "click_ms": click_ms,
    "ear": ear, "rove": rove,
    "freq_hz": 1000,        # 1 kHz 固定
    "target_rms": 0.03,     # 再生側でRMS調整
    # sampleRateはJS側で自動交渉（固定しない）
}

st.divider()

# ---------------- HTML/JS Embedding ----------------
html = dedent(r"""
<!doctype html>
<meta charset="utf-8">
<style>
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Noto Sans JP",sans-serif;color:#111}
  fieldset{border:1px solid #ddd;padding:12px 14px;border-radius:10px;margin:14px 0}
  legend{padding:0 6px;font-weight:700}
  .row{margin:8px 0;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
  button{padding:8px 12px;border-radius:10px;border:1px solid #ddd;background:#fff}
  button.primary{background:#0ea5e9;color:#fff;border-color:#0ea5e9}
  .note{color:#555;font-size:0.9rem}
  .pill{padding:2px 10px;border-radius:999px;background:#f3f4f6}
</style>

<div>
  <span class="pill" id="pill"></span>
  <div class="note">
    有線ヘッドホン／EQ・空間オーディオ・ヘッドフォン調整はOFF。音量は各耳で固定。<br>
    臨床は <b>Tone 1 kHz / Hann 7 ms 固定推奨</b>（Clickは切替で使用可）。
  </div>
  <fieldset>
    <legend>再生</legend>
    <div class="row">
      <button id="play1">▶ 1発（同長ダミー）</button>
      <button id="play2" class="primary">▶ 2発</button>
      <button id="playRand">🎲 ランダム (1 or 2)</button>
    </div>
  </fieldset>
</div>

<script id="cfg" type="application/json">{CFG_JSON}</script>

<script>
// ====== Web Audio: robust handling for iOS + route changes ======
let ctx_global = null;

// AudioContextを作成（sampleRateは固定指定しない）
async function createCtx(){
  try {
    return new (window.AudioContext||window.webkitAudioContext)();
  } catch(e) {
    return new (window.AudioContext||window.webkitAudioContext)();
  }
}

// 必ず resume() を await して有効化
async function ensureCtx(){
  if (!ctx_global) ctx_global = await createCtx();
  if (ctx_global.state === "suspended") {
    try { await ctx_global.resume(); } catch(e) {}
  }
  return ctx_global;
}

// ヘッドホン抜き差しなどのデバイス切替で無音化しないように再生成
if (navigator.mediaDevices?.addEventListener) {
  navigator.mediaDevices.addEventListener("devicechange", async () => {
    try {
      if (ctx_global) { try { await ctx_global.close(); } catch(e){} }
      ctx_global = await createCtx();
      // 1msの無音を鳴らしてroute確立（ユーザー操作直後に走るのが理想だが保険として）
      const sr = ctx_global.sampleRate || 48000;
      const buf = ctx_global.createBuffer(2, Math.max(1, Math.floor(sr*0.001)), sr);
      const node = ctx_global.createBufferSource(); node.buffer = buf;
      node.connect(ctx_global.destination); node.start();
    } catch(e) {}
  });
}

// ====== Stimulus Synthesis ======
function rms(a){ let s=0; for(let i=0;i<a.length;i++) s+=a[i]*a[i]; return Math.sqrt(s/a.length); }
function db2lin(db){ return Math.pow(10, db/20); }

const CFG = JSON.parse(document.getElementById('cfg').textContent);
let MODE   = CFG.stim;       // "tone" | "click"
let GAP_MS = CFG.gap;
let TB_MS  = CFG.dur;        // tone burst ms
let CK_MS  = CFG.click_ms;   // click burst ms
let EAR    = CFG.ear;        // "L" | "R" | "Both"
let ROVING = CFG.rove;
const FREQ = CFG.freq_hz || 1000;
const TARGET_RMS = CFG.target_rms || 0.03;

// バッジ表示
document.addEventListener('DOMContentLoaded', ()=>{
  const pill = document.getElementById('pill');
  const modeTxt = (MODE==="tone") ? `Tone ${FREQ} Hz / Hann ${TB_MS.toFixed(1)} ms`
                                  : `Click (noise) / Hann ${CK_MS.toFixed(2)} ms`;
  pill.textContent = `${modeTxt} / Gap ${GAP_MS.toFixed(1)} ms / Ear ${EAR}`;
});

function makeToneBurst(freq=FREQ, ms=TB_MS, sr){
  const n = Math.max(8, Math.round(sr*ms/1000));
  const w = new Float32Array(n);
  for(let i=0;i<n;i++){
    const han = 0.5 - 0.5*Math.cos(2*Math.PI*i/(n-1));
    w[i] = Math.sin(2*Math.PI*freq*(i/sr)) * han;
  }
  // peak normalize
  let pk = 0; for(let i=0;i<n;i++) pk = Math.max(pk, Math.abs(w[i]));
  if(pk>1e-9){ for(let i=0;i<n;i++) w[i] /= pk; }
  return w;
}

function makeClickBurst(ms=CK_MS, sr){
  const n = Math.max(8, Math.round(sr*ms/1000));
  const w = new Float32Array(n);
  for(let i=0;i<n;i++) w[i] = (Math.random()*2-1);
  // peak normalize
  let pk = 0; for(let i=0;i<n;i++) pk = Math.max(pk, Math.abs(w[i]));
  if(pk>1e-9){ for(let i=0;i<n;i++) w[i] /= pk; }
  // Hann window
  for(let i=0;i<n;i++){ const han = 0.5 - 0.5*Math.cos(2*Math.PI*i/(n-1)); w[i]*=han; }
  return w;
}

function synthTwoBurst(sr){
  const gapN = Math.round(sr*GAP_MS/1000);
  const unit = (MODE==="tone") ? makeToneBurst(FREQ, TB_MS, sr)
                               : makeClickBurst(CK_MS, sr);
  const total = unit.length + gapN + unit.length;
  let L = new Float32Array(total), R = new Float32Array(total);
  const add=(dst,src,off)=>{ for(let i=0;i<src.length && off+i<dst.length;i++) dst[off+i]+=src[i]; };
  if(EAR==='L'||EAR==='Both'){ add(L,unit,0); add(L,unit,unit.length+gapN); }
  if(EAR==='R'||EAR==='Both'){ add(R,unit,0); add(R,unit,unit.length+gapN); }
  const ref = rms((EAR==='L')?L:(EAR==='R')?R:L);
  const k = (ref>1e-9)? (TARGET_RMS/ref) : 1.0;
  for(let i=0;i<L.length;i++){ L[i]*=k; R[i]*=k; }
  if(ROVING){ const kk=db2lin((Math.random()*6)-3); for(let i=0;i<L.length;i++){ L[i]*=kk; R[i]*=kk; } }
  return {L, R, total};
}

function synthOneLike(sr){
  const gapN = Math.round(sr*GAP_MS/1000);
  const unit = (MODE==="tone") ? makeToneBurst(FREQ, TB_MS, sr)
                               : makeClickBurst(CK_MS, sr);
  const total = unit.length + gapN + unit.length;
  let L = new Float32Array(total), R = new Float32Array(total);
  const add=(dst,src,off)=>{ for(let i=0;i<src.length && off+i<dst.length;i++) dst[off+i]+=src[i]; };
  if(EAR==='L'||EAR==='Both') add(L,unit,0);
  if(EAR==='R'||EAR==='Both') add(R,unit,0);
  const ref = rms((EAR==='L')?L:(EAR==='R')?R:L);
  const k = (ref>1e-9)? (TARGET_RMS/ref) : 1.0;
  for(let i=0;i<L.length;i++){ L[i]*=k; R[i]*=k; }
  if(ROVING){ const kk=db2lin((Math.random()*6)-3); for(let i=0;i<L.length;i++){ L[i]*=kk; R[i]*=kk; } }
  return {L, R, total};
}

// 再生：毎回 ensureCtx() を await し、route切替後のsuspendedに強くする
async function play(getter){
  const ctx = await ensureCtx();
  const sr  = ctx.sampleRate || 48000;
  const {L, R, total} = getter(sr);
  const buf = ctx.createBuffer(2, total, sr);
  buf.copyToChannel(L,0); buf.copyToChannel(R,1);
  try { if (ctx.state === "suspended") await ctx.resume(); } catch(e) {}
  const node = ctx.createBufferSource();
  node.buffer = buf; node.connect(ctx.destination); node.start();
}

// ボタン（async/await で確実にresume→startの順）
document.getElementById('play1').onclick = async ()=>{ await play(synthOneLike);  };
document.getElementById('play2').onclick = async ()=>{ await play(synthTwoBurst); };
document.getElementById('playRand').onclick = async ()=>{
  if (Math.random() < 0.5) { await play(synthTwoBurst); } else { await play(synthOneLike); }
};
</script>
""")

html = html.replace("{CFG_JSON}", json.dumps(cfg))
st.components.v1.html(html, height=320, scrolling=False)

# ---------------- Response Logger ----------------
st.subheader("応答ログ")
if "log" not in st.session_state:
    st.session_state.log = []

col1, col2, col3, col4 = st.columns([1,1,1,2])
with col1:
    heard = st.selectbox("回答", ["未選択","1つ","2つ"], index=0)
with col2:
    ntr = st.number_input("試行番号", min_value=1, value=len(st.session_state.log)+1, step=1)
with col3:
    add = st.button("この条件でログ追加")
with col4:
    clear = st.button("ログ全消去")

if add and heard != "未選択":
    st.session_state.log.append(dict(
        time=datetime.now().isoformat(timespec="seconds"),
        stim=("Tone" if stim_mode.startswith("Tone") else "Click"),
        ear=ear, gap_ms=gap, burst_ms=dur, click_ms=click_ms, roving=rove,
        response=heard, trial=int(ntr),
    ))
    st.success("追加しました。")

if clear:
    st.session_state.log = []
    st.warning("ログを消去しました。")

if st.session_state.log:
    df = pd.DataFrame(st.session_state.log)
    st.dataframe(df, use_container_width=True)
    st.download_button("CSVダウンロード", df.to_csv(index=False).encode("utf-8"),
                       file_name="fusion_test_log.csv", mime="text/csv")
