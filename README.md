# TradeMind AI

## AI-Based Trading Performance & Behavioral Analysis

TradeMind AI is an intelligent trading analysis system designed to analyze historical trading behavior, identify risky behavioral patterns, calculate trader risk, and provide explainable decision support.

The goal is not to automate trading decisions, but to help traders understand and improve their own trading behavior.

## Current Pipeline

Historical Executions
        ↓
Position Validation
        ↓
Trade Reconstruction
        ↓
Feature Engineering
        ↓
Behavior Detection
        ↓
Risk Scoring
        ↓
Trader Profiles
        ↓
ML Validation
        ↓
FastAPI Backend
        ↓
React Dashboard

## Current Progress

- 174,327 raw executions processed
- 3,093 reconstructed / engineered trades
- 38 engineered features
- 2,488 behavioral flags
- 5 behavioral categories
- 32 trader profiles
- Risk classification
- Discipline scoring
- ML leakage audit
- Temporal validation
- Feature ablation study
- FastAPI backend
- React dashboard

## Behavioral Intelligence

TradeMind currently analyzes patterns such as:

- Revenge Trading
- Overtrading
- Oversizing
- Rapid Re-entry
- Loss Streaks

## Machine Learning

The project uses a leakage-aware ML evaluation process.

The initial random-split model produced an unrealistically perfect result, so a leakage audit and chronological temporal validation were performed.

Current temporal validation:

- Accuracy: 61.07%
- ROC-AUC: 0.5808
- PR-AUC: 0.8543

Feature ablation showed that previous-trade outcome information provides useful predictive signal.

## Technology Stack

### Backend
- Python
- Pandas
- NumPy
- Scikit-learn
- FastAPI

### Frontend
- React
- Axios
- Recharts
- Lucide React

### Data & ML
- Historical trading data
- Feature engineering
- Behavioral analysis
- Risk scoring
- Temporal ML validation

## Project Structure

TradeMind-AI/
│
├── backend/
│   ├── app/
│   └── ...
│
├── data/
│
├── frontend/
│
├── models/
│
├── tests/
│
├── docs/
│
├── .gitignore
└── README.md

## Project Status

Current stage: First Review Prototype

The current system focuses on establishing a reliable data, behavioral intelligence, ML validation, backend, and dashboard foundation.

## Future Scope

- Improved ML reliability
- Probability calibration
- AI-generated trading behavior reports
- Personalized trader coaching
- Alerts and behavioral monitoring
- Broker / TradingView integrations
- Mobile application
- AI trading journal assistant

## Disclaimer

TradeMind AI is an analytical and educational project. It is not intended to provide financial advice or guarantee trading outcomes.