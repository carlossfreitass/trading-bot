import time
import logging
import os
from dotenv import load_dotenv

from utils.asset_detector      import detect
from source.twelvedata_source  import fetch as twelvedata_fetch
from source.binance_source     import fetch as binance_fetch
from source.tvdatafeed_source  import fetch as tvdatafeed_fetch
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
    "tvdatafeed": tvdatafeed_fetch,
}

def validar_config() -> tuple[list[str], str, int]:
    obrigatorias = ["TELEGRAM_TOKEN", "TELEGRAM_CHATID"]

    forex_source = os.getenv("FOREX_SOURCE", "twelvedata").lower()
    if forex_source == "twelvedata":
        obrigatorias.append("TWELVE_DATA_TOKEN")

    faltando = [v for v in obrigatorias if not os.getenv(v)]
    if faltando:
        raise EnvironmentError(f"Variáveis ausentes no .env: {', '.join(faltando)}")

    symbols = [s.strip() for s in os.getenv("SYMBOLS", "USDJPY,EURGBP").split(",") if s.strip()]
    interval = os.getenv("INTERVAL", "15m")
    check_int = int(os.getenv("CHECK_INTERVAL", "900"))

    log.info(f"✅ Config OK | Ativos: {symbols} | Intervalo: {interval} | Check: {check_int}s")
    return symbols, interval, check_int

def processar_simbolo(symbol: str, interval: str) -> None:
    info = detect(symbol)
    if not info:
        log.warning(f"Não foi possível detectar o tipo de ativo para: {symbol}")
        return

    # Roteamento Dinâmico
    fonte_definida = info["source"]

    if fonte_definida == "twelvedata":
        escolha_usuario = os.getenv("FOREX_SOURCE", "twelvedata").lower()
    elif fonte_definida == "binance":
        escolha_usuario = os.getenv("CRYPTO_SOURCE", "binance").lower()
    else:
        escolha_usuario = fonte_definida

    if escolha_usuario in _FETCHERS:
        coletor_selecionado = _FETCHERS[escolha_usuario]
        log.debug(f"[{symbol}] Roteado dinamicamente para o provedor: {escolha_usuario}")
    else:
        coletor_selecionado = _FETCHERS[fonte_definida]
        log.warning(f"Provedor '{escolha_usuario}' inválido. Utilizando padrão: {fonte_definida}")

    df = coletor_selecionado(info["symbol"], interval, limit=100)
    if df is None or df.empty:
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
                time.sleep(2)
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