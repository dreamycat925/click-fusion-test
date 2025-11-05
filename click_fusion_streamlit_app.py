# click_fusion_streamlit_app.py
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

# ----------- UI -----------
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
    "freq_hz": 1000,
    "target_rms": 0.03,
}

st.divider()

# ----------- HTML/JS -----------
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
  audio{display:none}
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

<!-- iOSフォールバック用の隠しaudio -->
<audio id="fallbackAudio"></audio>
<script id="cfg" type="application/json">{CFG_JSON}</script>

<script>
// ===== 環境判定 =====
function isIOS(){
  return /iP(hone|od|ad)/.test(navigator.platform) ||
         (navigator.userAgent.includes("Mac") && "ontouchend" in document);
}
const IOS = isIOS();

// ===== 表示更新 =====
const CFG = JSON.parse(document.getElementById('cfg').textContent);
let MODE   = CFG.stim, GAP_MS = CFG.gap, TB_MS = CFG.dur, CK_MS = CFG.click_ms, EAR = CFG.ear, ROVING = CFG.rove;
const FREQ = CFG.freq_hz || 1000, TARGET_RMS = CFG.target_rms || 0.03;

document.addEventListener('DOMContentLoaded', ()=>{
  const pill = document.getElementById('pill');
  const modeTxt = (MODE==="tone") ? `Tone ${FREQ} Hz / Hann ${TB_MS.toFixed?.(1)||TB_MS} ms`
                                  : `Click (noise) / Hann ${CK_MS.toFixed?.(2)||CK_MS} ms`;
  pill.textContent = `${modeTxt} / Gap ${GAP_MS.toFixed?.(1)||GAP_MS} ms / Ear ${EAR}`;
});

// ===== 数学ユーティリティ =====
function rms(a){ let s=0; for(let i=0;i<a.length;i++) s+=a[i]*a[i]; return Math.sqrt(s/a.length); }
function db2lin(db){ return Math.pow(10, db/20); }

// ====== 刺激合成（共通）======
function makeToneBurst(freq, ms, sr){
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
function makeClickBurst(ms, sr){
  const n = Math.max(8, Math.round(sr*ms/1000));
  const w = new Float32Array(n);
  for(let i=0;i<n;i++) w[i] = (Math.random()*2-1);
  // peak normalize + Hann
  let pk = 0; for(let i=0;i<n;i++) pk = Math.max(pk, Math.abs(w[i]));
  if(pk>1e-9){ for(let i=0;i<n;i++) w[i] /= pk; }
  for(let i=0;i<n;i++){ const han = 0.5 - 0.5*Math.cos(2*Math.PI*i/(n-1)); w[i]*=han; }
  return w;
}
function synthTwoBurstBuffers(sr){
  const gapN = Math.round(sr*GAP_MS/1000);
  const unit = (MODE==="tone") ? makeToneBurst(FREQ, TB_MS, sr) : makeClickBurst(CK_MS, sr);
  const total = unit.length + gapN + unit.length;
  let L = new Float32Array(total), R = new Float32Array(total);
  const add=(dst,src,off)=>{ for(let i=0;i<src.length && off+i<dst.length;i++) dst[off+i]+=src[i]; };
  if(EAR==='L'||EAR==='Both'){ add(L,unit,0); add(L,unit,unit.length+gapN); }
  if(EAR==='R'||EAR==='Both'){ add(R,unit,0); add(R,unit,unit.length+gapN); }
  const ref = rms((EAR==='L')?L:(EAR==='R')?R:L);
  const k = (ref>1e-9)? (TARGET_RMS/ref) : 1.0;
  for(let i=0;i<L.length;i++){ L[i]*=k; R[i]*=k; }
  if(ROVING){ const kk=db2lin((Math.random()*6)-3); for(let i=0;i<L.length;i++){ L[i]*=kk; R[i]*=kk; } }
  return {L,R,total};
}
function synthOneLikeBuffers(sr){
  const gapN = Math.round(sr*GAP_MS/1000);
  const unit = (MODE==="tone") ? makeToneBurst(FREQ, TB_MS, sr) : makeClickBurst(CK_MS, sr);
  const total = unit.length + gapN + unit.length;
  let L = new Float32Array(total), R = new Float32Array(total);
  const add=(dst,src,off)=>{ for(let i=0;i<src.length && off+i<dst.length;i++) dst[off+i]+=src[i]; };
  if(EAR==='L'||EAR==='Both') add(L,unit,0);
  if(EAR==='R'||EAR==='Both') add(R,unit,0);
  const ref = rms((EAR==='L')?L:(EAR==='R')?R:L);
  const k = (ref>1e-9)? (TARGET_RMS/ref) : 1.0;
  for(let i=0;i<L.length;i++){ L[i]*=k; R[i]*=k; }
  if(ROVING){ const kk=db2lin((Math.random()*6)-3); for(let i=0;i<L.length;i++){ L[i]*=kk; R[i]*=kk; } }
  return {L,R,total};
}

// ====== iOSフォールバック：WAVを生成して <audio> で再生 ======
function floatTo16PCM(float32){
  const out = new Int16Array(float32.length);
  for (let i=0; i<float32.length; i++){
    const s = Math.max(-1, Math.min(1, float32[i]));
    out[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
  }
  return out;
}
function makeWavBlob(L, R, sr){
  const numFrames = L.length;
  const numCh = 2;
  const bytesPerSample = 2;
  const blockAlign = numCh * bytesPerSample;
  const byteRate = sr * blockAlign;
  const dataSize = numFrames * blockAlign;
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);

  // RIFF header
  function writeString(off, s){ for(let i=0;i<s.length;i++) view.setUint8(off+i, s.charCodeAt(i)); }
  let offset = 0;
  writeString(offset, 'RIFF'); offset += 4;
  view.setUint32(offset, 36 + dataSize, true); offset += 4;
  writeString(offset, 'WAVE'); offset += 4;
  writeString(offset, 'fmt '); offset += 4;
  view.setUint32(offset, 16, true); offset += 4;              // PCM
  view.setUint16(offset, 1, true); offset += 2;               // PCM format
  view.setUint16(offset, numCh, true); offset += 2;
  view.setUint32(offset, sr, true); offset += 4;
  view.setUint32(offset, byteRate, true); offset += 4;
  view.setUint16(offset, blockAlign, true); offset += 2;
  view.setUint16(offset, 16, true); offset += 2;              // 16-bit
  writeString(offset, 'data'); offset += 4;
  view.setUint32(offset, dataSize, true); offset += 4;

  // interleave
  const L16 = floatTo16PCM(L);
  const R16 = floatTo16PCM(R);
  let i = 0;
  for (let n=0; n<numFrames; n++){
    view.setInt16(44 + i, L16[n], true); i += 2;
    view.setInt16(44 + i, R16[n], true); i += 2;
  }
  return new Blob([buffer], {type:'audio/wav'});
}

// ====== 再生ルーチン（iOSはaudio、その他はWebAudio） ======
let ctx = null;
async function playWithWebAudio(getter){
  if (!ctx) { try { ctx = new (window.AudioContext||window.webkitAudioContext)(); } catch(e) { ctx = null; } }
  if (!ctx) return; // 安全
  if (ctx.state === "suspended") { try { await ctx.resume(); } catch(e){} }
  const sr  = ctx.sampleRate || 48000;
  const {L,R,total} = getter(sr);
  const buf = ctx.createBuffer(2, total, sr);
  buf.copyToChannel(L,0); buf.copyToChannel(R,1);
  try { if (ctx.state === "suspended") await ctx.resume(); } catch(e) {}
  const node = ctx.createBufferSource();
  node.buffer = buf; node.connect(ctx.destination); node.start();
}

async function playWithAudioTag(getter){
  const sr = 44100; // iOSでも無難
  const {L,R} = getter(sr);
  const blob = makeWavBlob(L, R, sr);
  const url = URL.createObjectURL(blob);
  const a = document.getElementById('fallbackAudio');
  a.src = url;
  try { await a.play(); } finally {
    // 再生完了後にURLを破棄（メモリリーク防止）
    a.onended = ()=> { URL.revokeObjectURL(url); a.onended = null; };
  }
}

async function play(getter){
  if (IOS) { await playWithAudioTag(getter); }
  else     { await playWithWebAudio(getter); }
}

// ボタン
document.getElementById('play1').onclick  = async ()=>{ await play(synthOneLikeBuffers);  };
document.getElementById('play2').onclick  = async ()=>{ await play(synthTwoBurstBuffers); };
document.getElementById('playRand').onclick = async ()=>{
  if (Math.random() < 0.5) { await play(synthTwoBurstBuffers); } else { await play(synthOneLikeBuffers); }
};
</script>
""")

html = html.replace("{CFG_JSON}", json.dumps(cfg))
st.components.v1.html(html, height=320, scrolling=False)

# ----------- ロガー -----------
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
