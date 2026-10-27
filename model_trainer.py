import os
import glob
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score

os.makedirs("models", exist_ok=True)

def load_filtered_data():
    files = glob.glob("data/filtered/filtered_*.csv")
    if not files:
        print("No filtered data found yet! Make sure your previous steps generated files in data/filtered/")
        return None
    
    latest_file = max(files, key=os.path.getctime)
    print(f"Loading training data from: {latest_file}")
    return pd.read_csv(latest_file)

def train_prediction_model():
    df = load_filtered_data()
    if df is None:
        return

    # Basic feature selection for the model
    features = ['RSI', 'ATR', 'SMA_20', 'close', 'volume']
    
    # Drop rows with missing values
    df = df.dropna(subset=features)
    
    if len(df) < 10:
        print("Not enough rows of data to train a model yet. Collect more data over the trading week!")
        return

    # Create a target label: Will the price go up in the next period? (1 = Up, 0 = Down)
    df['Target'] = (df['close'].shift(-1) > df['close']).astype(int)
    
    # Drop the last row since it won't have a future target
    df = df.iloc[:-1]

    X = df[features]
    y = df['Target']

    # Split into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print("Training XGBoost AI Model on your historical/live features...")
    model = XGBClassifier(n_estimators=100, learning_rate=0.05, max_depth=3)
    model.fit(X_train, y_train)

    # Evaluate model
    predictions = model.predict(X_test)
    acc = accuracy_score(y_test, predictions)
    
    print(f"Model Training Complete! Test Accuracy: {acc * 100:.2f}%")
    
    # Save the trained model model for future real-time predictions
    model.save_model("models/xgb_idx_model.json")
    print("Saved trained model to models/xgb_idx_model.json")

if __name__ == "__main__":
    train_prediction_model()
