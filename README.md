# Two-Burst Fusion Test (Tone / Click) for Streamlit

**Purpose**  
A browser-based application for conducting **two-burst fusion/separation (gap detection)** tests using 1 kHz tones (recommended) or clicks (noise bursts). The app works seamlessly on iPhone/Safari, requires **no Start button**, and includes **CSV log export** functionality.

---

## Features

- 1 kHz tone bursts (7 ms Hann window recommended) providing comfortable, non-piercing stimuli
- Switchable to click stimuli (noise bursts, default 0.6 ms)
- Adjustable gap (ISI) from 1.0 to 20.0 ms in 0.5 ms increments
- Monaural or binaural presentation modes
- No Start button required: AudioContext automatically initialized/reused during playback
- On-screen response logging with CSV download capability
- Entirely synthesized using Web Audio API (no server-side PortAudio required)

---

## Demo

> (Insert screenshots or GIFs here for visual reference)

---

## Quick Start Guide

1. Connect **wired, closed-back headphones** (Bluetooth/speakers not suitable)
2. Select **stimulus type** (default: Tone; switchable to Click)
3. Configure **Ear** and **Gap** settings (clinical use: Tone with 7 ms fixed recommended)
4. Play **2-burst** sequence (also available: single burst or randomized presentation)
5. Add responses to log and download **CSV** from bottom-right corner

---

## Recommended Clinical Implementation

- **Frequency**: 1,000 Hz (tone)
- **Tone duration**: **7 ms with Hann window** (fixed setting recommended)
- **Gap (ISI)**:
  - Screening: **10 ms** (20 trials; ≥70% "two" responses indicates separation capability)
  - Threshold estimation: Start at **8 ms** and decrease (2-3 trials per step, 2/3 correct criterion)
- **Level**: Fixed per ear (e.g., SRT or 1 kHz PTA + 40-50 dB SL, or MCL)
- **Roving**: Typically **OFF** (use ±2-3 dB only for research requiring cue elimination)
- **Monaural presentation** (alternating ears reduces fatigue)

> When using clicks, **0.6-1.0 ms with Hann window** minimizes sharpness, and **band-limiting (1-4 kHz)** can be beneficial (note: this standard app uses white noise clicks).

---

## Local Installation
```bash
git clone https://github.com/<you>/<repo>.git
cd <repo>
pip install -r requirements.txt
streamlit run click_fusion_streamlit_app.py
```

---

## Browser Access

Open the displayed local URL in your browser (typically `http://localhost:8501`). For iOS/Safari testing, ensure the device is on the same network and access via the network URL provided by Streamlit.