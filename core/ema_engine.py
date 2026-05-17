"""
Calcula as 4 EMAs e detecta confluência de cruzamentos.
"""

import pandas as pd
import ta as ta_lib
import logging

log = logging.getLogger(__name__)

EMA_FAST1 = 6
EMA_SLOW1  = 40
EMA_FAST2 = 10
EMA_SLOW2  = 20

# Mínimo de velas para calcular todas as EMAs com confiabilidade
MIN_BARS = EMA_SLOW1 + 10

def _crossover(fast: pd.Series, slow: pd.Series) -> pd.Series:
    """True na vela em que fast cruza slow de baixo para cima."""
    return (fast > slow) & (fast.shift(1) <= slow.shift(1))

def _crossunder(fast: pd.Series, slow: pd.Series) -> pd.Series:
    """True na vela em que fast cruza slow de cima para baixo."""
    return (fast < slow) & (fast.shift(1) >= slow.shift(1))

def analyze(df: pd.DataFrame) -> dict | None:
    """
    Recebe DataFrame de candles e verifica a última vela FECHADA.
    """
    if df is None or len(df) < MIN_BARS:
        qty = len(df) if df is not None else 0
        log.warning(f"Dados insuficientes: {qty} velas (mínimo {MIN_BARS}).")
        return None

    close = df["close"]

    # Calcula as 4 EMAs
    ema6  = ta_lib.trend.ema_indicator(close, window=EMA_FAST1)
    ema40 = ta_lib.trend.ema_indicator(close, window=EMA_SLOW1)
    ema10 = ta_lib.trend.ema_indicator(close, window=EMA_FAST2)
    ema20 = ta_lib.trend.ema_indicator(close, window=EMA_SLOW2)

    # Cruzamentos
    up_6_40  = _crossover (ema6,  ema40)
    dn_6_40  = _crossunder(ema6,  ema40)
    up_10_20 = _crossover (ema10, ema20)
    dn_10_20 = _crossunder(ema10, ema20)

    # Última vela FECHADA
    i = -2

    confluencia_compra = bool(up_6_40.iloc[i] and up_10_20.iloc[i])
    confluencia_venda  = bool(dn_6_40.iloc[i] and dn_10_20.iloc[i])

    if not confluencia_compra and not confluencia_venda:
        return None

    return {
        "confluencia_compra": confluencia_compra,
        "confluencia_venda":  confluencia_venda,
        "ema6":  round(float(ema6.iloc[i]),  5),
        "ema40": round(float(ema40.iloc[i]), 5),
        "ema10": round(float(ema10.iloc[i]), 5),
        "ema20": round(float(ema20.iloc[i]), 5),
    }