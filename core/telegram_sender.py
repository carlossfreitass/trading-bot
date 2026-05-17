"""
Envia mensagens formatadas ao Telegram Bot.
Tipos de sinal: COMPRA e VENDA.
"""

import os
import logging
import requests
from datetime import datetime, timezone

log = logging.getLogger(__name__)

_TEMPLATES = {
    "COMPRA": (
        "🟢 *SINAL DE COMPRA*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📈 Confluência altista detectada!\n"
        "• Ativo: `{display}`\n"
        "• EMA 6 cruzou ↑ EMA 40\n"
        "• EMA 10 cruzou ↑ EMA 20\n"
        "• EMA 6: `{ema6}` | EMA 40: `{ema40}`\n"
        "⏰ `{hora}`"
    ),
    "VENDA": (
        "🔴 *SINAL DE VENDA*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📉 Confluência baixista detectada!\n"
        "• Ativo: `{display}`\n"
        "• EMA 6 cruzou ↓ EMA 40\n"
        "• EMA 10 cruzou ↓ EMA 20\n"
        "• EMA 6: `{ema6}` | EMA 40: `{ema40}`\n"
        "⏰ `{hora}`"
    ),
}

def _hora() -> str:
    return datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")

def _post(texto: str) -> bool:
    token   = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHATID")
    if not token or not chat_id:
        log.error("TELEGRAM_TOKEN ou TELEGRAM_CHATID ausentes no .env")
        return False
    try:
        url  = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(
            url,
            json={"chat_id": chat_id, "text": texto, "parse_mode": "Markdown"},
            timeout=15,
        )
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        log.error(f"Falha ao enviar Telegram: {e}")
        return False

def send(sinal: str, display: str, ema_data: dict) -> bool:
    """
    Envia mensagem de COMPRA ou VENDA formatada.
    """
    template = _TEMPLATES.get(sinal)
    if not template:
        log.error(f"Tipo de sinal desconhecido: {sinal}")
        return False

    texto = template.format(display=display, hora=_hora(), **ema_data)
    ok    = _post(texto)
    if ok:
        log.info(f"[{display}] '{sinal}' enviado ao Telegram.")
    return ok

def send_raw(texto: str) -> bool:
    """Envia texto livre (avisos do sistema)."""
    return _post(texto)