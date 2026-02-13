from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from tracker import PolymarketAPIError, collect_event_probabilities, get_btc_price_usd

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

with st.sidebar:
    slug = st.text_input("Event slug", value="bitcoin-up-or-down-february-13-9am-et")
    use_mid = st.toggle("Use mid-price (recommended)", value=True)

if "history" not in st.session_state:
    st.session_state.history = {}


def _parse_iso_datetime(raw_value: str | None) -> datetime | None:
    if not raw_value or not isinstance(raw_value, str):
        return None

    cleaned = raw_value.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _format_time_left(raw_value: str | None) -> str:
    end_dt = _parse_iso_datetime(raw_value)
    if end_dt is None:
        return "N/D"

    now = datetime.now(timezone.utc)
    remaining = end_dt - now
    if remaining.total_seconds() <= 0:
        return "Encerrado"

    total_seconds = int(remaining.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    return f"{minutes}m {seconds}s"


def render_live_probabilities() -> None:
    try:
        data = collect_event_probabilities(slug)
    except PolymarketAPIError as exc:
        st.error(f"Erro ao buscar dados da Polymarket: {exc}")
        return

    btc_price = None
    try:
        btc_price = get_btc_price_usd()
    except PolymarketAPIError:
        btc_price = None

    dynamic_title = data["event_title"] or slug
    st.title(f"📈 {dynamic_title}")

    labels = data["labels"]
    probs = data["mid_probabilities"] if use_mid else data["direct_probabilities"]

    p0 = probs[0] if probs[0] is not None else 0.0
    p1 = probs[1] if probs[1] is not None else 0.0

    time_left = _format_time_left(data.get("market_end_time"))

    st.markdown(
        f"""
        <div class="event-card">
          <div class="muted">Slug: {slug}</div>
          <div class="muted">{data['market_question']}</div>
          <div class="muted">Tempo restante: {time_left}</div>
          <div class="muted">Atualizado em {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if btc_price is not None:
        st.metric("BTC (CoinGecko)", f"US$ {btc_price:,.2f}")
    else:
        st.caption("BTC (CoinGecko): indisponível no momento")

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
                "market_end_time": data.get("market_end_time"),
                "btc_price_usd": btc_price,
                "snapshots": [snapshot.__dict__ for snapshot in data["snapshots"]],
            }
        )

    st.session_state.history[slug] = (p0, p1)


if hasattr(st, "fragment"):

    @st.fragment(run_every="3s")
    def live_panel() -> None:
        render_live_probabilities()

    live_panel()
else:
    st.warning(
        "Sua versão do Streamlit não suporta atualização parcial automática. Atualize para usar refresh a cada 3s sem recarregar a página."
    )
    render_live_probabilities()
