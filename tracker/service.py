from __future__ import annotations

from typing import Any

from tracker.config import CLOB_BOOK_URL, COINGECKO_SIMPLE_PRICE_URL, GAMMA_EVENTS_URL
from tracker.errors import PolymarketAPIError
from tracker.http_client import request_json_with_retries
from tracker.models import OrderBookSnapshot
from tracker.probability import extract_prices, normalize_binary_probabilities, parse_json_array, to_float


def get_market_data(slug: str) -> dict[str, Any]:
    payload = request_json_with_retries(GAMMA_EVENTS_URL, params={"slug": slug})
    if not isinstance(payload, list) or not payload:
        raise PolymarketAPIError(f"No event found for slug={slug!r}")

    event = payload[0]
    markets = event.get("markets") or []
    if not isinstance(markets, list):
        raise PolymarketAPIError("Invalid markets payload from Gamma API")

    chosen_market: dict[str, Any] | None = None
    chosen_token_ids: list[str] = []

    for market in markets:
        token_ids = [str(x) for x in parse_json_array(market.get("clobTokenIds")) if x is not None]
        if len(token_ids) >= 2:
            chosen_market = market
            chosen_token_ids = token_ids[:2]
            break

    if not chosen_market or len(chosen_token_ids) < 2:
        raise PolymarketAPIError("Could not find a binary market with 2 token IDs")

    outcomes = [str(x) for x in parse_json_array(chosen_market.get("outcomes"))]
    labels = outcomes[:2] if len(outcomes) >= 2 else ["UP/YES", "DOWN/NO"]

    market_end_time = chosen_market.get("endDate") or event.get("endDate") or event.get("end_date")

    return {
        "event_slug": slug,
        "event_title": event.get("title") or slug,
        "market_question": chosen_market.get("question") or "",
        "market_end_time": market_end_time,
        "token_ids": chosen_token_ids,
        "labels": labels,
    }


def calculate_probability(token_id: str) -> OrderBookSnapshot:
    payload = request_json_with_retries(CLOB_BOOK_URL, params={"token_id": token_id})

    bids = extract_prices(payload.get("bids"))
    asks = extract_prices(payload.get("asks"))

    best_bid = max(bids) if bids else None
    best_ask = min(asks) if asks else None

    mid: float | None = None
    spread: float | None = None
    if best_bid is not None and best_ask is not None:
        mid = (best_bid + best_ask) / 2
        spread = best_ask - best_bid

    return OrderBookSnapshot(
        token_id=token_id,
        last_trade_price=to_float(payload.get("last_trade_price")),
        best_bid=best_bid,
        best_ask=best_ask,
        mid_price_probability=mid,
        spread=spread,
    )


def get_btc_price_usd() -> float | None:
    payload = request_json_with_retries(
        COINGECKO_SIMPLE_PRICE_URL,
        params={"ids": "bitcoin", "vs_currencies": "usd"},
    )
    if not isinstance(payload, dict):
        return None
    btc_payload = payload.get("bitcoin")
    if not isinstance(btc_payload, dict):
        return None
    return to_float(btc_payload.get("usd"))


def collect_event_probabilities(slug: str) -> dict[str, Any]:
    market = get_market_data(slug)
    t0, t1 = market["token_ids"]

    snap0 = calculate_probability(t0)
    snap1 = calculate_probability(t1)

    direct0, direct1 = normalize_binary_probabilities(snap0.last_trade_price, snap1.last_trade_price)
    mid0, mid1 = normalize_binary_probabilities(snap0.mid_price_probability, snap1.mid_price_probability)

    return {
        "event_title": market["event_title"],
        "market_question": market["market_question"],
        "market_end_time": market["market_end_time"],
        "labels": market["labels"],
        "tokens": market["token_ids"],
        "direct_probabilities": [direct0, direct1],
        "mid_probabilities": [mid0, mid1],
        "snapshots": [snap0, snap1],
    }
