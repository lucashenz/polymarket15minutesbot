from __future__ import annotations

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
    .countdown { color: #e74c3c; font-weight: 600; font-size: 1.1rem; }
    .auto-status { 
        background: #1e3a1e;
        border: 1px solid #2ecc71;
        border-radius: 8px;
        padding: 10px;
        margin: 10px 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🤖 BTC 5min Auto-Tracker")


# ========== FUNÇÕES AUXILIARES ==========
def extract_timestamp_from_slug(slug: str) -> int | None:
    """
    Extrai o timestamp de um slug no formato: btc-updown-5m-TIMESTAMP
    
    Exemplos:
        btc-updown-5m-1770999900 -> 1770999900
        btc-updown-5m-1771000200 -> 1771000200
    """
    try:
        parts = slug.split('-')
        # Último elemento é o timestamp
        timestamp = int(parts[-1])
        return timestamp
    except (IndexError, ValueError):
        return None


def generate_next_slug(current_slug: str, interval_seconds: int = 300) -> str:
    """
    Gera o próximo slug incrementando o timestamp
    
    Args:
        current_slug: Slug atual (ex: btc-updown-5m-1770999900)
        interval_seconds: Intervalo em segundos (padrão: 300 = 5 minutos)
    
    Returns:
        Próximo slug (ex: btc-updown-5m-1771000200)
    """
    timestamp = extract_timestamp_from_slug(current_slug)
    
    if timestamp is None:
        return current_slug
    
    # Incrementa o timestamp
    next_timestamp = timestamp + interval_seconds
    
    # Reconstrói o slug com o novo timestamp
    parts = current_slug.split('-')
    parts[-1] = str(next_timestamp)
    next_slug = '-'.join(parts)
    
    return next_slug


def get_time_until_next_period(current_timestamp: int, interval_seconds: int = 300) -> int:
    """
    Calcula quantos segundos faltam até o próximo período
    
    Args:
        current_timestamp: Timestamp do período atual
        interval_seconds: Duração do período em segundos
    
    Returns:
        Segundos até o próximo período
    """
    # Timestamp do fim do período atual
    period_end = current_timestamp + interval_seconds
    
    # Timestamp atual
    now = int(datetime.now(timezone.utc).timestamp())
    
    # Diferença
    remaining = period_end - now
    
    return max(0, remaining)  # Nunca retorna negativo


def should_update_slug(current_slug: str) -> bool:
    """
    Verifica se já passou o período e precisa atualizar o slug
    
    Returns:
        True se deve atualizar para o próximo slug
    """
    timestamp = extract_timestamp_from_slug(current_slug)
    if timestamp is None:
        return False
    
    time_remaining = get_time_until_next_period(timestamp)
    
    # Se faltam menos de 5 segundos, já atualiza
    return time_remaining <= 5


# ========== INICIALIZAÇÃO ==========
if "history" not in st.session_state:
    st.session_state.history = {}

if "auto_mode_enabled" not in st.session_state:
    st.session_state.auto_mode_enabled = False

if "base_slug" not in st.session_state:
    st.session_state.base_slug = "btc-updown-5m-1770999900"


# ========== SIDEBAR ==========
with st.sidebar:
    st.subheader("⚙️ Configuração")
    
    # Input do slug inicial
    input_slug = st.text_input(
        "Slug inicial (para ligar o bot)",
        value=st.session_state.base_slug,
        help="Cole o slug do mercado ativo atual. O bot continuará automaticamente a partir dele."
    )
    
    # Botão para ativar modo automático
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Ligar Bot", type="primary", use_container_width=True):
            st.session_state.auto_mode_enabled = True
            st.session_state.base_slug = input_slug
            st.rerun()
    
    with col2:
        if st.button("⏸️ Pausar", use_container_width=True):
            st.session_state.auto_mode_enabled = False
            st.rerun()
    
    st.markdown("---")
    
    # Status do bot
    if st.session_state.auto_mode_enabled:
        st.markdown("""
        <div class="auto-status">
            <b>🟢 BOT ATIVO</b><br/>
            <small>Atualizando automaticamente</small>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("⚪ Bot pausado. Clique em 'Ligar Bot' para começar.")
    
    st.markdown("---")
    
    # Configurações adicionais
    use_mid = st.toggle("Use mid-price (recommended)", value=True)
    
    # Informações do slug atual
    if st.session_state.auto_mode_enabled:
        st.subheader("📊 Informações")
        
        current_slug = st.session_state.base_slug
        timestamp = extract_timestamp_from_slug(current_slug)
        
        if timestamp:
            time_remaining = get_time_until_next_period(timestamp)
            minutes = time_remaining // 60
            seconds = time_remaining % 60
            
            st.metric("Tempo restante", f"{minutes}min {seconds}s")
            
            next_slug = generate_next_slug(current_slug)
            st.caption(f"**Próximo:** `{next_slug}`")


# ========== RENDERIZAÇÃO PRINCIPAL ==========
def render_live_probabilities() -> None:
    # Define qual slug usar
    if st.session_state.auto_mode_enabled:
        slug = st.session_state.base_slug
        
        # Verifica se precisa atualizar o slug
        if should_update_slug(slug):
            st.session_state.base_slug = generate_next_slug(slug)
            slug = st.session_state.base_slug
            st.toast("🔄 Novo período! Slug atualizado.", icon="✅")
    else:
        # Se não está ativo, não mostra nada
        st.info("⚪ Bot pausado. Configure o slug inicial e clique em 'Ligar Bot'.")
        return
    
    # Busca dados
    try:
        data = collect_event_probabilities(slug)
    except PolymarketAPIError as exc:
        st.error(f"❌ Erro ao buscar dados: {exc}")
        st.warning("💡 Verifique se o slug está correto e o mercado está ativo.")
        return

    labels = data["labels"]
    probs = data["mid_probabilities"] if use_mid else data["direct_probabilities"]

    p0 = probs[0] if probs[0] is not None else 0.0
    p1 = probs[1] if probs[1] is not None else 0.0
    
    # Calcula countdown
    timestamp = extract_timestamp_from_slug(slug)
    if timestamp:
        time_remaining = get_time_until_next_period(timestamp)
        minutes = time_remaining // 60
        seconds = time_remaining % 60
        countdown_html = f"""
        <div class="countdown">
            ⏱️ Janela fecha em: {minutes}min {seconds}s
        </div>
        """
    else:
        countdown_html = ""

    # Card principal
    st.markdown(
        f"""
        <div class="event-card">
          <h3 style="margin:0;">{data['event_title']}</h3>
          <div class="muted">{data['market_question']}</div>
          <div class="muted">Slug atual: <code>{slug}</code></div>
          {countdown_html}
          <div class="muted">Atualizado em {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Histórico
    prev = st.session_state.history.get(slug)

    # Colunas com probabilidades
    col1, col2 = st.columns(2)
    with col1:
        st.subheader(labels[0])
        st.progress(min(max(p0, 0.0), 1.0))
        st.metric("Probabilidade", f"{p0 * 100:.1f}%")
    with col2:
        st.subheader(labels[1])
        st.progress(min(max(p1, 0.0), 1.0))
        st.metric("Probabilidade", f"{p1 * 100:.1f}%")

    # Tendência
    if prev:
        d0 = p0 - prev[0]
        arrow = "⬆️" if d0 >= 0 else "⬇️"
        css_class = "trend-up" if d0 >= 0 else "trend-down"
        st.markdown(
            f"<p class='{css_class}'>Tendência (vs atualização anterior): {arrow} {d0 * 100:+.2f} p.p.</p>",
            unsafe_allow_html=True,
        )

    # Detalhes técnicos
    with st.expander("Detalhes técnicos"):
        st.json(
            {
                "slug": slug,
                "timestamp": timestamp,
                "time_remaining": time_remaining if timestamp else None,
                "next_slug": generate_next_slug(slug) if timestamp else None,
                "direct_probabilities": data["direct_probabilities"],
                "mid_probabilities": data["mid_probabilities"],
                "snapshots": [snapshot.__dict__ for snapshot in data["snapshots"]],
            }
        )

    # Salva histórico
    st.session_state.history[slug] = (p0, p1)


# ========== AUTO-REFRESH ==========
if hasattr(st, "fragment"):
    @st.fragment(run_every="3s")
    def live_panel() -> None:
        render_live_probabilities()

    live_panel()
else:
    st.warning("Sua versão do Streamlit não suporta atualização parcial automática.")
    render_live_probabilities()