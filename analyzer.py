"""
Module d'analyse technique du marché.
Centralise le calcul des indicateurs, l'évaluation de la tendance et la détection des niveaux clés.
"""
import pandas as pd
import numpy as np
import yfinance as yf
from typing import Dict, Any, Optional, List


class MarketAnalyzer:
    """Effectue des analyses techniques approfondies sur un actif."""

    def __init__(self, symbol: str, interval: str = "15m", period: str = "5d"):
        self.symbol = symbol
        self.interval = interval
        self.period = period

    def fetch_data(self) -> pd.DataFrame:
        """Télécharge les données de marché via yfinance."""
        df = yf.download(
            tickers=self.symbol,
            period=self.period,
            interval=self.interval,
            progress=False,
            auto_adjust=True,
        )
        if df.empty:
            raise ValueError(f"Impossible de récupérer les données pour {self.symbol}")
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcule l'ensemble des indicateurs techniques."""
        df = df.copy()
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]

        # Moyennes mobiles exponentielles
        df["EMA9"] = close.ewm(span=9, adjust=False).mean()
        df["EMA21"] = close.ewm(span=21, adjust=False).mean()
        df["EMA50"] = close.ewm(span=50, adjust=False).mean()
        df["EMA200"] = close.ewm(span=200, adjust=False).mean()

        # RSI (14)
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1/14, min_periods=14).mean()
        avg_loss = loss.ewm(alpha=1/14, min_periods=14).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        df["RSI14"] = 100 - (100 / (1 + rs))

        # MACD (12, 26, 9)
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        df["MACD_Line"] = ema12 - ema26
        df["MACD_Signal"] = df["MACD_Line"].ewm(span=9, adjust=False).mean()
        df["MACD_Hist"] = df["MACD_Line"] - df["MACD_Signal"]

        # ATR (14)
        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ], axis=1).max(axis=1)
        df["ATR14"] = tr.rolling(window=14).mean()

        # Bandes de Bollinger (20, 2)
        df["BB_Middle"] = close.rolling(window=20).mean()
        bb_std = close.rolling(window=20).std()
        df["BB_Upper"] = df["BB_Middle"] + (bb_std * 2)
        df["BB_Lower"] = df["BB_Middle"] - (bb_std * 2)
        df["BB_Width"] = (df["BB_Upper"] - df["BB_Lower"]) / df["BB_Middle"]

        # Volume Moyenne Mobile
        df["Vol_SMA20"] = volume.rolling(window=20).mean()
        df["Vol_Ratio"] = volume / df["Vol_SMA20"].replace(0, np.nan)

        return df

    def detect_support_resistance(self, df: pd.DataFrame, window: int = 20) -> Dict[str, float]:
        """Détecte les niveaux de support et de résistance récents."""
        recent_data = df.tail(window * 3)
        support = float(recent_data["Low"].min())
        resistance = float(recent_data["High"].max())
        pivot = float((recent_data["High"].iloc[-1] + recent_data["Low"].iloc[-1] + recent_data["Close"].iloc[-1]) / 3)
        return {
            "support": round(support, 4),
            "resistance": round(resistance, 4),
            "pivot": round(pivot, 4)
        }

    def analyze(self, df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """Effectue une analyse complète et renvoie le rapport contextuel."""
        if df is None:
            df = self.fetch_data()
        
        df = self.compute_indicators(df)
        last = df.iloc[-1]
        prev = df.iloc[-2]

        # Tendance globale
        trend = "NEUTRAL"
        if last["Close"] > last["EMA200"] and last["EMA9"] > last["EMA21"]:
            trend = "BULLISH"
        elif last["Close"] < last["EMA200"] and last["EMA9"] < last["EMA21"]:
            trend = "BEARISH"

        # Volatilité et état de marché
        volatility_state = "NORMAL"
        if pd.notna(last["BB_Width"]):
            if last["BB_Width"] < df["BB_Width"].tail(50).quantile(0.2):
                volatility_state = "SQUEEZE" # Volatilité très basse, possible breakout
            elif last["BB_Width"] > df["BB_Width"].tail(50).quantile(0.8):
                volatility_state = "HIGH" # Forte volatilité

        sr_levels = self.detect_support_resistance(df)

        # Signal EMA Cross récent
        ema_cross = None
        if prev["EMA9"] <= prev["EMA21"] and last["EMA9"] > last["EMA21"]:
            ema_cross = "GOLDEN_CROSS"
        elif prev["EMA9"] >= prev["EMA21"] and last["EMA9"] < last["EMA21"]:
            ema_cross = "DEATH_CROSS"

        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "timestamp": str(df.index[-1]),
            "close": float(last["Close"]),
            "high": float(last["High"]),
            "low": float(last["Low"]),
            "trend": trend,
            "volatility_state": volatility_state,
            "ema_cross": ema_cross,
            "indicators": {
                "rsi": round(float(last["RSI14"]), 2) if pd.notna(last["RSI14"]) else None,
                "macd_hist": round(float(last["MACD_Hist"]), 4) if pd.notna(last["MACD_Hist"]) else None,
                "macd_line": round(float(last["MACD_Line"]), 4) if pd.notna(last["MACD_Line"]) else None,
                "macd_signal": round(float(last["MACD_Signal"]), 4) if pd.notna(last["MACD_Signal"]) else None,
                "atr": round(float(last["ATR14"]), 4) if pd.notna(last["ATR14"]) else None,
                "ema9": round(float(last["EMA9"]), 4),
                "ema21": round(float(last["EMA21"]), 4),
                "ema200": round(float(last["EMA200"]), 4),
                "vol_ratio": round(float(last["Vol_Ratio"]), 2) if pd.notna(last["Vol_Ratio"]) else 1.0
            },
            "support_resistance": sr_levels,
            "raw_df": df
        }
