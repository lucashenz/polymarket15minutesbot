from __future__ import annotations

import json
from datetime import datetime, timezone

import streamlit as st

from tracker import PolymarketAPIError, collect_event_probabilities

st.set_page_config(page_title="Polymarket Real-Time Probability Tracker", layout="centered")

st.markdown(
    """
    <style>
    .main { background-color: #0f1117; color: #f5f5f5; }
    .event-card {
        background: #1a1f2b;
        border: 1px solid #2a3040;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
    }
    .muted { color: #9ba3b4; font-size: 0.9rem; }
    .trend-up { color: #2ecc71; font-weight: 700; }
    .trend-down { color: #e74c3c; font-weight: 700; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📈 Polymarket Real-Time Probability Tracker")

with st.sidebar:
    slug = st.text_input("Event slug", value="bitcoin-up-or-down-february-13-9am-et")
    interval_sec = st.number_input("Auto refresh (seconds)", min_value=10, max_value=3600, value=60, step=10)
    use_mid = st.toggle("Use mid-price (recommended)", value=True)

if "history" not in st.session_state:
    st.session_state.history = {}

try:
    data = collect_event_probabilities(slug)
except PolymarketAPIError as exc:
    st.error(f"Erro ao buscar dados da Polymarket: {exc}")
    st.stop()

labels = data["labels"]
probs = data["mid_probabilities"] if use_mid else data["direct_probabilities"]

p0 = probs[0] if probs[0] is not None else 0.0
p1 = probs[1] if probs[1] is not None else 0.0

st.markdown(
    f"""
    <div class="event-card">
      <h3 style="margin:0;">{data['event_title']}</h3>
      <div class="muted">{data['market_question']}</div>
      <div class="muted">Atualizado em {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

prev = st.session_state.history.get(slug)

col1, col2 = st.columns(2)
with col1:
    st.subheader(labels[0])
    st.progress(min(max(p0, 0.0), 1.0))
    st.metric("Probabilidade", f"{p0 * 100:.1f}%")
with col2:
    st.subheader(labels[1])
    st.progress(min(max(p1, 0.0), 1.0))
    st.metric("Probabilidade", f"{p1 * 100:.1f}%")

if prev:
    d0 = p0 - prev[0]
    arrow = "⬆️" if d0 >= 0 else "⬇️"
    css_class = "trend-up" if d0 >= 0 else "trend-down"
    st.markdown(
        f"<p class='{css_class}'>Tendência (vs atualização anterior): {arrow} {d0 * 100:+.2f} p.p.</p>",
        unsafe_allow_html=True,
    )

with st.expander("Detalhes técnicos"):
    st.json(
        {
            "direct_probabilities": data["direct_probabilities"],
            "mid_probabilities": data["mid_probabilities"],
            "snapshots": [snapshot.__dict__ for snapshot in data["snapshots"]],
        }
    )

st.session_state.history[slug] = (p0, p1)

st.markdown(f"<meta http-equiv='refresh' content='{int(interval_sec)}'>", unsafe_allow_html=True)
