"""
Busca candles OHLCV de pares Forex via Twelve Data API.
"""

import os
import logging
import requests
import pandas as pd

log = logging.getLogger(__name__)

BASE_URL = "https://api.twelvedata.com/time_series"

# Mapeamento
_INTERVAL_MAP = {
    "1m":  "1min",
    "5m":  "5min",
    "15m": "15min",
    "30m": "30min",
    "1h":  "1h",
    "1d":  "1day",
}

def fetch(symbol: str, interval: str, limit: int = 100) -> pd.DataFrame | None:
    """
    Busca candles do par Forex e retorna DataFrame com colunas:
        open, high, low, close, volume
    """
    token = os.getenv("TWELVE_DATA_TOKEN", "")
    if not token:
        log.error("TWELVE_DATA_TOKEN não definido no .env")
        return None

    iv = _INTERVAL_MAP.get(interval, "1min")

    try:
        resp = requests.get(
            BASE_URL,
            params={
                "symbol":     symbol,
                "interval":   iv,
                "outputsize": limit,
                "order":      "ASC",
                "apikey":     token,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") == "error":
            log.warning(f"[TwelveData] Erro para {symbol}: {data.get('message')}")
            return None

        values = data.get("values", [])
        if not values:
            log.warning(f"[TwelveData] Sem dados para {symbol}.")
            return None

        df = pd.DataFrame(values)
        df.index = pd.to_datetime(df["datetime"], utc=True)
        df = df.drop(columns=["datetime"])
        df = df.rename(columns={
            "open":   "open",
            "high":   "high",
            "low":    "low",
            "close":  "close",
            "volume": "volume",
        })

        df = df.astype(float)
        return df

    except requests.RequestException as e:
        log.error(f"[TwelveData] Erro ao buscar {symbol}: {e}")
        return None