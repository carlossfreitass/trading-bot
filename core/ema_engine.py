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

MIN_BARS = EMA_SLOW1 + 10

# Quantidade de velas a verificar na primeira execução
LOOKBACK_INICIAL = 10

def _crossover(fast: pd.Series, slow: pd.Series) -> pd.Series:
    """True na vela em que fast cruza slow de baixo para cima."""
    return (fast > slow) & (fast.shift(1) <= slow.shift(1))

def _crossunder(fast: pd.Series, slow: pd.Series) -> pd.Series:
    """True na vela em que fast cruza slow de cima para baixo."""
    return (fast < slow) & (fast.shift(1) >= slow.shift(1))

def analyze(df: pd.DataFrame, last_candle_ts=None) -> dict | None:
    """
    Verifica velas fechadas em busca de confluência.
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

    # Seleciona velas fechadas a verificar
    velas_fechadas = df.iloc[:-1]

    if last_candle_ts is not None:
        # Execuções normais
        velas_a_verificar = velas_fechadas[velas_fechadas.index > last_candle_ts]
        log.info(f"Verificando {len(velas_a_verificar)} velas novas desde {last_candle_ts}")
    else:
        # Primeira execução
        velas_a_verificar = velas_fechadas.iloc[-LOOKBACK_INICIAL:]
        log.info(f"Primeira execução — verificando últimas {len(velas_a_verificar)} velas fechadas")

    if velas_a_verificar.empty:
        log.info("Nenhuma vela nova para verificar.")
        return None

    # Verifica cada vela individualmente
    for ts in velas_a_verificar.index:
        pos = df.index.get_loc(ts)

        confluencia_compra = bool(up_6_40.iloc[pos] and up_10_20.iloc[pos])
        confluencia_venda  = bool(dn_6_40.iloc[pos] and dn_10_20.iloc[pos])

        if not confluencia_compra and not confluencia_venda:
            continue

        log.info(f"✅ Confluência encontrada na vela {ts}")
        return {
            "confluencia_compra": confluencia_compra,
            "confluencia_venda":  confluencia_venda,
            "candle_ts":          ts,
            "ema6":  round(float(ema6.iloc[pos]),  5),
            "ema40": round(float(ema40.iloc[pos]), 5),
            "ema10": round(float(ema10.iloc[pos]), 5),
            "ema20": round(float(ema20.iloc[pos]), 5),
        }

    return None