import pandas as pd
from pathlib import Path


# ============================================================
# TRADEMIND AI - BEHAVIOR DETECTION ENGINE
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[3]

INPUT_FILE = BASE_DIR / "data" / "trade_features.csv"
OUTPUT_FILE = BASE_DIR / "data" / "behavior_flags.csv"


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

OVERTRADING_THRESHOLD = 5

RAPID_REENTRY_MINUTES = 15

REVENGE_SIZE_RATIO = 1.50

OVERSIZING_RATIO = 2.00

LOSS_STREAK_THRESHOLD = 2


# ============================================================
# LOAD DATA
# ============================================================

def load_features():

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            f"Feature dataset not found: {INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    print(
        f"Loaded feature records: {len(df):,}"
    )

    return df


# ============================================================
# HELPER
# ============================================================

def add_flag(
    flags,
    row,
    behavior,
    severity,
    score,
    evidence
):

    flags.append({

        "trade_id": row["trade_id"],

        "account": row["account"],

        "symbol": row["symbol"],

        "entry_time": row["entry_time"],

        "behavior": behavior,

        "severity": severity,

        "score": score,

        "evidence": evidence

    })


# ============================================================
# OVERTRADING
# ============================================================

def detect_overtrading(df, flags):

    for _, row in df.iterrows():

        trades_today = row["trades_today"]

        if trades_today > OVERTRADING_THRESHOLD:

            score = min(
                100,
                60 + (
                    trades_today
                    - OVERTRADING_THRESHOLD
                ) * 5
            )

            evidence = (
                f"{int(trades_today)} trades "
                f"already taken today "
                f"(threshold: "
                f"{OVERTRADING_THRESHOLD})"
            )

            add_flag(
                flags,
                row,
                "Overtrading",
                "HIGH",
                score,
                evidence
            )


# ============================================================
# RAPID RE-ENTRY
# ============================================================

def detect_rapid_reentry(df, flags):

    for _, row in df.iterrows():

        minutes = row[
            "time_since_previous_trade"
        ]

        if (
            minutes >= 0
            and minutes <= RAPID_REENTRY_MINUTES
        ):

            score = 50

            if minutes <= 5:

                score = 75

            elif minutes <= 10:

                score = 65

            evidence = (
                f"New trade entered "
                f"{minutes:.1f} minutes "
                f"after previous trade"
            )

            add_flag(
                flags,
                row,
                "Rapid Re-entry",
                "MEDIUM",
                score,
                evidence
            )


# ============================================================
# OVERSIZING
# ============================================================

def detect_oversizing(df, flags):

    for _, row in df.iterrows():

        ratio = row[
            "position_size_ratio"
        ]

        if pd.isna(ratio):

            continue

        if ratio >= OVERSIZING_RATIO:

            score = min(
                100,
                60 + (
                    ratio
                    - OVERSIZING_RATIO
                ) * 10
            )

            score = round(
                score,
                1
            )

            evidence = (
                f"Position size is "
                f"{ratio:.2f}× the trader's "
                f"recent average size"
            )

            add_flag(
                flags,
                row,
                "Oversizing",
                "HIGH",
                score,
                evidence
            )


# ============================================================
# LOSS STREAK
# ============================================================

def detect_loss_streak(df, flags):

    for _, row in df.iterrows():

        streak = row[
            "loss_streak"
        ]

        if streak >= LOSS_STREAK_THRESHOLD:

            score = min(
                100,
                50 + (
                    streak
                    - LOSS_STREAK_THRESHOLD
                ) * 10
            )

            evidence = (
                f"Current losing streak: "
                f"{int(streak)} trades"
            )

            add_flag(
                flags,
                row,
                "Loss Streak",
                "MEDIUM",
                score,
                evidence
            )


# ============================================================
# REVENGE TRADING
# ============================================================

def detect_revenge_trading(df, flags):

    for _, row in df.iterrows():

        previous_loss = (
            row["previous_trade_is_loss"]
            == 1
        )

        rapid_entry = (
            row["time_since_previous_trade"]
            >= 0
            and
            row["time_since_previous_trade"]
            <= RAPID_REENTRY_MINUTES
        )

        size_increased = (
            not pd.isna(
                row["position_size_ratio"]
            )
            and
            row["position_size_ratio"]
            >= REVENGE_SIZE_RATIO
        )

        if (
            previous_loss
            and rapid_entry
            and size_increased
        ):

            score = 80

            # Increase confidence when
            # the trader was already losing
            # repeatedly.

            previous_loss_streak = (
                row["previous_loss_streak"]
            )

            if previous_loss_streak >= 2:

                score += 10

            score = min(
                100,
                score
            )

            evidence = (
                f"Previous trade was a loss; "
                f"re-entered after "
                f"{row['time_since_previous_trade']:.1f} "
                f"minutes; "
                f"position size was "
                f"{row['position_size_ratio']:.2f}× "
                f"normal"
            )

            if previous_loss_streak >= 2:

                evidence += (
                    f"; previous loss streak "
                    f"was {int(previous_loss_streak)}"
                )

            add_flag(
                flags,
                row,
                "Revenge Trading",
                "CRITICAL",
                score,
                evidence
            )


# ============================================================
# MAIN DETECTION ENGINE
# ============================================================

def detect_behaviors(df):

    flags = []

    detect_overtrading(
        df,
        flags
    )

    detect_rapid_reentry(
        df,
        flags
    )

    detect_oversizing(
        df,
        flags
    )

    detect_loss_streak(
        df,
        flags
    )

    detect_revenge_trading(
        df,
        flags
    )

    return pd.DataFrame(flags)


# ============================================================
# SAVE
# ============================================================

def save_flags(flags_df):

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    flags_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        f"\nSaved behavior flags to:"
    )

    print(
        OUTPUT_FILE
    )


# ============================================================
# SUMMARY
# ============================================================

def show_summary(flags_df):

    print(
        "\n========== BEHAVIOR DETECTION SUMMARY ==========\n"
    )

    if flags_df.empty:

        print(
            "No behavioral patterns detected."
        )

        return

    print(
        f"Total behavioral flags: "
        f"{len(flags_df):,}"
    )

    print("\nBehavior distribution:\n")

    print(
        flags_df[
            "behavior"
        ].value_counts()
    )

    print(
        "\nSeverity distribution:\n"
    )

    print(
        flags_df[
            "severity"
        ].value_counts()
    )

    print(
        "\nTop behavioral events:\n"
    )

    print(
        flags_df[
            [
                "trade_id",
                "account",
                "symbol",
                "behavior",
                "severity",
                "score",
                "evidence"
            ]
        ]
        .sort_values(
            "score",
            ascending=False
        )
        .head(15)
        .to_string(
            index=False
        )
    )

    print(
        "\n=================================================\n"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n========== TRADEMIND AI ==========\n"
    )

    print(
        "Starting behavioral detection..."
    )

    df = load_features()

    flags_df = detect_behaviors(
        df
    )

    save_flags(
        flags_df
    )

    show_summary(
        flags_df
    )


if __name__ == "__main__":

    main()