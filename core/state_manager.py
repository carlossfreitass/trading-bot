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
    return _state.get(symbol.upper(), 0)

def resolve_signal(symbol: str, confluencia_compra: bool, confluencia_venda: bool) -> str | None:
    """
    Decide se deve emitir sinal com base na confluência e posição atual.
    """
    sym     = symbol.upper()
    posicao = get_position(sym)
    sinal   = None

    if confluencia_compra and posicao != 1:
        sinal = "COMPRA"
        _state[sym] = 1

    elif confluencia_venda and posicao != -1:
        sinal = "VENDA"
        _state[sym] = -1

    if sinal:
        _save(_state)
        log.info(f"[{sym}] Posição: {posicao} → {_state[sym]}")

    return sinal