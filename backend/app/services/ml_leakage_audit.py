import pandas as pd
from pathlib import Path


# ============================================================
# TRADEMIND AI - ML LEAKAGE AUDIT
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[3]

INPUT_FILE = BASE_DIR / "data" / "ml_dataset.csv"


# ============================================================
# CONFIGURATION
# ============================================================

TARGET = "target"


# Features that are especially important to audit because
# they contain information derived from trading outcomes.
OUTCOME_RELATED_FEATURES = [
    "previous_trade_pnl",
    "previous_trade_is_loss",
    "previous_trade_is_win",
    "win_streak",
    "loss_streak",
    "previous_loss_streak",
    "previous_session_pnl",
    "behavior_loss_streak",
    "behavior_revenge",
]


# Features that directly describe the current trade outcome
# and therefore must NEVER be used as predictors.
FORBIDDEN_CURRENT_TRADE_FEATURES = [
    "net_pnl",
    "gross_pnl",
    "fees",
    "is_win",
    "is_loss",
    "is_breakeven",
    "exit_time",
    "exit_price",
]


# ============================================================
# LOAD
# ============================================================

def load_dataset():

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            f"ML dataset not found: {INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    print(
        f"Loaded records: {len(df):,}"
    )

    return df


# ============================================================
# DUPLICATE COLUMN AUDIT
# ============================================================

def audit_duplicate_columns(df):

    print(
        "\n========== DUPLICATE COLUMN AUDIT =========="
    )

    duplicate_columns = []

    seen = set()

    for column in df.columns:

        if column in seen:

            duplicate_columns.append(
                column
            )

        seen.add(column)

    if duplicate_columns:

        print(
            "Duplicate column names detected:"
        )

        for column in duplicate_columns:

            print(
                f"- {column}"
            )

    else:

        print(
            "No duplicate column names."
        )


# ============================================================
# FORBIDDEN FEATURE AUDIT
# ============================================================

def audit_forbidden_features(df):

    print(
        "\n========== FORBIDDEN FEATURE AUDIT =========="
    )

    found = []

    for column in FORBIDDEN_CURRENT_TRADE_FEATURES:

        if column in df.columns:

            found.append(column)

    if found:

        print(
            "🚨 CURRENT-TRADE OUTCOME FEATURES FOUND:"
        )

        for column in found:

            print(
                f"- {column}"
            )

        print(
            "\nThese features MUST NOT be used for prediction."
        )

    else:

        print(
            "No forbidden current-trade outcome features found."
        )


# ============================================================
# OUTCOME-RELATED FEATURE AUDIT
# ============================================================

def audit_outcome_related_features(df):

    print(
        "\n========== OUTCOME-RELATED FEATURE AUDIT =========="
    )

    for column in OUTCOME_RELATED_FEATURES:

        if column not in df.columns:

            continue

        print(
            f"\nFeature: {column}"
        )

        print(
            f"Type: {df[column].dtype}"
        )

        print(
            f"Missing: "
            f"{df[column].isna().sum():,}"
        )

        print(
            "Sample:"
        )

        print(
            df[
                [
                    "trade_id",
                    "entry_time",
                    "target",
                    column
                ]
            ]
            .head(10)
            .to_string(index=False)
        )


# ============================================================
# TARGET CORRELATION AUDIT
# ============================================================

def audit_target_relationships(df):

    print(
        "\n========== TARGET RELATIONSHIP AUDIT =========="
    )

    numeric_df = df.select_dtypes(
        include="number"
    )

    if TARGET not in numeric_df.columns:

        print(
            "Target is not numeric."
        )

        return

    correlations = (
        numeric_df
        .corr(numeric_only=True)[TARGET]
        .drop(TARGET)
        .abs()
        .sort_values(
            ascending=False
        )
    )

    print(
        "\nAbsolute correlation with target:"
    )

    print(
        correlations
        .head(20)
        .to_string()
    )


# ============================================================
# TEMPORAL AUDIT
# ============================================================

def audit_temporal_order(df):

    print(
        "\n========== TEMPORAL AUDIT =========="
    )

    if "entry_time" not in df.columns:

        print(
            "entry_time not found."
        )

        return

    timestamps = pd.to_datetime(
        df["entry_time"],
        errors="coerce"
    )

    print(
        f"Earliest trade: "
        f"{timestamps.min()}"
    )

    print(
        f"Latest trade:   "
        f"{timestamps.max()}"
    )

    print(
        f"Invalid timestamps: "
        f"{timestamps.isna().sum():,}"
    )

    sorted_timestamps = timestamps.sort_values()

    is_sorted = (
        timestamps.reset_index(drop=True)
        .equals(
            sorted_timestamps.reset_index(drop=True)
        )
    )

    print(
        f"Dataset already chronological: "
        f"{is_sorted}"
    )


# ============================================================
# TARGET DISTRIBUTION
# ============================================================

def audit_target(df):

    print(
        "\n========== TARGET AUDIT =========="
    )

    print(
        df[TARGET].value_counts(
            dropna=False
        )
    )

    print(
        "\nTarget percentages:"
    )

    print(
        (
            df[TARGET]
            .value_counts(normalize=True)
            * 100
        )
        .round(2)
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n========== TRADEMIND AI ==========\n"
    )

    print(
        "Starting ML leakage audit..."
    )

    df = load_dataset()

    audit_duplicate_columns(df)

    audit_forbidden_features(df)

    audit_outcome_related_features(df)

    audit_target_relationships(df)

    audit_temporal_order(df)

    audit_target(df)

    print(
        "\n=================================="
    )

    print(
        "ML LEAKAGE AUDIT COMPLETE"
    )

    print(
        "==================================\n"
    )


if __name__ == "__main__":
    main()
