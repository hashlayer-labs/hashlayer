"""
Cryptocurrency network statistics fetcher with caching.

Provides methods to fetch current network statistics for various cryptocurrencies
such as difficulty, with built-in caching to minimize API calls.
"""

import logging

import cachetools
import requests
from cachetools import TTLCache

logger = logging.getLogger(__name__)

DIFFICULTY_TTL = 12 * 60 * 60  # 12 hours
_difficulty_cache = TTLCache(maxsize=10, ttl=DIFFICULTY_TTL)

# Fallback difficulties (BTC SHA256d)
FALLBACK_DIFFICULTIES = {
    "bitcoin": 95_000_000_000_000,  # ~95T fallback for BTC
    "btc": 95_000_000_000_000,
}

API_TIMEOUT = 10  # seconds

DIFFICULTY_APIS = {
    "bitcoin": "https://api.blockchair.com/bitcoin/stats",
    "btc": "https://api.blockchair.com/bitcoin/stats",
}


def _normalize_coin(coin: str) -> str:
    c = coin.lower()
    if c in ("btc", "bitcoin"):
        return "bitcoin"
    return c


def _fetch_difficulty(coin: str = "bitcoin") -> float:
    """
    Fetch current network difficulty for specified coin.

    Args:
        coin: The cryptocurrency name (bitcoin)

    Returns:
        float: Current network difficulty

    Raises:
        Exception: If API request fails or returns invalid data
    """
    normalized = _normalize_coin(coin)
    api_url = DIFFICULTY_APIS.get(normalized)
    if not api_url:
        raise Exception(f"Unsupported coin: {coin}")

    response = requests.get(api_url, timeout=API_TIMEOUT)
    if response.status_code == 200:
        data = response.json()
        difficulty = float(data["data"]["difficulty"])
        logger.info(f"Fetched {normalized} difficulty: {difficulty:,.0f}")
        return difficulty
    raise Exception(f"API returned status {response.status_code}")


@cachetools.cached(cache=_difficulty_cache)
def get_current_difficulty(coin: str = "bitcoin") -> float:
    """
    Get current network difficulty for specified coin with caching.

    Args:
        coin: The cryptocurrency name (bitcoin / btc)

    Returns:
        float: Current network difficulty, or fallback value if fetch fails
    """
    normalized = _normalize_coin(coin)
    try:
        return _fetch_difficulty(normalized)
    except requests.Timeout:
        logger.warning(f"Timeout fetching {normalized} difficulty after {API_TIMEOUT}s")
    except Exception as e:
        logger.error(f"Error fetching {normalized} difficulty: {e}")

    fallback = FALLBACK_DIFFICULTIES.get(normalized, FALLBACK_DIFFICULTIES["bitcoin"])
    logger.warning(f"Using fallback {normalized} difficulty: {fallback:,.0f}")
    return fallback
