import pandas as pd
from pathlib import Path


# ============================================================
# TRADEMIND AI - DECISION ENGINE
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[3]

FEATURE_FILE = BASE_DIR / "data" / "trade_features.csv"
BEHAVIOR_FILE = BASE_DIR / "data" / "behavior_flags.csv"
RISK_FILE = BASE_DIR / "data" / "risk_scores.csv"
PROFILE_FILE = BASE_DIR / "data" / "trader_profiles.csv"

OUTPUT_FILE = BASE_DIR / "data" / "trade_decisions.csv"


# ============================================================
# CONFIGURATION
# ============================================================

CRITICAL_RISK_THRESHOLD = 80
HIGH_RISK_THRESHOLD = 60

HIGH_RISK_BEHAVIORS = {
    "Overtrading",
    "Rapid Re-entry",
    "Oversizing",
    "Loss Streak",
    "Revenge Trading",
}


# ============================================================
# LOAD DATA
# ============================================================

def load_data():

    print("Loading TradeMind intelligence...")

    features = pd.read_csv(FEATURE_FILE)
    behaviors = pd.read_csv(BEHAVIOR_FILE)
    risks = pd.read_csv(RISK_FILE)
    profiles = pd.read_csv(PROFILE_FILE)

    print(f"Loaded features:  {len(features):,}")
    print(f"Loaded behaviors: {len(behaviors):,}")
    print(f"Loaded risks:     {len(risks):,}")
    print(f"Loaded profiles:  {len(profiles):,}")

    return features, behaviors, risks, profiles


# ============================================================
# BEHAVIOR SUMMARY
# ============================================================

def get_behavior_summary(behaviors):

    if behaviors.empty:
        return {}

    summary = {}

    grouped = behaviors.groupby("trade_id")

    for trade_id, group in grouped:

        detected = []

        for behavior in group["behavior"].unique():

            if behavior in HIGH_RISK_BEHAVIORS:
                detected.append(behavior)

        summary[trade_id] = detected

    return summary


# ============================================================
# PROFILE LOOKUP
# ============================================================

def get_profile_lookup(profiles):

    lookup = {}

    if profiles.empty:
        return lookup

    for _, row in profiles.iterrows():

        lookup[row["account"]] = {
            "discipline_score": row.get(
                "discipline_score",
                50
            ),
            "primary_risk": row.get(
                "primary_risk",
                "None"
            ),
            "win_rate": row.get(
                "win_rate",
                0
            ),
            "average_risk_score": row.get(
                "average_risk_score",
                0
            ),
        }

    return lookup


# ============================================================
# DECISION LOGIC
# ============================================================

def calculate_decision(
    risk_score,
    risk_level,
    behaviors,
    discipline_score,
):

    behavior_count = len(behaviors)

    # --------------------------------------------------------
    # CRITICAL
    # --------------------------------------------------------

    if (
        risk_level == "CRITICAL"
        or risk_score >= CRITICAL_RISK_THRESHOLD
    ):

        decision = "DO NOT TRADE"

        recommendation = (
            "Stop trading and enter a cooldown period. "
            "Multiple high-risk conditions are present."
        )

    # --------------------------------------------------------
    # HIGH
    # --------------------------------------------------------

    elif (
        risk_level == "HIGH"
        or risk_score >= HIGH_RISK_THRESHOLD
    ):

        decision = "AVOID / REDUCE RISK"

        recommendation = (
            "Avoid the trade or significantly reduce "
            "position size until behavior stabilizes."
        )

    # --------------------------------------------------------
    # MEDIUM
    # --------------------------------------------------------

    elif risk_level == "MEDIUM":

        decision = "CAUTION"

        recommendation = (
            "Trade only with controlled position sizing "
            "and strict risk management."
        )

    # --------------------------------------------------------
    # LOW
    # --------------------------------------------------------

    else:

        decision = "ALLOW"

        recommendation = (
            "No major behavioral risk detected. "
            "Normal risk controls should still apply."
        )

    # --------------------------------------------------------
    # DISCIPLINE OVERRIDE
    # --------------------------------------------------------

    if discipline_score < 20:

        if decision == "ALLOW":
            decision = "CAUTION"

        recommendation += (
            " Trader discipline is currently very low."
        )

    # --------------------------------------------------------
    # MULTIPLE BEHAVIORS
    # --------------------------------------------------------

    if behavior_count >= 3:

        if decision != "DO NOT TRADE":
            decision = "AVOID / REDUCE RISK"

        recommendation += (
            " Multiple behavioral patterns were detected."
        )

    return decision, recommendation


# ============================================================
# EVIDENCE GENERATION
# ============================================================

def generate_reasons(
    row,
    behaviors,
    risk_score,
    risk_level,
):

    reasons = []

    for behavior in behaviors:
        reasons.append(
            f"{behavior} detected"
        )

    if risk_score >= HIGH_RISK_THRESHOLD:

        reasons.append(
            f"Risk score: {risk_score}/100"
        )

    if risk_level in {"HIGH", "CRITICAL"}:

        reasons.append(
            f"Risk level: {risk_level}"
        )

    return " | ".join(reasons)


# ============================================================
# BUILD DECISIONS
# ============================================================

def build_decisions(
    features,
    behaviors,
    risks,
    profiles,
):

    behavior_lookup = get_behavior_summary(
        behaviors
    )

    profile_lookup = get_profile_lookup(
        profiles
    )

    # --------------------------------------------------------
    # Risk lookup
    # --------------------------------------------------------

    risk_lookup = {}

    for _, row in risks.iterrows():

        risk_lookup[row["trade_id"]] = {
            "risk_score": row.get(
                "risk_score",
                0
            ),
            "risk_level": row.get(
                "risk_level",
                "LOW"
            ),
        }

    decisions = []

    for _, row in features.iterrows():

        trade_id = row["trade_id"]
        account = row["account"]

        # ----------------------------------------------------
        # Risk
        # ----------------------------------------------------

        risk = risk_lookup.get(
            trade_id,
            {
                "risk_score": 0,
                "risk_level": "LOW",
            }
        )

        risk_score = float(
            risk["risk_score"]
        )

        risk_level = risk["risk_level"]

        # ----------------------------------------------------
        # Behaviors
        # ----------------------------------------------------

        detected_behaviors = behavior_lookup.get(
            trade_id,
            []
        )

        # ----------------------------------------------------
        # Trader profile
        # ----------------------------------------------------

        profile = profile_lookup.get(
            account,
            {
                "discipline_score": 50,
                "primary_risk": "None",
                "win_rate": 0,
                "average_risk_score": 0,
            }
        )

        discipline_score = float(
            profile["discipline_score"]
        )

        primary_risk = profile[
            "primary_risk"
        ]

        win_rate = float(
            profile["win_rate"]
        )

        # ----------------------------------------------------
        # Decision
        # ----------------------------------------------------

        decision, recommendation = calculate_decision(
            risk_score,
            risk_level,
            detected_behaviors,
            discipline_score,
        )

        reasons = generate_reasons(
            row,
            detected_behaviors,
            risk_score,
            risk_level,
        )

        # ----------------------------------------------------
        # Output
        # ----------------------------------------------------

        decisions.append({

            "trade_id": trade_id,

            "account": account,

            "symbol": row["symbol"],

            "direction": row["direction"],

            "entry_time": row["entry_time"],

            "risk_score": risk_score,

            "risk_level": risk_level,

            "discipline_score": discipline_score,

            "win_rate": win_rate,

            "primary_risk": primary_risk,

            "behavior_count": len(
                detected_behaviors
            ),

            "behaviors": ", ".join(
                detected_behaviors
            ),

            "decision": decision,

            "recommendation": recommendation,

            "reasons": reasons,
        })

    return pd.DataFrame(decisions)


# ============================================================
# SAVE
# ============================================================

def save_decisions(decisions):

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    decisions.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        "\nSaved trade decisions to:"
    )

    print(OUTPUT_FILE)


# ============================================================
# SUMMARY
# ============================================================

def show_summary(decisions):

    print(
        "\n========== DECISION ENGINE SUMMARY ==========\n"
    )

    if decisions.empty:

        print("No decisions generated.")

        return

    print(
        f"Total trades analyzed: "
        f"{len(decisions):,}"
    )

    print("\nDecision distribution:\n")

    print(
        decisions[
            "decision"
        ].value_counts()
    )

    print("\nRisk distribution:\n")

    print(
        decisions[
            "risk_level"
        ].value_counts()
    )

    print("\nBehavior distribution:\n")

    behavior_counts = {}

    for behaviors in decisions["behaviors"]:

        if not behaviors:
            continue

        for behavior in behaviors.split(", "):

            behavior_counts[behavior] = (
                behavior_counts.get(
                    behavior,
                    0
                ) + 1
            )

    if behavior_counts:

        print(
            pd.Series(
                behavior_counts
            ).sort_values(
                ascending=False
            )
        )

    print(
        "\nHighest-risk decisions:\n"
    )

    display_columns = [
        "trade_id",
        "symbol",
        "risk_score",
        "risk_level",
        "discipline_score",
        "behaviors",
        "decision",
    ]

    print(
        decisions[
            display_columns
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
        "Starting decision engine..."
    )

    (
        features,
        behaviors,
        risks,
        profiles,
    ) = load_data()

    print(
        "\nGenerating intelligent trade decisions..."
    )

    decisions = build_decisions(
        features,
        behaviors,
        risks,
        profiles,
    )

    save_decisions(
        decisions
    )

    show_summary(
        decisions
    )


if __name__ == "__main__":
    main()