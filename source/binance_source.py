"""
Busca candles OHLCV de pares Cripto via Binance API pública.
"""

import logging
import requests
import pandas as pd

log = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com/api/v3/klines"

# Mapeamento
_INTERVAL_MAP = {
    "1m":  "1m",
    "5m":  "5m",
    "15m": "15m",
    "30m": "30m",
    "1h":  "1h",
    "4h":  "4h",
    "1d":  "1d",
}

def fetch(symbol: str, interval: str, limit: int = 100) -> pd.DataFrame | None:
    """
    Busca candles do par Cripto e retorna DataFrame com colunas:
        open, high, low, close, volume
    """
    iv = _INTERVAL_MAP.get(interval, "1m")

    try:
        resp = requests.get(
            BASE_URL,
            params={"symbol": symbol.upper(), "interval": iv, "limit": limit},
            timeout=10,
        )
        resp.raise_for_status()
        raw = resp.json()

        if not raw or isinstance(raw, dict):
            log.warning(f"[Binance] Resposta inesperada para {symbol}: {raw}")
            return None

        df = pd.DataFrame(raw, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_vol", "trades",
            "taker_buy_base", "taker_buy_quote", "ignore",
        ])
        df.index = pd.to_datetime(df["close_time"], unit="ms", utc=True)
        df = df[["open", "high", "low", "close", "volume"]].astype(float)
        return df

    except requests.RequestException as e:
        log.error(f"[Binance] Erro ao buscar {symbol}: {e}")
        return None