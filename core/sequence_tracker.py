"""
Rastreia a sequência entre os dois indicadores.
"""

import json
import os
import logging
from pathlib import Path

log = logging.getLogger(__name__)

SEQ_FILE = Path(os.path.dirname(os.path.abspath(__file__))).parent / "sequence_state.json"

def _load() -> dict:
    try:
        if SEQ_FILE.exists():
            return json.loads(SEQ_FILE.read_text())
    except Exception as e:
        log.warning(f"Não foi possível carregar sequence_state.json: {e}")
    return {}

def _save(state: dict) -> None:
    try:
        SEQ_FILE.write_text(json.dumps(state, indent=2))
    except Exception as e:
        log.warning(f"Não foi possível salvar sequence_state.json: {e}")

_seq_state: dict = _load()

def get_sequence_state(symbol: str) -> str:
    """Retorna o estado atual da sequência."""
    return _seq_state.get(symbol.upper(), {}).get("estado", "idle")

def process_sequence(
    symbol: str,
    up_10_20: bool,
    dn_10_20: bool,
    up_6_40: bool,
    dn_6_40: bool,
) -> str | None:
    """
    Processa os cruzamentos da vela atual e atualiza o estado da sequência.
    """
    sym    = symbol.upper()
    estado = get_sequence_state(sym)
    sinal  = None

    # Linha de baixo aparece nesta vela
    # Reseta qualquer sequência anterior
    if up_10_20:
        # Triângulo verde na linha de baixo
        _seq_state[sym] = {"estado": "waiting_up"}
        log.info(f"[{sym}] Sequência iniciada: aguardando verde na linha de cima")
        estado = "waiting_up"

    elif dn_10_20:
        # Triângulo vermelho na linha de baixo
        _seq_state[sym] = {"estado": "waiting_down"}
        log.info(f"[{sym}] Sequência iniciada: aguardando vermelho na linha de cima")
        estado = "waiting_down"

    # Linha de cima aparece nesta vela
    # Só é processada se já houver sequência ativa
    if estado == "waiting_up":
        if up_6_40:
            # Verde na linha de cima confirma a sequência
            sinal = "COMPRA_SEQ"
            _seq_state[sym] = {"estado": "idle"}
            log.info(f"[{sym}] ✅ Sequência de COMPRA confirmada")
        elif dn_6_40:
            # Vermelho na linha de cima cancela a sequência
            _seq_state[sym] = {"estado": "idle"}
            log.info(f"[{sym}] ❌ Sequência cancelada: direção oposta na linha de cima")

    elif estado == "waiting_down":
        if dn_6_40:
            # Vermelho na linha de cima confirma a sequência
            sinal = "VENDA_SEQ"
            _seq_state[sym] = {"estado": "idle"}
            log.info(f"[{sym}] ✅ Sequência de VENDA confirmada")
        elif up_6_40:
            # Verde na linha de cima cancela a sequência
            _seq_state[sym] = {"estado": "idle"}
            log.info(f"[{sym}] ❌ Sequência cancelada: direção oposta na linha de cima")

    # Linha de cima aparece sem sequência ativa
    # Ignorada
    _save(_seq_state)
    return sinal