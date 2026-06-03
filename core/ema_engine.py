"""
Calcula as 4 EMAs, detecta confluência e expõe cruzamentos individuais.
"""

import pandas as pd
import ta as ta_lib
import logging

log = logging.getLogger(__name__)

EMA_FAST1 = 6
EMA_SLOW1 = 40
EMA_FAST2 = 10
EMA_SLOW2 = 20
MIN_BARS  = EMA_SLOW1 + 10

def _crossover(fast: pd.Series, slow: pd.Series) -> pd.Series:
    """True na vela em que fast cruza slow de baixo para cima."""
    return (fast > slow) & (fast.shift(1) <= slow.shift(1))

def _crossunder(fast: pd.Series, slow: pd.Series) -> pd.Series:
    """True na vela em que fast cruza slow de cima para baixo."""
    return (fast < slow) & (fast.shift(1) >= slow.shift(1))

def analyze(df: pd.DataFrame, last_candle_ts=None) -> list[dict]:
    """
    Verifica velas fechadas em busca de cruzamentos.
    """
    if df is None or len(df) < MIN_BARS:
        log.warning(f"Dados insuficientes: {len(df) if df is not None else 0} velas.")
        return []

    close = df["close"]

    # Calcula as 4 EMAs
    ema6  = ta_lib.trend.ema_indicator(close, window=EMA_FAST1)
    ema40 = ta_lib.trend.ema_indicator(close, window=EMA_SLOW1)
    ema10 = ta_lib.trend.ema_indicator(close, window=EMA_FAST2)
    ema20 = ta_lib.trend.ema_indicator(close, window=EMA_SLOW2)

    # Detecta todos os cruzamentos na série histórica inteira de uma só vez
    up_6_40  = _crossover(ema6,  ema40)
    dn_6_40  = _crossunder(ema6,  ema40)
    up_10_20 = _crossover(ema10, ema20)
    dn_10_20 = _crossunder(ema10, ema20)

    # Ignora a última vela, pois ela ainda está aberta
    velas_fechadas = df.iloc[:-1]

    # Filtra apenas as velas que não foram analisadas no ciclo anterior
    if last_candle_ts is not None:
        velas_a_verificar = velas_fechadas[velas_fechadas.index > last_candle_ts]
        log.info(f"Verificando {len(velas_a_verificar)} velas novas desde {last_candle_ts}")
    else:
        velas_a_verificar = velas_fechadas.iloc[-2:]
        log.info("Verificando as duas últimas velas fechadas")

    if velas_a_verificar.empty:
        log.info("Nenhuma vela nova para verificar.")
        return []

    resultados = []

    # Varre apenas as velas novas buscando ações relevantes
    for ts in velas_a_verificar.index:
        pos = df.index.get_loc(ts)

        u640  = bool(up_6_40.iloc[pos])
        d640  = bool(dn_6_40.iloc[pos])
        u1020 = bool(up_10_20.iloc[pos])
        d1020 = bool(dn_10_20.iloc[pos])

        # Só inclui velas com pelo menos um cruzamento ativo
        if not any([u640, d640, u1020, d1020]):
            continue

        confluencia_compra = u640 and u1020
        confluencia_venda  = d640 and d1020

        resultados.append({
            "candle_ts":          ts,
            "confluencia_compra": confluencia_compra,
            "confluencia_venda":  confluencia_venda,
            "up_6_40":            u640,
            "dn_6_40":            d640,
            "up_10_20":           u1020,
            "dn_10_20":           d1020,
            "ema6":  round(float(ema6.iloc[pos]),  5),
            "ema40": round(float(ema40.iloc[pos]), 5),
            "ema10": round(float(ema10.iloc[pos]), 5),
            "ema20": round(float(ema20.iloc[pos]), 5),
        })

    if resultados:
        log.info(f"✅ {len(resultados)} vela(s) com cruzamento encontrada(s)")

    return resultados