"""
Alerte croisement EMA9/EMA21 sur plusieurs marches -> notification Telegram
Gratuit et illimite, execute par GitHub Actions (voir .github/workflows/ema-alert.yml)
"""

import os
import json
import yfinance as yf
import requests

# Exemples de symboles Yahoo Finance : BTC-USD, ETH-USD (crypto) / EURUSD=X, GBPUSD=X (forex)
# / AAPL, MSFT (actions) / ^GSPC, ^NDX (indices)
SYMBOLS = [s.strip() for s in os.environ.get("SYMBOLS", "BTC-USD,EURUSD=X,AAPL,^GSPC").split(",") if s.strip()]
INTERVAL = os.environ.get("INTERVAL", "5m")
PERIOD = os.environ.get("PERIOD", "5d")
TELEGRAM_TOKEN = os.environ["8812848116:AAEh9pAGXl5dK_ORC4TZ83Jc3JIAw06Y3rw"]
TELEGRAM_CHAT_ID = os.environ["6295934596"]
STATE_FILE = "state.json"


def send_telegram(message: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    resp = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=15)
    resp.raise_for_status()


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)


def check_symbol(symbol: str, data, state: dict) -> None:
    if data is None or data.empty or "Close" not in data or len(data["Close"].dropna()) < 22:
        print(f"[{symbol}] pas assez de donnees, on reessaiera au prochain run.")
        return

    close = data["Close"].dropna()
    ema9 = close.ewm(span=9, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()

    prev_ema9, prev_ema21 = float(ema9.iloc[-2]), float(ema21.iloc[-2])
    last_ema9, last_ema21 = float(ema9.iloc[-1]), float(ema21.iloc[-1])
    last_close = float(close.iloc[-1])
    last_time = str(close.index[-1])

    signal = None
    if prev_ema9 <= prev_ema21 and last_ema9 > last_ema21:
        signal = "haussier"
    elif prev_ema9 >= prev_ema21 and last_ema9 < last_ema21:
        signal = "baissier"

    symbol_state = state.get(symbol, {})
    signal_key = f"{signal}-{last_time}" if signal else None

    if signal and symbol_state.get("last_signal") != signal_key:
        emoji = "🟢" if signal == "haussier" else "🔴"
        message = (
            f"{emoji} {symbol} ({INTERVAL})\n"
            f"Croisement EMA9/EMA21 {signal}\n"
            f"Prix: {last_close:.5f}\n"
            f"Bougie: {last_time}"
        )
        send_telegram(message)
        symbol_state["last_signal"] = signal_key
        state[symbol] = symbol_state
        print(f"[{symbol}] alerte envoyee.")
    else:
        print(f"[{symbol}] aucun nouveau croisement.")


def main() -> None:
    data = yf.download(
        SYMBOLS,
        period=PERIOD,
        interval=INTERVAL,
        progress=False,
        auto_adjust=True,
        group_by="ticker",
    )

    state = load_state()

    for symbol in SYMBOLS:
        try:
            symbol_data = data[symbol]
        except (KeyError, TypeError):
            print(f"[{symbol}] telechargement impossible, symbole ignore.")
            continue
        check_symbol(symbol, symbol_data, state)

    save_state(state)


if __name__ == "__main__":
    main()
