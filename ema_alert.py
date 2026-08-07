"""
Alerte croisement EMA (periodes/unites de temps adaptees par actif)
+ filtre de tendance de fond (EMA200) pour reduire les faux signaux
-> notification Telegram. Gratuit et illimite, declenche par cron-job.org
qui appelle workflow_dispatch toutes les 5 min.
"""

import os
import json
from collections import defaultdict

import yfinance as yf
import requests

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
STATE_FILE = "state.json"

# ema_trend = EMA de fond utilisee comme filtre de tendance : une alerte haussiere
# n'est envoyee que si le prix est deja au-dessus, une alerte baissiere seulement
# si le prix est en dessous. Mets trend_filter a false pour desactiver ce filtre
# sur un symbole en particulier.
DEFAULT_CONFIG = {
    "BTC-USD":  {"interval": "15m", "period": "60d",  "ema_fast": 9,  "ema_slow": 21, "ema_trend": 200, "trend_filter": True},
    "ETH-USD":  {"interval": "15m", "period": "60d",  "ema_fast": 9,  "ema_slow": 21, "ema_trend": 200, "trend_filter": True},
    "EURUSD=X": {"interval": "15m", "period": "60d",  "ema_fast": 9,  "ema_slow": 21, "ema_trend": 200, "trend_filter": True},
    "GBPUSD=X": {"interval": "15m", "period": "60d",  "ema_fast": 9,  "ema_slow": 21, "ema_trend": 200, "trend_filter": True},
    "USDJPY=X": {"interval": "15m", "period": "60d",  "ema_fast": 9,  "ema_slow": 21, "ema_trend": 200, "trend_filter": True},
    "AUDUSD=X": {"interval": "15m", "period": "60d",  "ema_fast": 9,  "ema_slow": 21, "ema_trend": 200, "trend_filter": True},
    "USDCAD=X": {"interval": "15m", "period": "60d",  "ema_fast": 9,  "ema_slow": 21, "ema_trend": 200, "trend_filter": True},
    "USDCHF=X": {"interval": "15m", "period": "60d",  "ema_fast": 9,  "ema_slow": 21, "ema_trend": 200, "trend_filter": True},
    "AAPL":     {"interval": "15m", "period": "60d",  "ema_fast": 20, "ema_slow": 50, "ema_trend": 200, "trend_filter": True},
    "^GSPC":    {"interval": "1h",  "period": "180d", "ema_fast": 20, "ema_slow": 50, "ema_trend": 200, "trend_filter": True},
}

SYMBOLS_CONFIG = json.loads(os.environ.get("SYMBOLS_CONFIG", json.dumps(DEFAULT_CONFIG)))


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


def check_symbol(symbol: str, data, cfg: dict, interval: str, state: dict) -> None:
    ema_fast, ema_slow = cfg["ema_fast"], cfg["ema_slow"]
    ema_trend = cfg.get("ema_trend", 200)
    use_trend_filter = cfg.get("trend_filter", True)

    needed = max(ema_slow, ema_trend if use_trend_filter else 0) + 1
    if data is None or data.empty or "Close" not in data or len(data["Close"].dropna()) < needed:
        print(f"[{symbol}] pas assez de donnees ({needed} bougies minimum), on reessaiera.")
        return

    close = data["Close"].dropna()
    fast = close.ewm(span=ema_fast, adjust=False).mean()
    slow = close.ewm(span=ema_slow, adjust=False).mean()

    prev_fast, prev_slow = float(fast.iloc[-2]), float(slow.iloc[-2])
    last_fast, last_slow = float(fast.iloc[-1]), float(slow.iloc[-1])
    last_close = float(close.iloc[-1])
    last_time = str(close.index[-1])

    signal = None
    if prev_fast <= prev_slow and last_fast > last_slow:
        signal = "haussier"
    elif prev_fast >= prev_slow and last_fast < last_slow:
        signal = "baissier"

    if signal and use_trend_filter:
        trend = close.ewm(span=ema_trend, adjust=False).mean()
        last_trend = float(trend.iloc[-1])
        if signal == "haussier" and last_close < last_trend:
            print(f"[{symbol}] croisement haussier ignore (prix sous l'EMA{ema_trend}).")
            signal = None
        elif signal == "baissier" and last_close > last_trend:
            print(f"[{symbol}] croisement baissier ignore (prix au-dessus de l'EMA{ema_trend}).")
            signal = None

    symbol_state = state.get(symbol, {})
    signal_key = f"{signal}-{last_time}" if signal else None

    if signal and symbol_state.get("last_signal") != signal_key:
        emoji = "🟢" if signal == "haussier" else "🔴"
        message = (
            f"{emoji} {symbol} ({interval}, EMA{ema_fast}/{ema_slow}, filtre EMA{ema_trend})\n"
            f"Croisement {signal}\n"
            f"Prix: {last_close:.5f}\n"
            f"Bougie: {last_time}"
        )
        send_telegram(message)
        symbol_state["last_signal"] = signal_key
        state[symbol] = symbol_state
        print(f"[{symbol}] alerte envoyee.")
    elif signal:
        print(f"[{symbol}] signal deja notifie precedemment.")
    else:
        print(f"[{symbol}] aucun signal retenu.")


def main() -> None:
    state = load_state()

    groups = defaultdict(list)
    for symbol, cfg in SYMBOLS_CONFIG.items():
        groups[(cfg["interval"], cfg["period"])].append(symbol)

    for (interval, period), symbols in groups.items():
        data = yf.download(
            symbols,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True,
            group_by="ticker",
        )

        for symbol in symbols:
            try:
                symbol_data = data[symbol]
            except (KeyError, TypeError):
                print(f"[{symbol}] telechargement impossible, symbole ignore.")
                continue
            check_symbol(symbol, symbol_data, SYMBOLS_CONFIG[symbol], interval, state)

    save_state(state)


if __name__ == "__main__":
    main()
