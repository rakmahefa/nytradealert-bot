"""
Script de test pour vérifier analyzer.py et recommender.py
"""
import json
from analyzer import MarketAnalyzer
from recommender import TradeRecommender

def main():
    symbol = "BTC-USD"
    print(f"--- Analyse du marché pour {symbol} ---")
    analyzer = MarketAnalyzer(symbol=symbol, interval="15m", period="5d")
    analysis = analyzer.analyze()
    
    print(f"Prix de clôture : {analysis['close']}")
    print(f"Tendance : {analysis['trend']}")
    print(f"Volatilité : {analysis['volatility_state']}")
    print(f"Indicateurs : {json.dumps(analysis['indicators'], indent=2)}")
    print(f"Supports / Résistances : {analysis['support_resistance']}")
    
    print("\n--- Recommandation de Trading ---")
    recommender = TradeRecommender(min_confidence=50)
    rec = recommender.evaluate(analysis)
    print(json.dumps(rec, indent=2))

if __name__ == "__main__":
    main()
