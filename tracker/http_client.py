from __future__ import annotations

import json
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from tracker.config import DEFAULT_BACKOFF_SECONDS, DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT_SECONDS
from tracker.errors import PolymarketAPIError


def request_json_with_retries(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
) -> Any:
    query = f"?{urlencode(params)}" if params else ""
    final_url = f"{url}{query}"
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            req = Request(final_url, headers={"User-Agent": "polymarket-tracker/1.0"})
            with urlopen(req, timeout=timeout) as response:
                payload = response.read().decode("utf-8")
                return json.loads(payload)
        except HTTPError as exc:
            last_error = exc
            if exc.code == 429 and attempt < max_retries:
                time.sleep(backoff_seconds * (2**attempt))
                continue
            if attempt >= max_retries:
                break
            time.sleep(backoff_seconds * (2**attempt))
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt >= max_retries:
                break
            time.sleep(backoff_seconds * (2**attempt))

    raise PolymarketAPIError(f"Failed request after retries: {final_url}") from last_error
