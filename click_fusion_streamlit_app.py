import streamlit as st
from textwrap import dedent
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="1 kHz Click Fusion (Two-Burst)", page_icon="🎧", layout="centered")
st.title("🎧 1 kHz Click Fusion (Two-Burst) — Streamlit")

st.markdown("""
**使い方（必読）**
- 有線・密閉型ヘッドホン必須（Bluetooth/スピーカー不可）
- iPhone/Safari の場合は**最初に「オーディオ開始」**をタップしないと音が出ません
- レベル（音量）は**各耳で固定**（SRT + 40–50 dB SL もしくは MCL）にしてください
""")

# --- Controls on Streamlit side (mirrored into the HTML) ---
ear = st.radio("Ear（片耳/両耳）", ["R", "L", "Both"], horizontal=True, index=0)
gap = st.slider("Gap (ms)", 1.0, 20.0, 10.0, 0.5)
dur = st.slider("Tone-burst 長さ (ms, Hann)", 3.0, 12.0, 7.0, 0.5)
rove = st.checkbox("±3 dB ロービング（研究用。通常はOFF）", value=False)

st.divider()

html = dedent(f"""
<!doctype html>
<meta charset="utf-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans JP", sans-serif; color:#111; }}
  fieldset {{ border:1px solid #ddd; padding:12px 14px; border-radius:10px; margin:14px 0; }}
  legend {{ padding:0 6px; font-weight:700; }}
  .row {{ margin:8px 0; display:flex; align-items:center; gap:8px; flex-wrap:wrap; }}
  button {{ padding:8px 12px; border-radius:10px; border:1px solid #ddd; background:#fff; }}
  button.primary {{ background:#0ea5e9; color:#fff; border-color:#0ea5e9; }}
  .note {{ color:#555; font-size:0.9rem; }}
  .pill {{ padding:2px 10px; border-radius:999px; background:#f3f4f6; }}
</style>

<div>
  <button id="start">🔊 オーディオ開始（最初に押す）</button>
  <span class="pill">SR=48 kHz / 1 kHz / Hann {dur:.1f} ms / Gap {gap:.1f} ms / Ear {ear}</span>
  <div class="note">有線ヘッドホン／EQ・空間オーディオOFF。音量は各耳で固定してください。</div>

  <fieldset>
    <legend>再生</legend>
    <div class="row">
      <button id="play1">▶ 1バースト（同長ダミー）</button>
      <button id="play2" class="primary">▶ 2バースト</button>
      <button id="playRand">🎲 ランダム (1 or 2)</button>
    </div>
  </fieldset>
</div>

<script>
let ctx=null, sr=48000;
const FREQ = 1000;                  // 1 kHz
const BURST_MS = {dur:.4f};         // トーン・バースト長
const GAP_MS = {gap:.4f};           // ギャップ
const EAR = "{ear}";                // 'L' | 'R' | 'Both'
const ROVING = {str(rove).lower()}; // true/false
const TARGET_RMS = 0.03;

function rms(a){{ let s=0; for(let i=0;i<a.length;i++) s+=a[i]*a[i]; return Math.sqrt(s/a.length); }}
function db2lin(db){{ return Math.pow(10, db/20); }}

document.getElementById('start').onclick = async ()=>{
  ctx = new (window.AudioContext||window.webkitAudioContext)({sampleRate:48000});
  await ctx.resume(); sr = ctx.sampleRate;
  alert("オーディオ開始（SR="+sr+" Hz）");
};

function makeToneBurst(freq=FREQ, ms=BURST_MS){
  const n = Math.max(8, Math.round(sr*ms/1000));
  const w = new Float32Array(n);
  for(let i=0;i<n;i++){ // Hann
    const han = 0.5 - 0.5*Math.cos(2*Math.PI*i/(n-1));
    w[i] = Math.sin(2*Math.PI*freq*(i/sr)) * han;
  }
  // peak normalize then RMS tune per stimulus
  let pk = 0; for(let i=0;i<n;i++) pk = Math.max(pk, Math.abs(w[i]));
  if(pk>1e-9){ for(let i=0;i<n;i++) w[i] /= pk; }
  return w;
}

function toBuffer(L, R){
  const buf = ctx.createBuffer(2, L.length, sr);
  buf.copyToChannel(L, 0); buf.copyToChannel(R, 1);
  return buf;
}

function assembleTwoBurst(gapMs=GAP_MS, ear=EAR){
  const tb = makeToneBurst();
  const gapN = Math.round(sr*gapMs/1000);
  const total = tb.length + gapN + tb.length;
  let L = new Float32Array(total), R = new Float32Array(total);

  // place bursts
  const add=(dst,src,off)=>{{ for(let i=0;i<src.length && off+i<dst.length;i++) dst[off+i]+=src[i]; }};
  if(ear==='L'||ear==='Both'){{ add(L,tb,0); add(L,tb,tb.length+gapN); }}
  if(ear==='R'||ear==='Both'){{ add(R,tb,0); add(R,tb,tb.length+gapN); }}

  // RMS align (active channel参考) + optional roving
  let refCh = (ear==='L')? L : (ear==='R')? R : L; // Both→L基準
  const ref = rms(refCh);
  const k = (ref>1e-9)? (TARGET_RMS/ref) : 1.0;
  for(let i=0;i<L.length;i++){{ L[i]*=k; R[i]*=k; }}
  if(ROVING){{ const kk=db2lin((Math.random()*6)-3); for(let i=0;i<L.length;i++){{ L[i]*=kk; R[i]*=kk; }} }}

  return toBuffer(L,R);
}

function assembleOneLike(gapMs=GAP_MS, ear=EAR){
  const tb = makeToneBurst();
  const gapN = Math.round(sr*gapMs/1000);
  const total = tb.length + gapN + tb.length;
  let L = new Float32Array(total), R = new Float32Array(total);

  const add=(dst,src,off)=>{{ for(let i=0;i<src.length && off+i<dst.length;i++) dst[off+i]+=src[i]; }};
  if(ear==='L'||ear==='Both') add(L,tb,0);
  if(ear==='R'||ear==='Both') add(R,tb,0);

  let refCh = (ear==='L')? L : (ear==='R')? R : L;
  const ref = rms(refCh);
  const k = (ref>1e-9)? (TARGET_RMS/ref) : 1.0;
  for(let i=0;i<L.length;i++){{ L[i]*=k; R[i]*=k; }}
  if(ROVING){{ const kk=db2lin((Math.random()*6)-3); for(let i=0;i<L.length;i++){{ L[i]*=kk; R[i]*=kk; }} }}

  return toBuffer(L,R);
}

function playBuffer(buf){
  const node = ctx.createBufferSource();
  node.buffer = buf; node.connect(ctx.destination); node.start();
}

document.getElementById('play1').onclick = ()=>{
  if(!ctx) return alert("先に『オーディオ開始』を押してください。");
  playBuffer( assembleOneLike() );
};
document.getElementById('play2').onclick = ()=>{
  if(!ctx) return alert("先に『オーディオ開始』を押してください。");
  playBuffer( assembleTwoBurst() );
};
document.getElementById('playRand').onclick = ()=>{
  if(!ctx) return alert("先に『オーディオ開始』を押してください。");
  const two = Math.random() < 0.5;
  playBuffer( two ? assembleTwoBurst() : assembleOneLike() );
};
</script>
""")

st.components.v1.html(html, height=260, scrolling=False)

# --- Simple response logger on Streamlit side ---
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
    clear = st.button("ログを全消去")

if add and heard != "未選択":
    st.session_state.log.append(dict(
        time=datetime.now().isoformat(timespec="seconds"),
        ear=ear, gap_ms=gap, burst_ms=dur, roving=rove,
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
                       file_name="click_fusion_1k_log.csv", mime="text/csv")