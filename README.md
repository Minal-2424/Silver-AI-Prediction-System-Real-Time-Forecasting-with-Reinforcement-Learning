# Silver AI Prediction System

AI-powered real-time silver price prediction using multi-source data collection and reinforcement learning.

## Quick Start

### Backend Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env  # Add your ALPHA_KEY and GNEWS_KEY

# Run server
uvicorn main:app --reload
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Access dashboard at: http://localhost:8080

## Core Features

- **Multi-source Data Collection**: Spot silver, futures, and Alpha Vantage
- **Reinforcement Learning**: Bandit algorithm for optimal source selection
- **Real-time Prediction**: ARIMA-based price forecasting
- **Live Dashboard**: Interactive frontend with price history and predictions

## API Endpoints

- `GET /silver/predict` - Get current price and prediction
- `GET /silver/history` - Get recent price history (last 2 hours)

## Tech Stack

**Backend**: FastAPI, Python, ARIMA, Multi-armed Bandit
**Frontend**: React/Vite, Tailwind CSS
**Data Sources**: Yahoo Finance, Alpha Vantage, GNews

## Team

Tetra Logic - Echelon 2.0