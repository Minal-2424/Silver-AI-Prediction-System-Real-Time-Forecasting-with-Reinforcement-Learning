from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import time
from typing import Any, Dict, List

from agent.agent import DataCollectionAgent
from environment.environment import SilverMarketEnvironment
from models.silver_predictor_arima import SilverPricePredictorARIMA
from utils.logger import AILogger

# -------------------------------------------------
# FastAPI setup
# -------------------------------------------------
app = FastAPI(title="Silver Prediction API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# GLOBAL STATE
# -------------------------------------------------
PREDICTOR = SilverPricePredictorARIMA(order=(2, 1, 2), min_data_points=6)
AGENT = DataCollectionAgent(total_budget=5.0, epsilon=0.2)

LAST_RUN: Dict[str, Any] = {
    "price": None,
    "prediction": None,
    "timestamp": None,
}

MAX_SKIP_SECONDS = 30


# -------------------------------------------------
# Helpers
# -------------------------------------------------
def safe_float(value, fallback=0.0):
    try:
        return float(value)
    except Exception:
        return fallback


def compute_volatility(current, previous):
    if previous is None:
        return "medium"

    pct = abs(current - previous) / previous if previous else 0
    if pct > 0.01:
        return "high"
    if pct > 0.003:
        return "medium"
    return "low"


def compute_priority(source: Dict, remaining_budget: float) -> float:
    """
    SAME LOGIC as agent scoring (but exposed to UI)
    """
    freshness = source.get("freshness", 0.5)
    reliability = source.get("reliability", 0.5)
    cost = source.get("cost", 0.0)
    sentiment = source.get("sentiment", 0.5)
    market_impact = source.get("market_impact", 0.0)

    return round(
        0.35 * freshness
        + 0.35 * reliability
        + 0.15 * sentiment
        + 0.10 * market_impact
        - 0.05 * cost,
        4,
    )


def build_ranked_sources(
    sources: Dict[str, Dict],
    selected_source: str,
    remaining_budget: float,
) -> List[Dict]:

    ranked = []

    for name, s in sources.items():
        ranked.append({
            "id": name,
            "name": (
                "Spot Silver" if name == "spot_silver"
                else "Silver Futures" if name == "silver_futures"
                else "Alpha Vantage Silver"
            ),
            "icon": (
                "🪙" if name == "spot_silver"
                else "📈" if name == "silver_futures"
                else "🏦"
            ),
            "priorityScore": compute_priority(s, remaining_budget),
            "qualityScore": round(
                s.get("freshness", 0.5)
                * s.get("reliability", 0.5)
                * 100,
                2,
            ),
            "freshnessScore": round(s.get("freshness", 0.5) * 100, 2),
            "reliabilityScore": round(s.get("reliability", 0.5) * 100, 2),
            "isSelected": name == selected_source,
            "status": "active",
            "last_updated": int(s.get("last_updated", time.time())),
        })

    return ranked


# -------------------------------------------------
# API Endpoint
# -------------------------------------------------
@app.get("/silver/predict")
def predict_silver():
    logger = AILogger(name="BackendRunner")

    try:
        env = SilverMarketEnvironment()
        sources = env.get_all_sources()

        if not sources:
            raise RuntimeError("No sources available")

        selected_source, decision_score = AGENT.select_best_source(env)
        source = sources[selected_source]

        current_price = safe_float(source.get("value"))
        if current_price <= 0:
            raise RuntimeError("Invalid price")

        now = time.time()
        last_price = LAST_RUN["price"]
        last_ts = LAST_RUN["timestamp"]

        volatility = compute_volatility(current_price, last_price)
        freshness = safe_float(source.get("freshness"), 0.8)

        can_skip = (
            last_price is not None
            and last_ts is not None
            and freshness > 0.9
            and (now - last_ts) < MAX_SKIP_SECONDS
        )

        ranked_sources = build_ranked_sources(
            sources,
            selected_source,
            AGENT.remaining_budget,
        )

        if can_skip:
            return {
                "current_price": round(last_price, 4),
                "predicted_price": round(LAST_RUN["prediction"], 4),
                "confidence": 0.0,
                "trend": "stable",
                "selected_source": selected_source,
                "decision_score": round(decision_score, 4),
                "skipped": True,
                "resources_saved": 1,
                "volatility": volatility,
                "freshness": round(freshness, 4),
                "timestamp": int(now),
                "sources": ranked_sources,
            }

        PREDICTOR.add_price(current_price)
        prediction = PREDICTOR.predict_next()

        confidence = safe_float(prediction.get("confidence"), 0.003)
        trend = prediction.get("trend", "stable")

        offset = 0.002 + confidence * 0.004
        predicted_price = round(
            current_price * (1 + offset if trend == "up" else 1 - offset),
            4,
        )

        reward = env.calculate_reward(selected_source)
        AGENT.update_learning(selected_source, reward)
        AGENT.deduct_cost(source.get("cost", 0.0))

        LAST_RUN.update({
            "price": current_price,
            "prediction": predicted_price,
            "timestamp": now,
        })

        return {
            "current_price": round(current_price, 4),
            "predicted_price": predicted_price,
            "confidence": round(confidence, 4),
            "trend": trend,
            "selected_source": selected_source,
            "decision_score": round(decision_score, 4),
            "reward": round(reward, 4),
            "remaining_budget": round(AGENT.remaining_budget, 4),
            "volatility": volatility,
            "freshness": round(freshness, 4),
            "timestamp": int(now),
            "sources": ranked_sources,
        }

    except Exception as e:
        logger.logger.exception("BACKEND FAILURE")
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get("/silver/history")
def silver_history():
    """
    Returns real intraday silver prices (last ~2 hours)
    Used ONLY for visualization.
    """
    try:
        import yfinance as yf
        ticker = yf.Ticker("SI=F")

        hist = ticker.history(period="1d", interval="5m")
        hist = hist.tail(24)  # last ~2 hours

        return [
            {
                "timestamp": int(ts.timestamp() * 1000),
                "price": round(float(row["Close"]), 4)
            }
            for ts, row in hist.iterrows()
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

