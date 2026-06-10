"""
Busca candles OHLCV de pares Forex e Cripto via TradingView
utilizando a biblioteca tvDatafeed.
"""

import os
import logging
import pandas as pd
from tvDatafeed import TvDatafeed, Interval

log = logging.getLogger(__name__)

# Mapeamento
_INTERVAL_MAP = {
    "1m":  Interval.in_1_minute,
    "3m":  Interval.in_3_minute,
    "5m":  Interval.in_5_minute,
    "15m": Interval.in_15_minute,
    "30m": Interval.in_30_minute,
    "1h":  Interval.in_1_hour,
    "4h":  Interval.in_4_hour,
    "1d":  Interval.in_daily,
}

# Inicialização da API do TradingView
_tv_instance = None

def _get_tv_client():
    global _tv_instance
    if _tv_instance is None:
        username = os.getenv("TV_USERNAME", "")
        password = os.getenv("TV_PASSWORD", "")

        try:
            if username and password:
                log.info("Conectando ao TradingView usando conta autenticada.")
                _tv_instance = TvDatafeed(username, password)
            else:
                log.info("Conectando ao TradingView no modo anônimo.")
                _tv_instance = TvDatafeed()

        except Exception as e:
            log.warning(
                f"[TVDatafeed] Falha ao inicializar cliente TradingView: {e}"
            )

            try:
                log.info("Tentando reconectar em modo anônimo.")
                _tv_instance = TvDatafeed()
            except Exception as e2:
                log.error(
                    f"[TVDatafeed] Não foi possível criar cliente TradingView: {e2}",
                    exc_info=True
                )
                return None

    return _tv_instance

def _discover_exchange_and_symbol(symbol: str) -> tuple[str, str]:
    """Limpa o símbolo e define a melhor exchange padrão do TradingView."""
    clean = symbol.upper().replace("/", "").replace("-", "").replace("_", "").strip()

    # Forex
    if len(clean) == 6 and clean.isalpha():
        return "FX_IDC", clean

    # Binance (Cripto)
    return "BINANCE", clean

def fetch(symbol: str, interval: str, limit: int = 100) -> pd.DataFrame | None:
    """Busca dados históricos diretamente do TradingView."""
    tv = _get_tv_client()

    if tv is None:
        log.error("[TVDatafeed] Cliente TradingView indisponível.")
        return None

    tv_interval = _INTERVAL_MAP.get(interval)

    if not tv_interval:
        log.error(f"[TVDatafeed] Intervalo inválido ou não suportado: {interval}")
        return None

    exchange, clean_symbol = _discover_exchange_and_symbol(symbol)

    try:
        log.info(f"[TVDatafeed] Buscando {exchange}:{clean_symbol} em tempo gráfico {interval}")
        df = tv.get_hist(
            symbol=clean_symbol,
            exchange=exchange,
            interval=tv_interval,
            n_bars=limit
        )

        if df is None or df.empty:
            log.warning(f"[TVDatafeed] Nenhum dado retornado para {exchange}:{clean_symbol}")
            return None

        df.index = pd.to_datetime(df.index)
        df = df.rename(columns={
            "open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"
        })
        return df

    except Exception as e:
        log.error(f"[TVDatafeed] Falha crítica na busca de dados: {e}", exc_info=True)
        return None