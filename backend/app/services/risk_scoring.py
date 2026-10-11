import pandas as pd
from pathlib import Path


# ============================================================
# TRADEMIND AI - RISK SCORING ENGINE
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[3]

FEATURE_FILE = BASE_DIR / "data" / "trade_features.csv"
BEHAVIOR_FILE = BASE_DIR / "data" / "behavior_flags.csv"
OUTPUT_FILE = BASE_DIR / "data" / "risk_scores.csv"


# ============================================================
# CONFIGURATION
# ============================================================

MAX_RISK_SCORE = 100

OVERTRADING_WEIGHT = 20
RAPID_REENTRY_WEIGHT = 15
OVERSIZING_WEIGHT = 25
LOSS_STREAK_WEIGHT = 15
REVENGE_WEIGHT = 30

POSITION_RISK_WEIGHT = 10
TRADING_FREQUENCY_WEIGHT = 5


# ============================================================
# LOAD DATA
# ============================================================

def load_data():

    if not FEATURE_FILE.exists():
        raise FileNotFoundError(
            f"Feature dataset not found: {FEATURE_FILE}"
        )

    if not BEHAVIOR_FILE.exists():
        raise FileNotFoundError(
            f"Behavior dataset not found: {BEHAVIOR_FILE}"
        )

    features = pd.read_csv(FEATURE_FILE)
    behaviors = pd.read_csv(BEHAVIOR_FILE)

    print(
        f"Loaded feature records: {len(features):,}"
    )

    print(
        f"Loaded behavior flags: {len(behaviors):,}"
    )

    return features, behaviors


# ============================================================
# BEHAVIOR SCORE
# ============================================================

def calculate_behavior_score(behavior_rows):

    score = 0
    reasons = []

    if behavior_rows.empty:
        return score, reasons

    for _, row in behavior_rows.iterrows():

        behavior = row["behavior"]
        severity = row["severity"]

        if behavior == "Revenge Trading":

            score += REVENGE_WEIGHT

            reasons.append(
                "Revenge trading detected"
            )

        elif behavior == "Oversizing":

            score += OVERSIZING_WEIGHT

            reasons.append(
                "Position oversizing detected"
            )

        elif behavior == "Overtrading":

            score += OVERTRADING_WEIGHT

            reasons.append(
                "Overtrading detected"
            )

        elif behavior == "Rapid Re-entry":

            score += RAPID_REENTRY_WEIGHT

            reasons.append(
                "Rapid re-entry detected"
            )

        elif behavior == "Loss Streak":

            score += LOSS_STREAK_WEIGHT

            reasons.append(
                "Loss streak detected"
            )

    return score, reasons


# ============================================================
# POSITION RISK
# ============================================================

def calculate_position_risk(row):

    ratio = row.get(
        "position_size_ratio"
    )

    if pd.isna(ratio):

        return 0, []

    if ratio >= 10:

        return (
            POSITION_RISK_WEIGHT,
            [
                f"Position size is {ratio:.2f}× "
                "recent average"
            ]
        )

    if ratio >= 5:

        return (
            8,
            [
                f"Position size is {ratio:.2f}× "
                "recent average"
            ]
        )

    if ratio >= 2:

        return (
            5,
            [
                f"Position size is {ratio:.2f}× "
                "recent average"
            ]
        )

    return 0, []


# ============================================================
# TRADING FREQUENCY RISK
# ============================================================

def calculate_frequency_risk(row):

    trades_today = row.get(
        "trades_today"
    )

    if pd.isna(trades_today):

        return 0, []

    if trades_today >= 15:

        return (
            TRADING_FREQUENCY_WEIGHT,
            [
                f"{int(trades_today)} trades "
                "already taken today"
            ]
        )

    if trades_today >= 10:

        return (
            4,
            [
                f"{int(trades_today)} trades "
                "already taken today"
            ]
        )

    if trades_today > 5:

        return (
            2,
            [
                f"{int(trades_today)} trades "
                "already taken today"
            ]
        )

    return 0, []


# ============================================================
# RISK LEVEL
# ============================================================

def get_risk_level(score):

    if score >= 70:

        return "CRITICAL"

    if score >= 50:

        return "HIGH"

    if score >= 30:

        return "MEDIUM"

    return "LOW"


# ============================================================
# RECOMMENDATION
# ============================================================

def get_recommendation(score):

    if score >= 70:

        return "STOP / DO NOT TRADE"

    if score >= 50:

        return "WAIT / REDUCE RISK"

    if score >= 30:

        return "TRADE WITH CAUTION"

    return "NORMAL"


# ============================================================
# SCORE SINGLE TRADE
# ============================================================

def score_trade(row, behavior_rows):

    risk_score = 0
    reasons = []

    # --------------------------------------------------------
    # Behavioral risk
    # --------------------------------------------------------

    behavior_score, behavior_reasons = (
        calculate_behavior_score(
            behavior_rows
        )
    )

    risk_score += behavior_score
    reasons.extend(
        behavior_reasons
    )

    # --------------------------------------------------------
    # Position risk
    # --------------------------------------------------------

    position_score, position_reasons = (
        calculate_position_risk(row)
    )

    risk_score += position_score
    reasons.extend(
        position_reasons
    )

    # --------------------------------------------------------
    # Frequency risk
    # --------------------------------------------------------

    frequency_score, frequency_reasons = (
        calculate_frequency_risk(row)
    )

    risk_score += frequency_score
    reasons.extend(
        frequency_reasons
    )

    # --------------------------------------------------------
    # Clamp score
    # --------------------------------------------------------

    risk_score = min(
        MAX_RISK_SCORE,
        risk_score
    )

    risk_score = round(
        risk_score,
        1
    )

    risk_level = get_risk_level(
        risk_score
    )

    recommendation = get_recommendation(
        risk_score
    )

    return (
        risk_score,
        risk_level,
        recommendation,
        reasons
    )


# ============================================================
# MAIN ENGINE
# ============================================================

def calculate_risk_scores(
    features,
    behaviors
):

    results = []

    print(
        "\nCalculating trade risk scores..."
    )

    for _, row in features.iterrows():

        trade_id = row["trade_id"]

        trade_behaviors = behaviors[
            behaviors["trade_id"]
            == trade_id
        ]

        (
            risk_score,
            risk_level,
            recommendation,
            reasons
        ) = score_trade(
            row,
            trade_behaviors
        )

        results.append({

            "trade_id":
                trade_id,

            "account":
                row["account"],

            "symbol":
                row["symbol"],

            "direction":
                row["direction"],

            "entry_time":
                row["entry_time"],

            "net_pnl":
                row["net_pnl"],

            "risk_score":
                risk_score,

            "risk_level":
                risk_level,

            "recommendation":
                recommendation,

            "reason_count":
                len(reasons),

            "reasons":
                " | ".join(
                    reasons
                )

        })

    return pd.DataFrame(
        results
    )


# ============================================================
# SAVE
# ============================================================

def save_results(
    results
):

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    results.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        "\nSaved risk scores to:"
    )

    print(
        OUTPUT_FILE
    )


# ============================================================
# SUMMARY
# ============================================================

def show_summary(
    results
):

    print(
        "\n========== RISK SCORING SUMMARY ==========\n"
    )

    print(
        f"Total trades scored: "
        f"{len(results):,}"
    )

    print(
        "\nRisk level distribution:\n"
    )

    print(
        results[
            "risk_level"
        ].value_counts()
    )

    print(
        "\nAverage risk score:"
    )

    print(
        f"{results['risk_score'].mean():.2f}"
    )

    print(
        "\nHighest risk trades:\n"
    )

    columns = [
        "trade_id",
        "account",
        "symbol",
        "risk_score",
        "risk_level",
        "recommendation",
        "reasons"
    ]

    print(
        results[
            columns
        ]
        .sort_values(
            "risk_score",
            ascending=False
        )
        .head(15)
        .to_string(
            index=False
        )
    )

    print(
        "\n============================================\n"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n========== TRADEMIND AI ==========\n"
    )

    print(
        "Starting risk scoring engine..."
    )

    features, behaviors = load_data()

    results = calculate_risk_scores(
        features,
        behaviors
    )

    save_results(
        results
    )

    show_summary(
        results
    )


if __name__ == "__main__":

    main()