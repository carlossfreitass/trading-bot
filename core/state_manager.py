"""
Controla o estado de cada símbolo para evitar sinais duplicados consecutivos.
"""

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

STATE_FILE = Path("state.json")

def _load() -> dict:
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except Exception as e:
        log.warning(f"Não foi possível carregar state.json: {e}")
    return {}

def _save(state: dict) -> None:
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2))
    except Exception as e:
        log.warning(f"Não foi possível salvar state.json: {e}")

# Carregado uma vez na inicialização
_state: dict = _load()

def get_position(symbol: str) -> int:
    """Retorna a posição atual: 0, 1 ou -1."""
    return _state.get(symbol.upper(), {}).get("posicao", 0)

def get_last_candle_ts(symbol: str) -> str:
    """Retorna o timestamp da última vela já processada."""
    return _state.get(symbol.upper(), {}).get("last_candle_ts", "")

def resolve_signal(
    symbol: str,
    confluencia_compra: bool,
    confluencia_venda: bool,
    candle_ts,
) -> str | None:
    """
    Decide se deve emitir sinal com base na confluência,
    posição atual e timestamp da vela.
    """
    sym         = symbol.upper()
    posicao     = get_position(sym)
    last_ts     = get_last_candle_ts(sym)
    candle_ts_s = str(candle_ts)

    # Ignora vela já processada
    if candle_ts_s == last_ts:
        log.debug(f"[{sym}] Vela {candle_ts_s} já processada. Ignorando.")
        return None

    sinal = None

    if confluencia_compra and posicao != 1:
        sinal = "COMPRA"
        _state[sym] = {"posicao": 1, "last_candle_ts": candle_ts_s}

    elif confluencia_venda and posicao != -1:
        sinal = "VENDA"
        _state[sym] = {"posicao": -1, "last_candle_ts": candle_ts_s}

    else:
        # Mesma direção — apenas atualiza o timestamp para não re-processar
        if sym not in _state:
            _state[sym] = {"posicao": posicao, "last_candle_ts": candle_ts_s}
        else:
            _state[sym]["last_candle_ts"] = candle_ts_s

    _save(_state)

    if sinal:
        log.info(f"[{sym}] Posição: {posicao} → {_state[sym]['posicao']} | Vela: {candle_ts_s}")

    return sinal