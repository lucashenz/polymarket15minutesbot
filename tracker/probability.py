from __future__ import annotations

import json
from typing import Any


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_json_array(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        if isinstance(parsed, list):
            return parsed
    return []


def extract_prices(levels: list[dict[str, Any]] | None) -> list[float]:
    if not levels:
        return []
    values: list[float] = []
    for level in levels:
        price = to_float(level.get("price"))
        if price is not None:
            values.append(price)
    return values


def normalize_binary_probabilities(prob_a: float | None, prob_b: float | None) -> tuple[float | None, float | None]:
    if prob_a is None and prob_b is None:
        return None, None
    if prob_a is None:
        return None, 1.0
    if prob_b is None:
        return 1.0, None

    total = prob_a + prob_b
    if total <= 0:
        return 0.5, 0.5

    return prob_a / total, prob_b / total
