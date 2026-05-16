"""
Detecta o tipo de ativo pelo símbolo digitado e retorna
a fonte de dados correta e o símbolo no formato aceito por ela.
"""

# Moedas fiat reconhecidas para detecção de Forex
_FIAT = {
    "USD", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD",
    "CAD", "SEK", "NOK", "DKK", "SGD", "HKD", "MXN",
    "ZAR", "TRY", "BRL", "CNY", "INR", "KRW", "PLN",
}

# Sufixos de cotação cripto
_CRYPTO_QUOTES = ("USDT", "USDC", "BUSD", "USD", "BTC", "ETH", "BNB")

def _clean(symbol: str) -> str:
    """Remove separadores e converte para maiúsculas."""
    return symbol.upper().strip().replace("/", "").replace("-", "").replace("_", "")

def detect(symbol: str) -> dict:
    """
    Recebe o símbolo como o usuário digitou e retorna o símbolo formatado.
    """
    c = _clean(symbol)

    # Forex
    if len(c) == 6 and c.isalpha():
        base, quote = c[:3], c[3:]
        if base in _FIAT and quote in _FIAT:
            fmt = f"{base}/{quote}"
            return {"source": "twelvedata", "symbol": fmt, "display": fmt}

    # Cripto
    if c.endswith("USD") and not c.endswith("USDT"):
        c = c[:-3] + "USDT"

    for q in _CRYPTO_QUOTES:
        if c.endswith(q) and len(c) > len(q):
            return {"source": "binance", "symbol": c, "display": c}

    # Fallback
    return {"source": "binance", "symbol": c, "display": c}