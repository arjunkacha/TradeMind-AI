import pandas as pd
from pathlib import Path


# ============================================================
# TRADEMIND AI
# TRADINGVIEW ANALYSIS PIPELINE
# ============================================================
#
# This service takes normalized TradingView trades and sends
# them through the EXISTING TradeMind intelligence engines.
#
# Existing engines are reused:
#
# 1. Feature Engineering
# 2. Behavioral Detection
# 3. Risk Scoring
# 4. Trader Profile
# 5. ML Prediction
# 6. Decision Engine
#
# IMPORTANT:
# Existing historical TradeMind datasets are NOT modified.
#
# TradingView analysis is stored separately under:
#
# data/tradingview_analysis/
#
# ============================================================


from app.services.feature_engineering import (
    prepare_data,
    add_basic_features,
    add_account_trade_sequence,
    add_previous_trade_features,
    add_streak_features,
    add_position_size_features,
    add_session_pnl,
    add_holding_features,
)

from app.services.behavior_detection import (
    detect_behaviors,
)

from app.services.risk_scoring import (
    calculate_risk_scores,
)

from app.services.trader_profile import (
    build_profiles,
)

from app.services.ml_dataset import (
    prepare_dataset,
)

from app.services.decision_engine import (
    load_ml_model,
    build_decisions,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[3]

DATA_DIR = BASE_DIR / "data"

TRADINGVIEW_TRADES_FILE = (
    DATA_DIR / "tradingview_trades.csv"
)

ANALYSIS_DIR = (
    DATA_DIR / "tradingview_analysis"
)


# ============================================================
# FEATURE ENGINEERING
# ============================================================

def build_tradingview_features(
    trades
):
    """
    Run the existing TradeMind feature engineering
    pipeline on TradingView trades.

    This intentionally reuses the same feature definitions
    used by the historical TradeMind dataset.
    """

    df = trades.copy()

    # --------------------------------------------------------
    # Prepare timestamps and account ordering
    # --------------------------------------------------------

    df = prepare_data(
        df
    )

    # --------------------------------------------------------
    # Basic features
    # --------------------------------------------------------

    df = add_basic_features(
        df
    )

    # --------------------------------------------------------
    # Trade sequence
    # --------------------------------------------------------

    df = add_account_trade_sequence(
        df
    )

    # --------------------------------------------------------
    # Previous trade features
    # --------------------------------------------------------

    df = add_previous_trade_features(
        df
    )

    # --------------------------------------------------------
    # Streak features
    # --------------------------------------------------------

    df = add_streak_features(
        df
    )

    # --------------------------------------------------------
    # Position size features
    # --------------------------------------------------------

    df = add_position_size_features(
        df
    )

    # --------------------------------------------------------
    # Session P/L
    # --------------------------------------------------------

    df = add_session_pnl(
        df
    )

    # --------------------------------------------------------
    # Holding time
    # --------------------------------------------------------

    df = add_holding_features(
        df
    )

    return df


# ============================================================
# BUILD ML STATE
# ============================================================

def add_ml_state(
    features
):
    """
    Build the same pre-trade ML state used by the existing
    TradeMind ML dataset builder.

    The current-trade outcome is NOT used as an ML input
    because the trusted model was trained on pre-trade
    information.
    """

    ml_dataset = prepare_dataset(
        features.copy()
    )

    enriched = features.copy()

    # --------------------------------------------------------
    # Add ML-state columns that do not already exist
    # --------------------------------------------------------

    ml_columns = [
        "trade_id",
        "previous_session_pnl",
        "behavior_overtrading",
        "behavior_rapid_reentry",
        "behavior_oversizing",
    ]

    available_columns = [
        column
        for column in ml_columns
        if column in ml_dataset.columns
    ]

    if available_columns:

        state = ml_dataset[
            available_columns
        ].copy()

        enriched = enriched.merge(
            state,
            on="trade_id",
            how="left",
            suffixes=(
                "",
                "_ml",
            ),
        )

    # --------------------------------------------------------
    # Resolve possible duplicate columns
    # --------------------------------------------------------

    for column in [
        "previous_session_pnl",
        "behavior_overtrading",
        "behavior_rapid_reentry",
        "behavior_oversizing",
    ]:

        ml_column = f"{column}_ml"

        if (
            column not in enriched.columns
            and ml_column in enriched.columns
        ):

            enriched[column] = (
                enriched[ml_column]
            )

        if ml_column in enriched.columns:

            enriched = enriched.drop(
                columns=[ml_column]
            )

    return enriched


# ============================================================
# SAVE ANALYSIS
# ============================================================

def save_analysis(
    features,
    behaviors,
    risks,
    profiles,
    decisions,
):
    """
    Save TradingView-specific analysis.

    Existing historical output files are untouched.
    """

    ANALYSIS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    features.to_csv(
        ANALYSIS_DIR / "features.csv",
        index=False,
    )

    behaviors.to_csv(
        ANALYSIS_DIR / "behaviors.csv",
        index=False,
    )

    risks.to_csv(
        ANALYSIS_DIR / "risks.csv",
        index=False,
    )

    profiles.to_csv(
        ANALYSIS_DIR / "profiles.csv",
        index=False,
    )

    decisions.to_csv(
        ANALYSIS_DIR / "decisions.csv",
        index=False,
    )


# ============================================================
# MAIN PIPELINE
# ============================================================

def run_tradingview_analysis():
    """
    Run the complete TradeMind intelligence pipeline
    for TradingView Paper Trading data.
    """

    print(
        "\n=============================================="
    )

    print(
        "TRADEMIND AI - TRADINGVIEW ANALYSIS"
    )

    print(
        "==============================================\n"
    )

    # ========================================================
    # LOAD TRADINGVIEW TRADES
    # ========================================================

    if not TRADINGVIEW_TRADES_FILE.exists():

        raise FileNotFoundError(
            "TradingView trade file not found: "
            f"{TRADINGVIEW_TRADES_FILE}"
        )

    trades = pd.read_csv(
        TRADINGVIEW_TRADES_FILE
    )

    print(
        f"TradingView trades loaded: "
        f"{len(trades):,}"
    )

    # ========================================================
    # FEATURE ENGINEERING
    # ========================================================

    print(
        "\n[1/6] Feature engineering..."
    )

    features = build_tradingview_features(
        trades
    )

    print(
        f"Feature records: "
        f"{len(features):,}"
    )

    # ========================================================
    # BEHAVIOR DETECTION
    # ========================================================

    print(
        "\n[2/6] Behavioral AI..."
    )

    behaviors = detect_behaviors(
        features
    )

    print(
        f"Behavior flags: "
        f"{len(behaviors):,}"
    )

    # ========================================================
    # RISK SCORING
    # ========================================================

    print(
        "\n[3/6] Risk intelligence..."
    )

    risks = calculate_risk_scores(
        features,
        behaviors,
    )

    print(
        f"Risk records: "
        f"{len(risks):,}"
    )

    # ========================================================
    # TRADER PROFILE
    # ========================================================

    print(
        "\n[4/6] Trader profile..."
    )

    profiles = build_profiles(
        features,
        behaviors,
        risks,
    )

    print(
        f"Trader profiles: "
        f"{len(profiles):,}"
    )

    # ========================================================
    # ML STATE
    # ========================================================

    print(
        "\n[5/6] ML intelligence..."
    )

    enriched_features = add_ml_state(
        features
    )

    ml_model = load_ml_model()

    # ========================================================
    # DECISION ENGINE
    # ========================================================

    print(
        "\n[6/6] Decision engine..."
    )

    decisions = build_decisions(
        enriched_features,
        behaviors,
        risks,
        profiles,
        ml_model,
    )

    print(
        f"Decisions generated: "
        f"{len(decisions):,}"
    )

    # ========================================================
    # SAVE
    # ========================================================

    save_analysis(
        enriched_features,
        behaviors,
        risks,
        profiles,
        decisions,
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    print(
        "\n=============================================="
    )

    print(
        "TRADINGVIEW ANALYSIS COMPLETE"
    )

    print(
        "=============================================="
    )

    print(
        f"Trades       : {len(trades):,}"
    )

    print(
        f"Behaviors    : {len(behaviors):,}"
    )

    print(
        f"Risk records : {len(risks):,}"
    )

    print(
        f"Profiles     : {len(profiles):,}"
    )

    print(
        f"Decisions    : {len(decisions):,}"
    )

    print(
        "\nAnalysis saved to:"
    )

    print(
        ANALYSIS_DIR
    )

    print(
        "\n==============================================\n"
    )

    return {
        "trades": trades,
        "features": enriched_features,
        "behaviors": behaviors,
        "risks": risks,
        "profiles": profiles,
        "decisions": decisions,
    }


# ============================================================
# COMMAND LINE TEST
# ============================================================

if __name__ == "__main__":

    run_tradingview_analysis()