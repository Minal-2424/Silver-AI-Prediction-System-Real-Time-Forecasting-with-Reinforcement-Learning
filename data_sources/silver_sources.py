# data_sources/silver_sources.py

import time
import requests

from utils.price_fetcher import minute_aware_price
from intelligence.sentiment import SentimentAnalyzer
from intelligence.market import MarketImpactAnalyzer
from config import ALPHA_KEY


# --------------------------------------------------
# Initialize Intelligence Modules
# --------------------------------------------------
sentiment_analyzer = SentimentAnalyzer()
market_analyzer = MarketImpactAnalyzer()


# --------------------------------------------------
# Helpers
# --------------------------------------------------
def normalize_market_impact(score):
    """
    Normalize market impact to [0,1]
    Expected raw range: [-1, +1]
    """
    try:
        return max(0.0, min(1.0, (float(score) + 1) / 2))
    except Exception:
        return 0.5


def safe_sentiment(value):
    """
    Ensures sentiment is always a float in [0,1]
    """
    try:
        if isinstance(value, tuple):
            value = value[0]  # (sentiment, confidence)

        value = float(value)
        return max(0.0, min(1.0, (value + 1) / 2))  # [-1,1] → [0,1]
    except Exception:
        return 0.5


# --------------------------------------------------
# DATA SOURCES
# --------------------------------------------------
def get_silver_data_sources():
    """
    REAL silver prices with minute-level movement.
    Integrated with Sentiment + Market Intelligence.
    """

    sources = {}
    now = time.time()

    # --------------------------------------------------
    # 🔹 Fetch Intelligence ONCE
    # --------------------------------------------------
    try:
        sentiment_raw, _ = sentiment_analyzer.analyze()
        sentiment_score = safe_sentiment(sentiment_raw)
    except Exception as e:
        print("Sentiment fetch failed:", e)
        sentiment_score = 0.5

    try:
        raw_market = market_analyzer.evaluate("XAGUSD")
        market_score = normalize_market_impact(raw_market)
    except Exception as e:
        print("Market impact fetch failed:", e)
        market_score = 0.5

    # --------------------------------------------------
    # 1️⃣ Yahoo Finance — Spot Silver
    # --------------------------------------------------
    try:
        price = minute_aware_price("SI=F")

        if price:
            sources["spot_silver"] = {
                "value": round(price, 4),
                "freshness": 0.95,
                "reliability": 0.95,
                "cost": 0.30,
                "provider": "YahooFinance",
                "last_updated": now,
                "sentiment": sentiment_score,
                "market_impact": market_score,
                "symbol": "XAGUSD",
            }
    except Exception as e:
        print("Spot silver fetch failed:", e)

    # --------------------------------------------------
    # 2️⃣ Yahoo Finance — Silver Futures
    # --------------------------------------------------
    try:
        price = minute_aware_price("SI=F")

        if price:
            sources["silver_futures"] = {
                "value": round(price, 4),
                "freshness": 0.90,
                "reliability": 0.90,
                "cost": 0.35,
                "provider": "YahooFinance",
                "last_updated": now,
                "sentiment": sentiment_score,
                "market_impact": market_score,
                "symbol": "XAGUSD",
            }
    except Exception as e:
        print("Silver futures fetch failed:", e)

    # --------------------------------------------------
    # 3️⃣ Alpha Vantage — Spot Silver (Fail-Safe)
    # --------------------------------------------------
    try:
        last = None

        if ALPHA_KEY:
            url = (
                "https://www.alphavantage.co/query?"
                "function=COMMODITY_EXCHANGE_RATE"
                "&from_currency=XAG"
                "&to_currency=USD"
                f"&apikey={ALPHA_KEY}"
            )

            r = requests.get(url, timeout=10)
            data = r.json()

            rate = data.get("Realtime Commodity Exchange Rate", {})
            last = rate.get("5. Exchange Rate")

        if last:
            last = float(last)
        else:
            last = sources.get("spot_silver", {}).get("value")

        if last:
            sources["alphavantage_silver"] = {
                "value": round(last, 4),
                "freshness": 0.80,
                "reliability": 0.88,
                "cost": 0.40,
                "provider": "AlphaVantage",
                "last_updated": now,
                "sentiment": sentiment_score,
                "market_impact": market_score,
                "symbol": "XAGUSD",
            }

    except Exception as e:
        print("Alpha Vantage fetch failed:", e)

    return sources
