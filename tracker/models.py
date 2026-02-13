from dataclasses import dataclass


@dataclass
class OrderBookSnapshot:
    token_id: str
    last_trade_price: float | None
    best_bid: float | None
    best_ask: float | None
    mid_price_probability: float | None
    spread: float | None
