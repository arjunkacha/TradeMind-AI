from fastapi import (
    FastAPI,
    HTTPException,
    Query,
    UploadFile,
    File,
)
from app.integrations.tradingview.parser import (
    parse_tradingview_csv,
    save_trades,
)

from fastapi.middleware.cors import CORSMiddleware

from app.routers.simulator import router as simulator_router

import pandas as pd
import numpy as np
import json
from pathlib import Path
import math


# ============================================================
# JSON-SAFE HELPERS
# ============================================================

def clean_for_json(value):
    """
    Convert Pandas / NumPy values into JSON-safe values.

    NaN, +inf and -inf become None.
    NumPy scalar values are converted to native Python values.
    """

    if value is None:
        return None

    # NumPy scalar -> native Python scalar
    if isinstance(value, np.generic):
        value = value.item()

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value

    if isinstance(value, dict):
        return {
            key: clean_for_json(val)
            for key, val in value.items()
        }

    if isinstance(value, list):
        return [
            clean_for_json(item)
            for item in value
        ]

    return value


# ============================================================
# TRADEMIND AI - FASTAPI BACKEND
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"


# ============================================================
# FILE PATHS
# ============================================================

FEATURE_FILE = DATA_DIR / "trade_features.csv"
BEHAVIOR_FILE = DATA_DIR / "behavior_flags.csv"
RISK_FILE = DATA_DIR / "risk_scores.csv"
PROFILE_FILE = DATA_DIR / "trader_profiles.csv"
DECISION_FILE = DATA_DIR / "trade_decisions.csv"

ML_METRICS_FILE = MODELS_DIR / "trusted_training_metrics.json"


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="TradeMind AI",
    description=(
        "AI-based trading behavior analysis and "
        "risk intelligence API."
    ),
    version="1.0.0",
)

# Register the demo trading simulator routes.
app.include_router(simulator_router)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# DATA CACHE
# ============================================================

features_df = None
behaviors_df = None
risks_df = None
profiles_df = None
decisions_df = None
ml_metrics = None


# ============================================================
# JSON-SAFE DATAFRAME HELPERS
# ============================================================

def clean_dataframe(df):
    """
    Convert Pandas NaN and infinite values into JSON-safe None.
    """

    if df is None:
        return df

    cleaned = df.replace(
        [np.inf, -np.inf],
        np.nan
    )

    cleaned = cleaned.astype(object).where(
        pd.notna(cleaned),
        None
    )

    return cleaned


def clean_records(df):
    """
    Convert a DataFrame into JSON-safe records.
    """

    if df is None or df.empty:
        return []

    records = clean_dataframe(df).to_dict(
        orient="records"
    )

    return clean_for_json(records)


def safe_float(value, default=0.0):
    """
    Convert a value to a JSON-safe float.
    """

    try:
        value = float(value)

        if not np.isfinite(value):
            return default

        return value

    except (TypeError, ValueError):
        return default


def clean_dict(data):
    """
    Recursively convert NaN/infinite values into None.
    """

    if isinstance(data, dict):
        return {
            key: clean_dict(value)
            for key, value in data.items()
        }

    if isinstance(data, list):
        return [
            clean_dict(value)
            for value in data
        ]

    if isinstance(data, np.generic):
        data = data.item()

    if isinstance(data, float):
        if not np.isfinite(data):
            return None

    return data


# ============================================================
# LOAD DATA
# ============================================================

def load_data():

    global features_df
    global behaviors_df
    global risks_df
    global profiles_df
    global decisions_df
    global ml_metrics

    print("Loading TradeMind datasets...")

    # --------------------------------------------------------
    # FEATURES
    # --------------------------------------------------------

    features_df = pd.read_csv(
        FEATURE_FILE
    )

    # --------------------------------------------------------
    # BEHAVIORS
    # --------------------------------------------------------

    behaviors_df = pd.read_csv(
        BEHAVIOR_FILE
    )

    # --------------------------------------------------------
    # RISKS
    # --------------------------------------------------------

    risks_df = pd.read_csv(
        RISK_FILE
    )

    # --------------------------------------------------------
    # PROFILES
    # --------------------------------------------------------

    profiles_df = pd.read_csv(
        PROFILE_FILE
    )

    # --------------------------------------------------------
    # DECISIONS
    # --------------------------------------------------------

    decisions_df = pd.read_csv(
        DECISION_FILE
    )

    # --------------------------------------------------------
    # ML METRICS
    # --------------------------------------------------------

    with open(
        ML_METRICS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        ml_metrics = json.load(file)

    print(
        f"Features loaded:  {len(features_df):,}"
    )

    print(
        f"Behaviors loaded: {len(behaviors_df):,}"
    )

    print(
        f"Risks loaded:     {len(risks_df):,}"
    )

    print(
        f"Profiles loaded:  {len(profiles_df):,}"
    )

    print(
        f"Decisions loaded: {len(decisions_df):,}"
    )

    print(
        "ML metrics loaded."
    )


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
def startup_event():
    # Default application mode uses simulator trades and auto-journaling.
    # Historical CSV-backed datasets are loaded lazily only if a legacy
    # historical endpoint is explicitly requested. This keeps the default
    # startup independent of the old static project dataset.
    print("TradeMind AI started in demo-simulator-first mode.")


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
def health():

    return {
        "status": "healthy",
        "service": "TradeMind AI",
        "version": "1.0.0",
    }


# ============================================================
# DASHBOARD OVERVIEW
# ============================================================

@app.get("/api/dashboard")
def dashboard():

    if decisions_df is None:
        load_data()

    total_trades = len(
        decisions_df
    )

    decision_distribution = (
        decisions_df[
            "decision"
        ]
        .value_counts()
        .to_dict()
    )

    risk_distribution = (
        decisions_df[
            "risk_level"
        ]
        .value_counts()
        .to_dict()
    )

    average_risk = safe_float(
        decisions_df[
            "risk_score"
        ].mean()
    )

    average_discipline = safe_float(
        decisions_df[
            "discipline_score"
        ].mean()
    )

    average_ml_win_probability = safe_float(
        decisions_df[
            "ml_win_probability"
        ].mean()
    )

    return clean_dict({

        "total_trades":
            total_trades,

        "average_risk_score":
            round(
                average_risk,
                2
            ),

        "average_discipline_score":
            round(
                average_discipline,
                2
            ),

        "average_ml_win_probability":
            round(
                average_ml_win_probability,
                4
            ),

        "decision_distribution":
            decision_distribution,

        "risk_distribution":
            risk_distribution,

    })


# ============================================================
# TRADES
# ============================================================

@app.get("/api/trades")
def get_trades(

    limit: int = Query(
        50,
        ge=1,
        le=500
    ),

    decision: str | None = None,

    risk_level: str | None = None,

):

    if decisions_df is None:
        load_data()

    df = decisions_df.copy()

    # --------------------------------------------------------
    # FILTER BY DECISION
    # --------------------------------------------------------

    if decision:

        df = df[
            df["decision"]
            .astype(str)
            .str.upper()
            == decision.upper()
        ]

    # --------------------------------------------------------
    # FILTER BY RISK
    # --------------------------------------------------------

    if risk_level:

        df = df[
            df["risk_level"]
            .astype(str)
            .str.upper()
            == risk_level.upper()
        ]

    # --------------------------------------------------------
    # LIMIT
    # --------------------------------------------------------

    df = df.head(
        limit
    )

    return {
        "count":
            len(df),

        "trades":
            clean_records(df)
    }


# ============================================================
# SINGLE TRADE
# ============================================================

@app.get("/api/trades/{trade_id}")
def get_trade(trade_id: str):

    if decisions_df is None:
        load_data()

    matches = decisions_df[
        decisions_df[
            "trade_id"
        ].astype(str)
        == str(trade_id)
    ]

    if matches.empty:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Trade {trade_id} "
                "not found."
            )
        )

    trade = matches.iloc[0].to_dict()

    trade = clean_for_json(
        trade
    )

    return {
        "trade":
            trade
    }


# ============================================================
# TRADERS
# ============================================================

@app.get("/api/traders")
def get_traders():

    if profiles_df is None:
        load_data()

    return {

        "count":
            len(profiles_df),

        "traders":
            clean_records(
                profiles_df
            ),

    }


# ============================================================
# SINGLE TRADER
# ============================================================

@app.get("/api/traders/{account}")
def get_trader(
    account: str
):

    if profiles_df is None:
        load_data()

    matches = profiles_df[
        profiles_df[
            "account"
        ].astype(str)
        == str(account)
    ]

    if matches.empty:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Trader {account} "
                "not found."
            )
        )

    trader = clean_records(
        matches.iloc[[0]]
    )[0]

    # --------------------------------------------------------
    # TRADER DECISIONS
    # --------------------------------------------------------

    trader_decisions = decisions_df[
        decisions_df[
            "account"
        ].astype(str)
        == str(account)
    ]

    # --------------------------------------------------------
    # DECISION DISTRIBUTION
    # --------------------------------------------------------

    decision_distribution = (
        trader_decisions[
            "decision"
        ]
        .value_counts()
        .to_dict()
    )

    # --------------------------------------------------------
    # RISK DISTRIBUTION
    # --------------------------------------------------------

    risk_distribution = (
        trader_decisions[
            "risk_level"
        ]
        .value_counts()
        .to_dict()
    )

    # --------------------------------------------------------
    # BEHAVIOR DISTRIBUTION
    # --------------------------------------------------------

    trader_behaviors = behaviors_df[
        behaviors_df[
            "account"
        ].astype(str)
        == str(account)
    ]

    behavior_distribution = (
        trader_behaviors[
            "behavior"
        ]
        .value_counts()
        .to_dict()
        if not trader_behaviors.empty
        else {}
    )

    return clean_dict({

        "profile":
            trader,

        "decision_distribution":
            decision_distribution,

        "risk_distribution":
            risk_distribution,

        "behavior_distribution":
            behavior_distribution,

        "behavior_event_count":
            len(trader_behaviors),

        "trade_count":
            len(trader_decisions),

    })


# ============================================================
# BEHAVIOR SUMMARY
# ============================================================

@app.get("/api/behaviors")
def get_behaviors():

    if behaviors_df is None:
        load_data()

    if behaviors_df.empty:

        return {
            "total_flags": 0,
            "behaviors": {},
            "severity_distribution": {},
            "top_events": [],
        }

    # --------------------------------------------------------
    # BEHAVIOR COUNTS
    # --------------------------------------------------------

    behavior_counts = (
        behaviors_df[
            "behavior"
        ]
        .value_counts()
        .to_dict()
    )

    # --------------------------------------------------------
    # SEVERITY COUNTS
    # --------------------------------------------------------

    severity_distribution = (
        behaviors_df[
            "severity"
        ]
        .value_counts()
        .to_dict()
    )

    # --------------------------------------------------------
    # AVERAGE SCORE
    # --------------------------------------------------------

    average_score = safe_float(
        behaviors_df[
            "score"
        ].mean()
    )

    # --------------------------------------------------------
    # HIGH / CRITICAL COUNT
    # --------------------------------------------------------

    high_risk_events = int(
        behaviors_df[
            "severity"
        ]
        .astype(str)
        .str.upper()
        .isin(
            [
                "HIGH",
                "CRITICAL"
            ]
        )
        .sum()
    )

    # --------------------------------------------------------
    # TOP EVENTS
    # --------------------------------------------------------

    top_events = (
        behaviors_df
        .sort_values(
            "score",
            ascending=False
        )
        .head(15)
    )

    return clean_dict({

        "total_flags":
            len(behaviors_df),

        "behaviors":
            behavior_counts,

        "severity_distribution":
            severity_distribution,

        "average_behavior_score":
            round(
                average_score,
                2
            ),

        "high_risk_events":
            high_risk_events,

        "top_events":
            clean_records(
                top_events
            ),

    })


# ============================================================
# BEHAVIOR EVENTS
# ============================================================

@app.get("/api/behaviors/events")
def get_behavior_events(

    limit: int = Query(
        100,
        ge=1,
        le=1000
    ),

    behavior: str | None = None,

    severity: str | None = None,

):

    if behaviors_df is None:
        load_data()

    df = behaviors_df.copy()

    # --------------------------------------------------------
    # FILTER BEHAVIOR
    # --------------------------------------------------------

    if behavior:

        df = df[
            df["behavior"]
            .astype(str)
            .str.upper()
            == behavior.upper()
        ]

    # --------------------------------------------------------
    # FILTER SEVERITY
    # --------------------------------------------------------

    if severity:

        df = df[
            df["severity"]
            .astype(str)
            .str.upper()
            == severity.upper()
        ]

    # --------------------------------------------------------
    # SORT BY SCORE
    # --------------------------------------------------------

    if "score" in df.columns:

        df["score"] = pd.to_numeric(
            df["score"],
            errors="coerce"
        )

        df = df.sort_values(
            "score",
            ascending=False,
            na_position="last"
        )

    # --------------------------------------------------------
    # LIMIT
    # --------------------------------------------------------

    df = df.head(
        limit
    )

    return clean_dict({

        "count":
            len(df),

        "events":
            clean_records(df),

    })


# ============================================================
# SINGLE TRADE BEHAVIOR
# ============================================================

@app.get("/api/behaviors/{trade_id}")
def get_trade_behaviors(
    trade_id: str
):

    if behaviors_df is None:
        load_data()

    matches = behaviors_df[
        behaviors_df[
            "trade_id"
        ].astype(str)
        == str(trade_id)
    ]

    if matches.empty:

        return clean_dict({

            "trade_id":
                trade_id,

            "behavior_count":
                0,

            "behaviors":
                [],

        })

    behavior_records = clean_records(
        matches
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    behavior_counts = (
        matches[
            "behavior"
        ]
        .value_counts()
        .to_dict()
    )

    severity_counts = (
        matches[
            "severity"
        ]
        .value_counts()
        .to_dict()
    )

    average_score = safe_float(
        matches[
            "score"
        ].mean()
    )

    return clean_dict({

        "trade_id":
            trade_id,

        "behavior_count":
            len(matches),

        "behavior_distribution":
            behavior_counts,

        "severity_distribution":
            severity_counts,

        "average_score":
            round(
                average_score,
                2
            ),

        "behaviors":
            behavior_records,

    })


# ============================================================
# RISK SUMMARY
# ============================================================

@app.get("/api/risk-summary")
def get_risk_summary():

    if decisions_df is None:
        load_data()

    risk_counts = (
        decisions_df[
            "risk_level"
        ]
        .value_counts()
        .to_dict()
    )

    average_risk = safe_float(
        decisions_df[
            "risk_score"
        ].mean()
    )

    return clean_dict({

        "average_risk_score":
            round(
                average_risk,
                2
            ),

        "risk_distribution":
            risk_counts,

    })


# ============================================================
# ML METRICS
# ============================================================

@app.get("/api/ml-metrics")
def get_ml_metrics():

    if ml_metrics is None:
        load_data()

    return clean_dict({

        "model":
            "Trusted Logistic Regression",

        "validation":
            "Temporal 80/20 split",

        "features":
            19,

        "metrics":
            ml_metrics,

    })


# ============================================================
# RECENT HIGH-RISK TRADES
# ============================================================

@app.get("/api/high-risk-trades")
def get_high_risk_trades(

    limit: int = Query(
        10,
        ge=1,
        le=100
    )

):

    if decisions_df is None:
        load_data()

    high_risk = decisions_df[
        decisions_df[
            "risk_level"
        ]
        .astype(str)
        .str.upper()
        .isin(
            [
                "HIGH",
                "CRITICAL"
            ]
        )
    ]

    high_risk = (
        high_risk
        .sort_values(
            "risk_score",
            ascending=False
        )
        .head(limit)
    )

    return {

        "count":
            len(high_risk),

        "trades":
            clean_records(
                high_risk
            ),

    }


# your existing code above
# your existing API endpoints above

# ============================================================
# TRADINGVIEW PAPER TRADING
# ============================================================

TRADINGVIEW_TRADES_FILE = DATA_DIR / "tradingview_trades.csv"
TRADINGVIEW_ANALYSIS_DIR = DATA_DIR / "tradingview_analysis"


def load_tradingview_analysis():
    """Load the latest TradingView-specific TradeMind analysis."""

    required = {
        "trades": TRADINGVIEW_TRADES_FILE,
        "features": TRADINGVIEW_ANALYSIS_DIR / "features.csv",
        "behaviors": TRADINGVIEW_ANALYSIS_DIR / "behaviors.csv",
        "risks": TRADINGVIEW_ANALYSIS_DIR / "risks.csv",
        "profiles": TRADINGVIEW_ANALYSIS_DIR / "profiles.csv",
        "decisions": TRADINGVIEW_ANALYSIS_DIR / "decisions.csv",
    }

    missing = [str(path) for path in required.values() if not path.exists()]
    if missing:
        raise HTTPException(
            status_code=404,
            detail=(
                "TradingView analysis is not available yet. "
                "Import a TradingView Trade History CSV first. "
                f"Missing: {', '.join(missing)}"
            ),
        )

    try:
        return {
            name: pd.read_csv(path)
            for name, path in required.items()
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not load TradingView analysis: {exc}",
        )


def tradingview_decisions():
    return load_tradingview_analysis()["decisions"]


def tradingview_behaviors():
    return load_tradingview_analysis()["behaviors"]


def tradingview_profiles():
    return load_tradingview_analysis()["profiles"]


@app.post("/api/tradingview/import")
async def import_tradingview_csv(
    file: UploadFile = File(...),
    account: str = Query("TradingView-Paper"),
):
    """Import TradingView Paper Trading CSV and run TradeMind AI."""

    filename = file.filename or ""

    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a CSV file exported from TradingView.",
        )

    try:
        file_bytes = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not read uploaded file: {exc}",
        )

    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail="Uploaded CSV file is empty.",
        )

    try:
        trades_df = parse_tradingview_csv(
            file_bytes,
            account=account,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"TradingView import failed: {exc}",
        )

    output_path = save_trades(trades_df)

    try:
        from app.services.tradingview_pipeline import run_tradingview_analysis
        analysis = run_tradingview_analysis()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "TradingView import succeeded, but AI analysis failed: "
                f"{exc}"
            ),
        )

    return clean_dict({
        "status": "success",
        "source": "tradingview_paper",
        "filename": filename,
        "account": account,
        "completed_trades": len(trades_df),
        "analysis": {
            "trades": len(analysis["trades"]),
            "features": len(analysis["features"]),
            "behavior_flags": len(analysis["behaviors"]),
            "risk_records": len(analysis["risks"]),
            "trader_profiles": len(analysis["profiles"]),
            "decisions": len(analysis["decisions"]),
        },
        "output_file": str(output_path),
        "analysis_directory": str(TRADINGVIEW_ANALYSIS_DIR),
    })


@app.get("/api/tradingview/status")
def tradingview_status():
    """Return whether TradingView data has been imported and analyzed."""

    files = {
        "trades": TRADINGVIEW_TRADES_FILE,
        "features": TRADINGVIEW_ANALYSIS_DIR / "features.csv",
        "behaviors": TRADINGVIEW_ANALYSIS_DIR / "behaviors.csv",
        "risks": TRADINGVIEW_ANALYSIS_DIR / "risks.csv",
        "profiles": TRADINGVIEW_ANALYSIS_DIR / "profiles.csv",
        "decisions": TRADINGVIEW_ANALYSIS_DIR / "decisions.csv",
    }

    available = all(path.exists() for path in files.values())
    trade_count = 0

    if TRADINGVIEW_TRADES_FILE.exists():
        try:
            trade_count = len(pd.read_csv(TRADINGVIEW_TRADES_FILE))
        except Exception:
            trade_count = 0

    return {
        "connected": available,
        "source": "tradingview_paper",
        "trade_count": trade_count,
        "analysis_ready": available,
    }


@app.get("/api/tradingview/dashboard")
def tradingview_dashboard():
    """Dashboard overview for TradingView Paper Trading."""

    data = load_tradingview_analysis()
    decisions = data["decisions"]

    if decisions.empty:
        return {
            "total_trades": 0,
            "average_risk_score": 0,
            "average_discipline_score": 0,
            "average_ml_win_probability": 0,
            "decision_distribution": {},
            "risk_distribution": {},
        }

    decision_distribution = (
        decisions["decision"].value_counts().to_dict()
        if "decision" in decisions.columns else {}
    )
    risk_distribution = (
        decisions["risk_level"].value_counts().to_dict()
        if "risk_level" in decisions.columns else {}
    )

    average_risk = safe_float(
        decisions["risk_score"].mean()
        if "risk_score" in decisions.columns else 0
    )
    average_discipline = safe_float(
        decisions["discipline_score"].mean()
        if "discipline_score" in decisions.columns else 0
    )
    average_ml = safe_float(
        decisions["ml_win_probability"].mean()
        if "ml_win_probability" in decisions.columns else 0
    )

    return clean_dict({
        "total_trades": len(decisions),
        "average_risk_score": round(average_risk, 2),
        "average_discipline_score": round(average_discipline, 2),
        "average_ml_win_probability": round(average_ml, 4),
        "decision_distribution": decision_distribution,
        "risk_distribution": risk_distribution,
    })


@app.get("/api/tradingview/trades")
def tradingview_trades(
    limit: int = Query(200, ge=1, le=500),
    decision: str | None = None,
    risk_level: str | None = None,
):
    """Return TradingView trades with TradeMind analysis."""

    df = tradingview_decisions().copy()

    if decision:
        df = df[
            df["decision"].astype(str).str.upper() == decision.upper()
        ]

    if risk_level:
        df = df[
            df["risk_level"].astype(str).str.upper() == risk_level.upper()
        ]

    df = df.head(limit)

    return {
        "source": "tradingview_paper",
        "count": len(df),
        "trades": clean_records(df),
    }


@app.get("/api/tradingview/trades/{trade_id}")
def tradingview_trade(trade_id: str):
    """
    Return one complete TradingView trade.

    The feature record is the authoritative source for execution fields
    because the TradingView parser converts the original entry/exit rows
    into one completed-trade record keyed by trade_id.
    """

    data = load_tradingview_analysis()

    decisions = data["decisions"]
    behaviors = data["behaviors"]
    risks = data["risks"]
    features = data["features"]

    # ------------------------------------------------------------
    # FIND AI DECISION
    # ------------------------------------------------------------

    matches = decisions[
        decisions["trade_id"].astype(str) == str(trade_id)
    ]

    if matches.empty:
        raise HTTPException(
            status_code=404,
            detail=f"TradingView trade {trade_id} not found.",
        )

    ai_trade = clean_records(matches.iloc[[0]])[0]

    # ------------------------------------------------------------
    # FIND FEATURE / EXECUTION RECORD
    # ------------------------------------------------------------

    feature_matches = (
        features[
            features["trade_id"].astype(str) == str(trade_id)
        ]
        if "trade_id" in features.columns
        else pd.DataFrame()
    )

    feature_trade = (
        clean_records(feature_matches.iloc[[0]])[0]
        if not feature_matches.empty
        else {}
    )

    # ------------------------------------------------------------
    # FIND BEHAVIOR RECORDS
    # ------------------------------------------------------------

    trade_behaviors = (
        behaviors[
            behaviors["trade_id"].astype(str) == str(trade_id)
        ]
        if "trade_id" in behaviors.columns
        else pd.DataFrame()
    )

    # ------------------------------------------------------------
    # FIND RISK RECORD
    # ------------------------------------------------------------

    trade_risk = (
        risks[
            risks["trade_id"].astype(str) == str(trade_id)
        ]
        if "trade_id" in risks.columns
        else pd.DataFrame()
    )

    # ------------------------------------------------------------
    # BUILD COMPLETE TRADE
    # ------------------------------------------------------------

    # Feature engineering already contains the normalized execution
    # fields: entry/exit, quantity, P&L, holding time, etc.
    complete_trade = dict(feature_trade)

    # AI decision/risk/ML fields are layered on top.
    complete_trade.update(ai_trade)

    # ------------------------------------------------------------
    # CONSISTENCY CHECKS
    # ------------------------------------------------------------

    # primary_risk is an account/profile-level value in the legacy
    # decision file. For an individual journal trade, the detected
    # behavior events are the authoritative trade-level risk signal.
    # Select the most severe detected behavior; if none exist, report
    # that no behavioral risk was detected for this trade.
    if not trade_behaviors.empty and {"behavior", "severity"}.issubset(
        trade_behaviors.columns
    ):
        severity_rank = {
            "CRITICAL": 4,
            "HIGH": 3,
            "MEDIUM": 2,
            "LOW": 1,
        }

        behavior_rows = trade_behaviors.copy()
        behavior_rows["_severity_rank"] = (
            behavior_rows["severity"]
            .astype(str)
            .str.upper()
            .map(severity_rank)
            .fillna(0)
        )

        if "score" in behavior_rows.columns:
            behavior_rows["_score"] = pd.to_numeric(
                behavior_rows["score"], errors="coerce"
            ).fillna(0)
        else:
            behavior_rows["_score"] = 0

        behavior_rows = behavior_rows.sort_values(
            ["_severity_rank", "_score"],
            ascending=False,
        )

        complete_trade["primary_risk"] = str(
            behavior_rows.iloc[0]["behavior"]
        )
    else:
        complete_trade["primary_risk"] = "None detected"

    complete_trade["behavior_count"] = len(trade_behaviors)
    complete_trade["behaviors"] = (
        ", ".join(
            trade_behaviors["behavior"].astype(str).tolist()
        )
        if "behavior" in trade_behaviors.columns
        else None
    )

    # A profile discipline score of exactly 0 is currently not enough
    # evidence to call the individual trade "very low discipline".
    # Preserve the stored value, but mark it so the UI/API can explain
    # its provenance instead of silently presenting it as trade-level.
    stored_discipline = complete_trade.get("discipline_score")
    complete_trade["discipline_score_source"] = "trader_profile"
    complete_trade["discipline_score_scope"] = "account"
    complete_trade["discipline_score_valid"] = (
        stored_discipline is not None
        and safe_float(stored_discipline, default=0.0) > 0
    )

    # Do not attach the legacy "very low discipline" sentence to a
    # trade when the stored profile score is the suspicious zero value.
    if (
        safe_float(stored_discipline, default=0.0) == 0.0
        and complete_trade.get("recommendation")
    ):
        complete_trade["recommendation"] = str(
            complete_trade["recommendation"]
        ).replace(
            " Trader discipline is currently very low.",
            "",
        )

    # ------------------------------------------------------------
    # NORMALIZE FRONTEND-FRIENDLY EXECUTION FIELDS
    # ------------------------------------------------------------

    field_aliases = {
        "entry_price": ["entry_price"],
        "exit_price": ["exit_price"],
        "quantity": ["quantity"],
        "pnl": ["net_pnl", "gross_pnl"],
        "net_pnl": ["net_pnl"],
        "gross_pnl": ["gross_pnl"],
        "commission": ["fees", "commission"],
        "timestamp": ["entry_time", "timestamp"],
        "holding_minutes": ["holding_minutes"],
    }

    for target, candidates in field_aliases.items():
        if complete_trade.get(target) is None:
            for candidate in candidates:
                if complete_trade.get(candidate) is not None:
                    complete_trade[target] = complete_trade[candidate]
                    break

    # Ensure these core values come from the feature record if the
    # decision record does not contain them.
    for field in [
        "symbol",
        "direction",
        "entry_time",
        "exit_time",
        "entry_price",
        "exit_price",
        "quantity",
        "gross_pnl",
        "fees",
        "net_pnl",
        "holding_minutes",
    ]:
        if feature_trade.get(field) is not None:
            complete_trade[field] = feature_trade[field]

    complete_trade["trade_id"] = trade_id
    complete_trade["account"] = (
        complete_trade.get("account")
        or "TradingView-Paper"
    )

    # ------------------------------------------------------------
    # RETURN
    # ------------------------------------------------------------

    return clean_dict({
        "source": "tradingview_paper",
        "trade": complete_trade,
        "behaviors": clean_records(trade_behaviors),
        "risk": clean_records(trade_risk),
        "features": clean_records(feature_matches),
    })


# ============================================================
# TRADINGVIEW ML PREDICTIONS
# ============================================================

@app.get("/api/tradingview/ml-predictions")
def tradingview_ml_predictions(
    limit: int = Query(100, ge=1, le=500),
):
    """
    Return ML predictions generated by the TradingView TradeMind
    analysis pipeline.
    """

    df = tradingview_decisions().copy()

    if df.empty:
        return clean_dict({
            "source": "tradingview_paper",
            "count": 0,
            "predictions": [],
        })

    prediction_columns = [
        column
        for column in [
            "trade_id",
            "account",
            "symbol",
            "direction",
            "entry_time",
            "exit_time",
            "ml_win_probability",
            "ml_loss_probability",
            "ml_signal",
            "risk_score",
            "risk_level",
            "decision",
            "recommendation",
        ]
        if column in df.columns
    ]

    predictions = df[prediction_columns].copy()

    if "ml_win_probability" in predictions.columns:
        predictions["ml_win_probability"] = pd.to_numeric(
            predictions["ml_win_probability"],
            errors="coerce",
        )

        predictions = predictions.sort_values(
            "ml_win_probability",
            ascending=False,
            na_position="last",
        )

    predictions = predictions.head(limit)

    return clean_dict({
        "source": "tradingview_paper",
        "count": len(predictions),
        "predictions": clean_records(predictions),
    })


@app.get("/api/tradingview/behaviors")
def tradingview_behavior_summary():
    """Behavioral AI summary for TradingView trades."""

    df = tradingview_behaviors()

    if df.empty:
        return {
            "source": "tradingview_paper",
            "total_flags": 0,
            "behaviors": {},
            "severity_distribution": {},
            "average_behavior_score": 0,
            "high_risk_events": 0,
            "top_events": [],
        }

    behavior_counts = (
        df["behavior"].value_counts().to_dict()
        if "behavior" in df.columns else {}
    )
    severity_distribution = (
        df["severity"].value_counts().to_dict()
        if "severity" in df.columns else {}
    )
    average_score = safe_float(
        df["score"].mean() if "score" in df.columns else 0
    )
    high_risk_events = int(
        df["severity"].astype(str).str.upper().isin(
            ["HIGH", "CRITICAL"]
        ).sum()
        if "severity" in df.columns else 0
    )

    top_events = (
        df.sort_values("score", ascending=False).head(15)
        if "score" in df.columns else df.head(15)
    )

    return clean_dict({
        "source": "tradingview_paper",
        "total_flags": len(df),
        "behaviors": behavior_counts,
        "severity_distribution": severity_distribution,
        "average_behavior_score": round(average_score, 2),
        "high_risk_events": high_risk_events,
        "top_events": clean_records(top_events),
    })


@app.get("/api/tradingview/behaviors/events")
def tradingview_behavior_events(
    limit: int = Query(100, ge=1, le=1000),
    behavior: str | None = None,
    severity: str | None = None,
):
    """Behavior events generated from TradingView trades."""

    df = tradingview_behaviors().copy()

    if behavior:
        df = df[
            df["behavior"].astype(str).str.upper() == behavior.upper()
        ]

    if severity:
        df = df[
            df["severity"].astype(str).str.upper() == severity.upper()
        ]

    if "score" in df.columns:
        df["score"] = pd.to_numeric(df["score"], errors="coerce")
        df = df.sort_values("score", ascending=False, na_position="last")

    df = df.head(limit)

    return clean_dict({
        "source": "tradingview_paper",
        "count": len(df),
        "events": clean_records(df),
    })


@app.get("/api/tradingview/behaviors/{trade_id}")
def tradingview_trade_behaviors(trade_id: str):
    """Behavior analysis for one TradingView trade."""

    df = tradingview_behaviors()
    matches = df[
        df["trade_id"].astype(str) == str(trade_id)
    ]

    if matches.empty:
        return {
            "source": "tradingview_paper",
            "trade_id": trade_id,
            "behavior_count": 0,
            "behaviors": [],
        }

    behavior_distribution = matches["behavior"].value_counts().to_dict()
    severity_distribution = matches["severity"].value_counts().to_dict()
    average_score = safe_float(matches["score"].mean())

    return clean_dict({
        "source": "tradingview_paper",
        "trade_id": trade_id,
        "behavior_count": len(matches),
        "behavior_distribution": behavior_distribution,
        "severity_distribution": severity_distribution,
        "average_score": round(average_score, 2),
        "behaviors": clean_records(matches),
    })


@app.get("/api/tradingview/risk-summary")
def tradingview_risk_summary():
    """Risk Intelligence summary for TradingView trades."""

    decisions = tradingview_decisions()

    risk_counts = (
        decisions["risk_level"].value_counts().to_dict()
        if "risk_level" in decisions.columns else {}
    )
    average_risk = safe_float(
        decisions["risk_score"].mean()
        if "risk_score" in decisions.columns else 0
    )

    return clean_dict({
        "source": "tradingview_paper",
        "average_risk_score": round(average_risk, 2),
        "risk_distribution": risk_counts,
    })


@app.get("/api/tradingview/high-risk-trades")
def tradingview_high_risk_trades(
    limit: int = Query(10, ge=1, le=100),
):
    """Highest-risk TradingView trades."""

    df = tradingview_decisions().copy()

    if "risk_level" in df.columns:
        df = df[
            df["risk_level"].astype(str).str.upper().isin(
                ["HIGH", "CRITICAL"]
            )
        ]

    if "risk_score" in df.columns:
        df["risk_score"] = pd.to_numeric(
            df["risk_score"], errors="coerce"
        )
        df = df.sort_values(
            "risk_score", ascending=False, na_position="last"
        )

    df = df.head(limit)

    return clean_dict({
        "source": "tradingview_paper",
        "count": len(df),
        "trades": clean_records(df),
    })


@app.get("/api/tradingview/traders")
def tradingview_traders():
    """TradingView trader profiles."""

    profiles = tradingview_profiles()

    return {
        "source": "tradingview_paper",
        "count": len(profiles),
        "traders": clean_records(profiles),
    }


@app.get("/api/tradingview/traders/{account}")
def tradingview_trader(account: str):
    """Complete TradingView trader profile and distributions."""

    data = load_tradingview_analysis()
    profiles = data["profiles"]
    decisions = data["decisions"]
    behaviors = data["behaviors"]

    matches = profiles[
        profiles["account"].astype(str) == str(account)
    ]

    if matches.empty:
        raise HTTPException(
            status_code=404,
            detail=f"TradingView trader {account} not found.",
        )

    trader_decisions = decisions[
        decisions["account"].astype(str) == str(account)
    ] if "account" in decisions.columns else decisions.iloc[0:0]

    trader_behaviors = behaviors[
        behaviors["account"].astype(str) == str(account)
    ] if "account" in behaviors.columns else behaviors.iloc[0:0]

    return clean_dict({
        "source": "tradingview_paper",
        "profile": clean_records(matches.iloc[[0]])[0],
        "decision_distribution": (
            trader_decisions["decision"].value_counts().to_dict()
            if "decision" in trader_decisions.columns else {}
        ),
        "risk_distribution": (
            trader_decisions["risk_level"].value_counts().to_dict()
            if "risk_level" in trader_decisions.columns else {}
        ),
        "behavior_distribution": (
            trader_behaviors["behavior"].value_counts().to_dict()
            if "behavior" in trader_behaviors.columns else {}
        ),
        "behavior_event_count": len(trader_behaviors),
        "trade_count": len(trader_decisions),
    })


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "message": "Welcome to TradeMind AI",
        "docs": "/docs",
        "health": "/api/health",
    }
