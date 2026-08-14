"""
Alerte croisement EMA et analyse de marché automatisée.
Notification Telegram envoyée via GitHub Actions ou exécutée localement.
"""

import json
import os
import requests
from analyzer import MarketAnalyzer
from recommender import TradeRecommender

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
STATE_FILE = "state.json"

DEFAULT_CONFIG = {
    "BTC-USD":  {"interval": "15m", "period": "5d", "min_confidence": 60},
    "ETH-USD":  {"interval": "15m", "period": "5d", "min_confidence": 60},
    "EURUSD=X": {"interval": "15m", "period": "5d", "min_confidence": 60},
    "GBPUSD=X": {"interval": "15m", "period": "5d", "min_confidence": 60},
    "USDJPY=X": {"interval": "15m", "period": "5d", "min_confidence": 60},
    "AAPL":     {"interval": "15m", "period": "5d", "min_confidence": 60},
}

SYMBOLS_CONFIG = json.loads(os.getenv("SYMBOLS_CONFIG", json.dumps(DEFAULT_CONFIG)))


def send_telegram(message: str) -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram] Token ou Chat ID non défini, affichage console :")
        print(message)
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    resp = requests.post(
        url,
        data={"chat_id": TELEGRAM_CHAT_ID, "text": message},
        timeout=15,
    )
    resp.raise_for_status()


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def check_symbol(symbol: str, cfg: dict, state: dict) -> None:
    interval = cfg.get("interval", "15m")
    period = cfg.get("period", "5d")
    min_confidence = cfg.get("min_confidence", 60)

    try:
        analyzer = MarketAnalyzer(symbol=symbol, interval=interval, period=period)
        analysis = analyzer.analyze()
    except Exception as e:
        print(f"[{symbol}] Erreur d'analyse : {e}")
        return

    recommender = TradeRecommender(min_confidence=min_confidence)
    recommendation = recommender.evaluate(analysis)

    action = recommendation["action"]
    last_time = analysis["timestamp"]
    signal_key = f"{action}-{last_time}"

    symbol_state = state.get(symbol, {})

    if action in ["BUY", "SELL"] and symbol_state.get("last_signal") != signal_key:
        emoji = "🟢" if action == "BUY" else "🔴"
        reasons_text = "\n".join([f"• {r}" for r in recommendation["reasons"]])
        warnings_text = "\n".join([f"⚠️ {w}" for w in recommendation["warnings"]]) if recommendation["warnings"] else "Aucun"

        message = (
            f"{emoji} **ALERTE DE TRADING: {symbol}** ({interval})\n"
            f"Action recommandée : **{action}** (Confiance: {recommendation['confidence_score']}%)\n\n"
            f"📊 **Niveaux Clés** :\n"
            f"Prix d'entrée: {recommendation['entry_price']}\n"
            f"Stop Loss: {recommendation['stop_loss']}\n"
            f"Take Profit 1: {recommendation['take_profit_1']}\n"
            f"Take Profit 2: {recommendation['take_profit_2']}\n"
            f"Ratio R:R: {recommendation['risk_reward_ratio']}\n\n"
            f"💡 **Facteurs de Confluence** :\n{reasons_text}\n\n"
            f"⚠️ **Points d'attention** :\n{warnings_text}\n"
            f"🕒 Date/Heure : {last_time}"
        )
        send_telegram(message)
        symbol_state["last_signal"] = signal_key
        state[symbol] = symbol_state
        print(f"[{symbol}] Alerte {action} envoyée avec un score de {recommendation['confidence_score']}%")
    else:
        print(f"[{symbol}] Statut: {action} (Confiance: {recommendation['confidence_score']}%) - Aucune nouvelle alerte à déclencher.")


def main() -> None:
    state = load_state()
    for symbol, cfg in SYMBOLS_CONFIG.items():
        check_symbol(symbol, cfg, state)
    save_state(state)


if __name__ == "__main__":
    main()
