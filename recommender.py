"""
Module de recommandation de trading.
Analyse le contexte fourni par MarketAnalyzer et génère une recommandation d'action complète.
"""
from typing import Dict, Any, List


class TradeRecommender:
    """Génère des conseils de trading motivés et des plans de gestion du risque."""

    def __init__(self, min_confidence: int = 60):
        self.min_confidence = min_confidence

    def evaluate(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prend un dictionnaire issu de MarketAnalyzer.analyze() et retourne la recommandation.
        """
        close = analysis["close"]
        trend = analysis["trend"]
        volatility_state = analysis["volatility_state"]
        ema_cross = analysis.get("ema_cross")
        indicators = analysis["indicators"]
        sr = analysis["support_resistance"]

        score = 50
        reasons: List[str] = []
        warnings: List[str] = []

        action = "WAIT"

        # 1. Évaluation du sens et confluence
        if trend == "BULLISH":
            score += 15
            reasons.append("Tendance de fond haussière (Prix > EMA200)")
        elif trend == "BEARISH":
            score += 15
            reasons.append("Tendance de fond baissière (Prix < EMA200)")

        # Signals de Croisement
        if ema_cross == "GOLDEN_CROSS":
            score += 20
            reasons.append("Croisement haussier rapide (EMA9 > EMA21)")
            if trend == "BULLISH":
                action = "BUY"
        elif ema_cross == "DEATH_CROSS":
            score += 20
            reasons.append("Croisement baissier rapide (EMA9 < EMA21)")
            if trend == "BEARISH":
                action = "SELL"

        # RSI Analysis
        rsi = indicators.get("rsi")
        if rsi is not None:
            if rsi < 30:
                if action == "BUY":
                    score += 15
                    reasons.append(f"RSI en survente ({rsi}), rebond potentiel")
                else:
                    warnings.append(f"RSI en survente ({rsi})")
            elif rsi > 70:
                if action == "SELL":
                    score += 15
                    reasons.append(f"RSI en surachat ({rsi}), correction potentielle")
                else:
                    warnings.append(f"RSI en surachat ({rsi})")
            elif 40 <= rsi <= 60:
                score += 10
                reasons.append(f"RSI équilibré ({rsi})")

        # Volatilité & Volume
        vol_ratio = indicators.get("vol_ratio", 1.0)
        if vol_ratio > 1.5:
            score += 10
            reasons.append(f"Volume supérieur à la moyenne (x{vol_ratio})")

        if volatility_state == "SQUEEZE":
            warnings.append("Marché en Squeeze de volatilité : attention au risque de faux breakout")
        elif volatility_state == "HIGH":
            warnings.append("Forte volatilité détectée : élargir légèrement le Stop Loss")

        confidence_score = min(max(score, 0), 100)

        # Si le score de confiance ne passe pas le seuil minimum, repasser en WAIT
        if confidence_score < self.min_confidence:
            action = "WAIT"

        # 2. Calcul de la stratégie de sortie (SL / TP)
        atr = indicators.get("atr") or (close * 0.01)
        entry_price = close
        stop_loss = None
        tp1 = None
        tp2 = None
        rr_ratio = None

        if action == "BUY":
            # SL placé sous le support récent ou ATR
            sl_atr = entry_price - (1.5 * atr)
            sl_support = sr["support"]
            stop_loss = round(max(sl_atr, sl_support * 0.998), 4)
            
            risk = entry_price - stop_loss
            if risk > 0:
                tp1 = round(entry_price + (risk * 1.5), 4)
                tp2 = round(entry_price + (risk * 2.5), 4)
                rr_ratio = round((tp1 - entry_price) / risk, 2)
        elif action == "SELL":
            # SL placé au-dessus de la résistance récente ou ATR
            sl_atr = entry_price + (1.5 * atr)
            sl_resistance = sr["resistance"]
            stop_loss = round(min(sl_atr, sl_resistance * 1.002), 4)
            
            risk = stop_loss - entry_price
            if risk > 0:
                tp1 = round(entry_price - (risk * 1.5), 4)
                tp2 = round(entry_price - (risk * 2.5), 4)
                rr_ratio = round((entry_price - tp1) / risk, 2)

        return {
            "symbol": analysis["symbol"],
            "action": action,
            "confidence_score": confidence_score,
            "entry_price": round(entry_price, 4),
            "stop_loss": stop_loss,
            "take_profit_1": tp1,
            "take_profit_2": tp2,
            "risk_reward_ratio": rr_ratio,
            "reasons": reasons,
            "warnings": warnings
        }
