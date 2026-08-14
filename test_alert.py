import os
import requests

def test_send_alert():
    symbol = "BTC-USD"
    interval = "15m"
    last_close = 64320.50
    signal = "haussier"
    score = 85
    atr = 312.40
    rsi = 58.4
    macd_hist = 14.20
    ema_trend_val = 62100.00
    ema_fast, ema_slow, ema_trend = 9, 21, 200
    reasons = [
        "EMA Cross (9/21)",
        "Prix > EMA200 (Tendance Haussière)",
        "RSI Bullish (58.4)",
        "MACD Hist Positive (14.20)"
    ]
    last_time = "2026-08-14 13:15:00+00:00"

    # Risk Management (SL / TP)
    sl = last_close - (1.5 * atr)
    tp1 = last_close + (1.5 * atr)
    tp2 = last_close + (2.5 * atr)

    emoji = "🟢" if signal == "haussier" else "🔴"
    action = "ACHAT (BULLISH)" if signal == "haussier" else "VENTE (BEARISH)"
    stars = "⭐" * max(1, score // 20)
    reasons_str = "\n".join([f"  ✓ {r}" for r in reasons])

    message = (
        f"{emoji} *SIGNAL {action}*\n"
        f"📊 Actif : `{symbol}` | UT : `{interval}`\n"
        f"🎯 Score de Confluence : *{score}%* {stars}\n"
        f"───────────────────\n"
        f"💡 *Prix d'entrée* : `{last_close:.2f}`\n"
        f"🛑 *Stop Loss (1.5x ATR)* : `{sl:.2f}`\n"
        f"🎯 *Take Profit 1 (R:R 1.5)* : `{tp1:.2f}`\n"
        f"🚀 *Take Profit 2 (R:R 2.5)* : `{tp2:.2f}`\n"
        f"───────────────────\n"
        f"🔍 *ANALYSE TECHNIQUE* :\n"
        f"• RSI (14) : `{rsi:.1f}`\n"
        f"• MACD Hist : `{macd_hist:.2f}`\n"
        f"• Trend EMA{ema_trend} : `{ema_trend_val:.2f}`\n"
        f"• ATR Volatilité : `{atr:.2f}`\n"
        f"───────────────────\n"
        f"📌 *Facteurs de Confluence* :\n"
        f"{reasons_str}\n"
        f"───────────────────\n"
        f"⏰ Bougie : `{last_time}`"
    )

    print("=== RENDU DU MESSAGE TELEGRAM ===\n")
    print(message)
    print("\n=================================")

    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        res = requests.post(url, json=payload)
        print(f"Statut envoi Telegram : {res.status_code}")
    else:
        print("ℹ️ Clés TELEGRAM_TOKEN et TELEGRAM_CHAT_ID non configurées en local.")

if __name__ == "__main__":
    test_send_alert()
