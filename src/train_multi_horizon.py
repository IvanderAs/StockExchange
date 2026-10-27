import os
import glob
import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

os.makedirs("../models", exist_ok=True)

def prepare_historical_dataset():
    """
    Merges historical price candles, technical indicators, sentiment scores, 
    and market category features across training data.
    """
    # 1. Load technical & market snapshot features
    tech_files = glob.glob("../data/technical/technical_*.csv")
    if not tech_files:
        print("❌ No technical datasets found!")
        return None, None
        
    latest_tech = max(tech_files, key=os.path.getctime)
    df = pd.read_csv(latest_tech)

    # 2. Define standard feature columns
    feature_cols = ['RSI', 'ATR', 'SMA_20', 'close', 'volume']
    
    # Optional: Merge sentiment scores if sentiment files exist
    sent_files = glob.glob("../data/sentiment/sentiment_*.csv")
    if sent_files:
        latest_sent = max(sent_files, key=os.path.getctime)
        df_sent = pd.read_csv(latest_sent)
        if 'sentiment_score' in df_sent.columns:
            # Average sentiment score integrated as a feature
            avg_sentiment = df_sent['sentiment_score'].mean()
            df['Sentiment_Score'] = avg_sentiment
            feature_cols.append('Sentiment_Score')
        else:
            df['Sentiment_Score'] = 0.0
            feature_cols.append('Sentiment_Score')
    else:
        df['Sentiment_Score'] = 0.0
        feature_cols.append('Sentiment_Score')

    df = df.dropna(subset=['close', 'volume'] + feature_cols)
    if len(df) < 10:
        print("⚠️ Not enough valid rows to train.")
        return None, None

    # 3. Target Label: 1 if price increases next period, 0 if it decreases
    df['Target_1D'] = (df['close'].shift(-1) > df['close']).astype(int)
    df = df.iloc[:-1] # Remove last row due to shift NaN

    return df, feature_cols

def train_sentiment_aware_model():
    df, features = prepare_historical_dataset()
    if df is None or features is None:
        return

    X = df[features]
    y = df['Target_1D']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Calculate class imbalance ratio dynamically
    num_neg = (y_train == 0).sum()
    num_pos = (y_train == 1).sum()
    ratio = num_neg / num_pos if num_pos > 0 else 1.0

    print(f"🧠 Training XGBoost AI Model with parameters: {features}")
    print(f"⚖️ Class Imbalance Ratio (Neg/Pos): {ratio:.2f}")

    model = XGBClassifier(
        n_estimators=200,
        learning_rate=0.03,
        max_depth=4,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=ratio,  # Balances precision & recall for BUY opportunities
        random_state=42
    )
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    print("\n--- MODEL PERFORMANCE REPORT ---")
    print(classification_report(y_test, predictions))

    # Save trained model artifact
    model_path = "../models/xgb_idx_sentiment_aware.json"
    model.save_model(model_path)
    print(f"✅ Saved trained sentiment-aware model to: {model_path}")

if __name__ == "__main__":
    train_sentiment_aware_model()
