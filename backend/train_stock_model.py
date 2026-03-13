"""
Train a Random Forest model for Stock AI Decisions using the Huge Stock Market Dataset.
"""
import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib
import glob

# Constants
DATA_DIR = os.path.join(os.getcwd(), "data", "archive", "Stocks")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "stock_model.pkl")
SAMPLE_SIZE = 50  # Number of tickers to train on for efficiency

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def prepare_data():
    all_data = []
    files = glob.glob(os.path.join(DATA_DIR, "*.txt"))
    
    if not files:
        raise ValueError(f"No ticker files found in {DATA_DIR}")
        
    print(f"[*] Found {len(files)} tickers. Training on a sample of {SAMPLE_SIZE}...")
    
    # Use a fixed seed for reproducibility in sampling
    np.random.seed(42)
    sample_files = np.random.choice(files, min(SAMPLE_SIZE, len(files)), replace=False)
    
    for f in sample_files:
        try:
            df = pd.read_csv(f)
            if len(df) < 250: continue # Skip if too short
            
            # Feature Engineering
            df['MA50'] = df['Close'].rolling(window=50).mean()
            df['MA200'] = df['Close'].rolling(window=200).mean()
            df['RSI'] = compute_rsi(df['Close'])
            df['Return'] = df['Close'].pct_change()
            
            # Labeling: 1 if price rises > 3% in next 5 days
            df['Target'] = (df['Close'].shift(-5) > df['Close'] * 1.03).astype(int)
            
            # Drop NaNs from windowing
            df = df.dropna()
            
            # Keep relevant columns
            features = df[['Close', 'MA50', 'MA200', 'RSI', 'Return', 'Target']]
            all_data.append(features)
        except Exception as e:
            print(f"[!] Error processing {f}: {e}")

    if not all_data:
        raise ValueError("No valid data collected after processing tickers.")
        
    return pd.concat(all_data)

def train():
    print("[*] Loading and engineering features...")
    df = prepare_data()
    
    X = df[['Close', 'MA50', 'MA200', 'RSI', 'Return']]
    y = df['Target']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print(f"[*] Training on {len(X_train)} samples...")
    model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, class_weight='balanced')
    model.fit(X_train, y_train)
    
    print("\n[*] Model Evaluation:")
    y_pred = model.predict(X_test)
    print(classification_report(y_test, y_pred, target_names=["Wait/Sell", "Buy Signal"]))
    
    joblib.dump(model, MODEL_PATH)
    print(f"[OK] Stock model saved to {MODEL_PATH}")

if __name__ == "__main__":
    train()
