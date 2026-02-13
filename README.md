# Polymarket Real-Time Probability Tracker

Bot de monitoramento para mercados binários da Polymarket usando Gamma API + CLOB API, com cálculo de probabilidade implícita e dashboard minimalista em dark mode.

## Arquitetura simples

```
tracker/
  config.py        # endpoints e parâmetros padrão
  errors.py        # exceções de domínio
  http_client.py   # chamadas HTTP com retry/backoff
  probability.py   # parsing utilitário + normalização
  models.py        # dataclasses
  service.py       # casos de uso (get_market_data/calculate_probability)
dashboard.py       # UI Streamlit
polymarket_tracker.py  # fachada de compatibilidade
tests/
```

## O que foi implementado

- `get_market_data(slug)`: consulta a Gamma API e retorna metadados do evento + 2 `clobTokenIds`.
- `calculate_probability(token_id)`: consulta o livro de ofertas na CLOB API e calcula:
  - probabilidade direta (`last_trade_price`)
  - best bid / best ask
  - mid-price
  - spread
- Normalização binária para manter soma próxima de 100%.
- Retry com backoff exponencial para lidar com rate limit e falhas temporárias (implementado com `urllib` da biblioteca padrão).
- Dashboard Streamlit com atualização automática a cada 3 segundos (sem recarregar a página inteira), barras de progresso UP/DOWN e tendência contra a atualização anterior.

## Como rodar

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run dashboard.py
# o painel atualiza automaticamente as probabilidades a cada 3s
```

## Testes

```bash
pytest -q
```
