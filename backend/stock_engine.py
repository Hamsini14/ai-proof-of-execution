"""
Stock Engine: Fetches real-time stock data and generates AI predictions.
Implements:
  - Technical indicator computation (MA50, RSI14)
  - Simple predictive logic (BUY/SELL/HOLD) based on indicators
"""
from typing import Dict, Any, Tuple
import yfinance as yf
import pandas as pd
import traceback

MODEL_VERSION = "Stock_Indicator_AI_v1.0"

def _fetch_stock_data(ticker: str) -> pd.DataFrame:
    """Fetch the last 60 days of daily price data using yfinance."""
    stock = yf.Ticker(ticker)
    hist = stock.history(period="60d")
    if hist.empty:
        raise ValueError(f"No data found for ticker {ticker}")
    return hist

def _compute_indicators(hist: pd.DataFrame) -> Tuple[float, float, float]:
    """Compute Current Price, 50-day MA, and 14-day RSI."""
    current_price = float(hist['Close'].iloc[-1])
    
    # Compute 50-day Moving Average
    if len(hist) >= 50:
        ma_50 = float(hist['Close'].rolling(window=50).mean().iloc[-1])
    else:
        ma_50 = float(hist['Close'].mean())

    # Compute 14-day RSI
    delta = hist['Close'].diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    
    avg_gain = gain.rolling(window=14, min_periods=1).mean()
    avg_loss = loss.rolling(window=14, min_periods=1).mean()
    
    rs = avg_gain / avg_loss
    rsi_series = 100 - (100 / (1 + rs))
    rsi_14 = float(rsi_series.iloc[-1])

    return current_price, ma_50, rsi_14

def _predict(current_price: float, ma_50: float, rsi_14: float) -> Tuple[str, float]:
    """
    Generate AI prediction using indicator heuristic.
    Buy if Price > MA50 and RSI < 70 (trend up, not overbought).
    Sell if Price < MA50 and RSI > 30 (trend down, not oversold).
    Hold otherwise.
    """
    decision = "HOLD"
    confidence = 0.50 # Base confidence

    if current_price > ma_50 and rsi_14 < 70:
        decision = "BUY"
        # Confidence increases as RSI goes lower (more room to grow)
        confidence = 0.60 + ((70 - rsi_14) / 70) * 0.35 
    elif current_price < ma_50 and rsi_14 > 30:
        decision = "SELL"
        # Confidence increases as RSI goes higher (more overbought)
        confidence = 0.60 + ((rsi_14 - 30) / 70) * 0.35
    else:
        # Hold confidence increases as price is closer to MA
        ratio = min(current_price, ma_50) / max(current_price, ma_50)
        confidence = 0.50 + (ratio * 0.40)
        
    # Cap confidence at 0.99 for realism
    confidence = min(0.99, float(round(confidence, 4)))

    return decision, confidence

def execute_stock_decision(ticker: str) -> Dict[str, Any]:
    """
    Execute stock AI decision fetching data and returning result.
    """
    try:
        hist = _fetch_stock_data(ticker)
        current_price, ma_50, rsi_14 = _compute_indicators(hist)
        decision, confidence = _predict(current_price, ma_50, rsi_14)
        
        return {
            "model_version": MODEL_VERSION,
            "decision": decision,
            "confidence": confidence,
            "current_price": round(current_price, 2),
            "ma_50": round(ma_50, 2),
            "rsi_14": round(rsi_14, 2)
        }
    except Exception as e:
        print(f"Error executing stock decision: {e}")
        traceback.print_exc()
        raise ValueError(f"Failed to analyze stock {ticker}: {str(e)}")

def execute_stock_decision_from_indicators(current_price: float, ma_50: float, rsi_14: float) -> Dict[str, Any]:
    """
    For replay purposes using existing indicators.
    """
    decision, confidence = _predict(current_price, ma_50, rsi_14)
    return {
        "model_version": MODEL_VERSION,
        "decision": decision,
        "confidence": confidence,
    }
