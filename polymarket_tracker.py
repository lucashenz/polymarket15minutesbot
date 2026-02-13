"""Backward-compatible facade for legacy imports.

Prefer importing from the `tracker` package modules directly.
"""

from tracker import PolymarketAPIError, calculate_probability, collect_event_probabilities, get_market_data
from tracker.models import OrderBookSnapshot
from tracker.probability import normalize_binary_probabilities

__all__ = [
    "PolymarketAPIError",
    "OrderBookSnapshot",
    "get_market_data",
    "calculate_probability",
    "collect_event_probabilities",
    "normalize_binary_probabilities",
]
