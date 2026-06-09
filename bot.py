import time
import logging
import os
from dotenv import load_dotenv

from utils.asset_detector      import detect
from source.twelvedata_source  import fetch as twelvedata_fetch
from source.binance_source     import fetch as binance_fetch
from core.ema_engine           import analyze
from core.state_manager        import get_last_candle_ts, resolve_signal
from core.telegram_sender      import send, send_raw
from core.sequence_tracker     import process_sequence, reset_sequence

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(_BASE_DIR, "bot.log"), encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

load_dotenv()

_FETCHERS = {
    "twelvedata": twelvedata_fetch,
    "binance":    binance_fetch,
}

_SOURCE_LABEL = {
    "twelvedata": "Twelve Data (Forex)",
    "binance":    "Binance (Cripto)",
}

def validar_config() -> tuple[list[str], str, int]:
    faltando = [
        v for v in ("TELEGRAM_TOKEN", "TELEGRAM_CHATID", "TWELVE_DATA_TOKEN")
        if not os.getenv(v)
    ]
    if faltando:
        raise EnvironmentError(f"Variáveis ausentes no .env: {', '.join(faltando)}")

    symbols   = [s.strip() for s in os.getenv("SYMBOLS", "USDJPY,EURGBP").split(",") if s.strip()]
    interval  = os.getenv("INTERVAL", "15m")
    check_int = int(os.getenv("CHECK_INTERVAL", "900"))

    log.info(f"✅ Config OK | Ativos: {symbols} | Intervalo: {interval} | Check: {check_int}s")
    return symbols, interval, check_int

def processar_simbolo(symbol: str, interval: str) -> None:
    info    = detect(symbol)
    fetcher = _FETCHERS[info["source"]]

    log.info(f"[{info['display']}] Buscando dados via {_SOURCE_LABEL[info['source']]}...")

    df = fetcher(info["symbol"], interval, limit=100)
    if df is None:
        log.warning(f"[{info['display']}] Sem dados disponíveis.")
        return

    last_ts   = get_last_candle_ts(symbol)
    velas     = analyze(df, last_candle_ts=last_ts)

    if not velas:
        log.debug(f"[{info['display']}] Nenhum cruzamento em velas novas.")
        return

    for vela in velas:
        ts             = vela["candle_ts"]
        is_confluencia = vela["confluencia_compra"] or vela["confluencia_venda"]

        # Confluência perfeita
        if is_confluencia:
            # Sistema 1: Confluência perfeita (Mesma vela)
            sinal = resolve_signal(
                symbol,
                vela["confluencia_compra"],
                vela["confluencia_venda"],
                ts,
            )
            if sinal:
                log.info(f"[{info['display']}] 🔔 Confluência: {sinal}")
                send(sinal, info["display"], vela)

            # Limpa a memória da sequência para evitar sinais duplicados
            reset_sequence(symbol)

        else:
            # Sequência entre indicadores
            sinal_seq = process_sequence(
                symbol,
                up_10_20=vela["up_10_20"],
                dn_10_20=vela["dn_10_20"],
                up_6_40=vela["up_6_40"],
                dn_6_40=vela["dn_6_40"],
            )
            if sinal_seq:
                log.info(f"[{info['display']}] 🔔 Sequência: {sinal_seq}")
                send(sinal_seq, info["display"], vela)

            # Atualiza o timestamp no state_manager para não reprocessar esta vela
            resolve_signal(symbol, False, False, ts)

def loop(symbols: list[str], interval: str, check_interval: int) -> None:
    falhas = 0
    MAX_FALHAS = 10

    log.info("🚀 Bot iniciado.")

    while True:
        try:
            for symbol in symbols:
                processar_simbolo(symbol, interval)
            falhas = 0
            time.sleep(check_interval)

        except KeyboardInterrupt:
            log.info("⛔ Bot encerrado pelo usuário.")
            break

        except Exception as e:
            falhas += 1
            log.error(f"Erro inesperado ({falhas}x): {e}", exc_info=True)
            if falhas >= MAX_FALHAS:
                send_raw(f"🚨 *Bot — ERRO CRÍTICO*\n{falhas} falhas consecutivas.\nVerifique `bot.log`.")
                falhas = 0
            time.sleep(30)

    log.info("Bot encerrado.")

if __name__ == "__main__":
    symbols, interval, check_interval = validar_config()
    loop(symbols, interval, check_interval)