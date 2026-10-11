import pandas as pd
from pathlib import Path


# ============================================================
# TRADEMIND AI - TRADER PROFILE ENGINE
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[3]

FEATURE_FILE = BASE_DIR / "data" / "trade_features.csv"
BEHAVIOR_FILE = BASE_DIR / "data" / "behavior_flags.csv"
RISK_FILE = BASE_DIR / "data" / "risk_scores.csv"

OUTPUT_FILE = BASE_DIR / "data" / "trader_profiles.csv"


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

    if not RISK_FILE.exists():
        raise FileNotFoundError(
            f"Risk dataset not found: {RISK_FILE}"
        )

    features = pd.read_csv(FEATURE_FILE)
    behaviors = pd.read_csv(BEHAVIOR_FILE)
    risks = pd.read_csv(RISK_FILE)

    print(
        f"Loaded feature records: {len(features):,}"
    )

    print(
        f"Loaded behavior flags: {len(behaviors):,}"
    )

    print(
        f"Loaded risk scores: {len(risks):,}"
    )

    return features, behaviors, risks


# ============================================================
# SAFE PERCENTAGE
# ============================================================

def percentage(value, total):

    if total == 0:
        return 0.0

    return round(
        (value / total) * 100,
        2
    )


# ============================================================
# DISCIPLINE SCORE
# ============================================================

def calculate_discipline_score(
    total_trades,
    overtrading,
    rapid_reentry,
    oversizing,
    loss_streak,
    revenge
):

    if total_trades == 0:
        return 100.0

    behavior_events = (
        overtrading
        + rapid_reentry
        + oversizing
        + loss_streak
        + revenge
    )

    behavior_rate = (
        behavior_events / total_trades
    )

    score = 100 - (
        behavior_rate * 100
    )

    # Extra penalty for critical behavior
    score -= revenge * 2

    return round(
        max(0, min(100, score)),
        2
    )


# ============================================================
# BEHAVIOR LEVEL
# ============================================================

def behavior_level(
    count,
    total_trades
):

    rate = (
        count / total_trades
        if total_trades > 0
        else 0
    )

    if rate >= 0.20:
        return "HIGH"

    if rate >= 0.08:
        return "MEDIUM"

    if count > 0:
        return "LOW"

    return "NONE"


# ============================================================
# PRIMARY RISK
# ============================================================

def determine_primary_risk(
    counts
):

    if not counts:
        return "None"

    primary = max(
        counts,
        key=counts.get
    )

    if counts[primary] == 0:
        return "None"

    return primary


# ============================================================
# TRADER PROFILE
# ============================================================

def build_profiles(
    features,
    behaviors,
    risks
):

    profiles = []

    accounts = features[
        "account"
    ].dropna().unique()

    print(
        f"\nBuilding profiles for "
        f"{len(accounts)} accounts..."
    )

    for account in accounts:

        trader = features[
            features["account"] == account
        ]

        trader_behaviors = behaviors[
            behaviors["account"] == account
        ]

        trader_risks = risks[
            risks["account"] == account
        ]

        total_trades = len(trader)

        # ----------------------------------------------------
        # PERFORMANCE
        # ----------------------------------------------------

        wins = int(
            trader["is_win"].sum()
        )

        losses = int(
            trader["is_loss"].sum()
        )

        breakeven = int(
            trader["is_breakeven"].sum()
        )

        win_rate = percentage(
            wins,
            total_trades
        )

        loss_rate = percentage(
            losses,
            total_trades
        )

        net_pnl = round(
            trader["net_pnl"].sum(),
            2
        )

        average_pnl = round(
            trader["net_pnl"].mean(),
            2
        )

        # ----------------------------------------------------
        # RISK
        # ----------------------------------------------------

        average_risk = round(
            trader_risks[
                "risk_score"
            ].mean(),
            2
        )

        high_risk_trades = int(
            trader_risks[
                "risk_level"
            ].isin(
                ["HIGH", "CRITICAL"]
            ).sum()
        )

        critical_risk_trades = int(
            (
                trader_risks[
                    "risk_level"
                ] == "CRITICAL"
            ).sum()
        )

        # ----------------------------------------------------
        # BEHAVIOR COUNTS
        # ----------------------------------------------------

        overtrading = int(
            (
                trader_behaviors[
                    "behavior"
                ] == "Overtrading"
            ).sum()
        )

        rapid_reentry = int(
            (
                trader_behaviors[
                    "behavior"
                ] == "Rapid Re-entry"
            ).sum()
        )

        oversizing = int(
            (
                trader_behaviors[
                    "behavior"
                ] == "Oversizing"
            ).sum()
        )

        loss_streak = int(
            (
                trader_behaviors[
                    "behavior"
                ] == "Loss Streak"
            ).sum()
        )

        revenge = int(
            (
                trader_behaviors[
                    "behavior"
                ] == "Revenge Trading"
            ).sum()
        )

        # ----------------------------------------------------
        # BEHAVIOR LEVELS
        # ----------------------------------------------------

        overtrading_level = behavior_level(
            overtrading,
            total_trades
        )

        rapid_reentry_level = behavior_level(
            rapid_reentry,
            total_trades
        )

        oversizing_level = behavior_level(
            oversizing,
            total_trades
        )

        loss_streak_level = behavior_level(
            loss_streak,
            total_trades
        )

        revenge_level = behavior_level(
            revenge,
            total_trades
        )

        # ----------------------------------------------------
        # DISCIPLINE
        # ----------------------------------------------------

        discipline_score = (
            calculate_discipline_score(
                total_trades,
                overtrading,
                rapid_reentry,
                oversizing,
                loss_streak,
                revenge
            )
        )

        # ----------------------------------------------------
        # PRIMARY RISK
        # ----------------------------------------------------

        behavior_counts = {

            "Overtrading":
                overtrading,

            "Rapid Re-entry":
                rapid_reentry,

            "Oversizing":
                oversizing,

            "Loss Streak":
                loss_streak,

            "Revenge Trading":
                revenge
        }

        primary_risk = determine_primary_risk(
            behavior_counts
        )

        # ----------------------------------------------------
        # PROFILE
        # ----------------------------------------------------

        profiles.append({

            "account":
                account,

            "total_trades":
                total_trades,

            "wins":
                wins,

            "losses":
                losses,

            "breakeven":
                breakeven,

            "win_rate":
                win_rate,

            "loss_rate":
                loss_rate,

            "net_pnl":
                net_pnl,

            "average_trade_pnl":
                average_pnl,

            "average_risk_score":
                average_risk,

            "high_risk_trades":
                high_risk_trades,

            "critical_risk_trades":
                critical_risk_trades,

            "overtrading_count":
                overtrading,

            "rapid_reentry_count":
                rapid_reentry,

            "oversizing_count":
                oversizing,

            "loss_streak_count":
                loss_streak,

            "revenge_trading_count":
                revenge,

            "overtrading_level":
                overtrading_level,

            "rapid_reentry_level":
                rapid_reentry_level,

            "oversizing_level":
                oversizing_level,

            "loss_streak_level":
                loss_streak_level,

            "revenge_trading_level":
                revenge_level,

            "discipline_score":
                discipline_score,

            "primary_risk":
                primary_risk
        })

    return pd.DataFrame(
        profiles
    )


# ============================================================
# SAVE
# ============================================================

def save_profiles(
    profiles
):

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    profiles.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        "\nSaved trader profiles to:"
    )

    print(
        OUTPUT_FILE
    )


# ============================================================
# SUMMARY
# ============================================================

def show_summary(
    profiles
):

    print(
        "\n========== TRADER PROFILE SUMMARY ==========\n"
    )

    print(
        f"Total traders: "
        f"{len(profiles):,}"
    )

    print(
        "\nAverage discipline score:"
    )

    print(
        f"{profiles['discipline_score'].mean():.2f}/100"
    )

    print(
        "\nAverage risk score:"
    )

    print(
        f"{profiles['average_risk_score'].mean():.2f}/100"
    )

    print(
        "\nPrimary risk distribution:\n"
    )

    print(
        profiles[
            "primary_risk"
        ].value_counts()
    )

    print(
        "\nHighest-risk traders:\n"
    )

    columns = [
        "account",
        "total_trades",
        "win_rate",
        "net_pnl",
        "average_risk_score",
        "discipline_score",
        "primary_risk"
    ]

    print(
        profiles[
            columns
        ]
        .sort_values(
            "average_risk_score",
            ascending=False
        )
        .head(10)
        .to_string(
            index=False
        )
    )

    print(
        "\nLowest-discipline traders:\n"
    )

    columns = [
        "account",
        "total_trades",
        "win_rate",
        "discipline_score",
        "primary_risk",
        "revenge_trading_count",
        "oversizing_count",
        "overtrading_count"
    ]

    print(
        profiles[
            columns
        ]
        .sort_values(
            "discipline_score"
        )
        .head(10)
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
        "Starting trader profile engine..."
    )

    features, behaviors, risks = load_data()

    profiles = build_profiles(
        features,
        behaviors,
        risks
    )

    save_profiles(
        profiles
    )

    show_summary(
        profiles
    )


if __name__ == "__main__":
    main()