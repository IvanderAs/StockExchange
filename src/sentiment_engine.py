import glob
import os
import pandas as pd
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline

# Folder setups
os.makedirs("data/sentiment", exist_ok=True)

# 1. Load Pre-trained Indonesian BERT Sentiment Model
MODEL_NAME = "mdhugol/indonesia-bert-sentiment-classification"
print("Loading Indonesian BERT NLP Model...")

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)

# Set device to GPU (CUDA) if available on your GTX 1050
device = 0 if torch.cuda.is_available() else -1
nlp = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer, device=device)

# Label mappings to numeric score
SCORE_MAP = {
    "LABEL_0": 1.0,   # Positive / Positif
    "LABEL_1": 0.0,   # Neutral / Netral
    "LABEL_2": -1.0   # Negative / Negatif
}

def get_latest_news_file():
    files = glob.glob("data/news/news_*.csv")
    if not files:
        return None
    return max(files, key=os.path.getctime)

def process_sentiment():
    latest_file = get_latest_news_file()
    if not latest_file:
        print("No news CSV found in data/news/")
        return

    print(f" Processing sentiment for: {latest_file}")
    df = pd.read_csv(latest_file)

    scores = []
    labels = []

    for title in df['title']:
        try:
            # Truncate text to fit BERT sequence limit
            result = nlp(str(title)[:512])[0]
            raw_label = result['label']
            confidence = result['score']
            
            # Map label to numerical value weighted by confidence
            base_score = SCORE_MAP.get(raw_label, 0.0)
            weighted_score = base_score * confidence
            
            labels.append(raw_label)
            scores.append(round(weighted_score, 4))
        except Exception as e:
            labels.append("LABEL_1")
            scores.append(0.0)

    df['sentiment_label'] = labels
    df['sentiment_score'] = scores

    # Output file
    base_name = os.path.basename(latest_file).replace("news_", "sentiment_")
    out_file = f"data/sentiment/{base_name}"
    df.to_csv(out_file, index=False)

    print(f" Done! Saved sentiment analysis to {out_file}")
    print("\nSample Output:")
    print(df[['source', 'title', 'sentiment_score']].head())

if __name__ == "__main__":
    process_sentiment()
