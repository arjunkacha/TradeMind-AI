import pandas as pd
from pathlib import Path


# ============================================================
# TRADEMIND AI - ML DATASET BUILDER
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[3]

INPUT_FILE = BASE_DIR / "data" / "trade_features.csv"
OUTPUT_FILE = BASE_DIR / "data" / "ml_dataset.csv"


# ============================================================
# LOAD
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
# PREPARE
# ============================================================

def prepare_dataset(df):

    print("\nPreparing ML dataset...")

    df = df.copy()

    # --------------------------------------------------------
    # TIME
    # --------------------------------------------------------

    df["entry_time"] = pd.to_datetime(
        df["entry_time"]
    )

    df = df.sort_values(
        ["entry_time", "trade_id"]
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # PREVIOUS SESSION P/L
    #
    # IMPORTANT:
    # We must NOT include the current trade's P/L.
    # --------------------------------------------------------

    df["previous_session_pnl"] = (
        df.groupby(
            ["account", "trading_date"]
        )["net_pnl"]
        .cumsum()
        - df["net_pnl"]
    )

    # --------------------------------------------------------
    # BEHAVIOR FEATURES
    #
    # These are deterministic descriptions of the state
    # BEFORE the current trade.
    # --------------------------------------------------------

    df["behavior_overtrading"] = (
        df["trades_today"]
        > 5
    ).astype(int)

    df["behavior_rapid_reentry"] = (
        (
            df["time_since_previous_trade"] >= 0
        )
        &
        (
            df["time_since_previous_trade"] <= 15
        )
    ).astype(int)

    df["behavior_oversizing"] = (
        df["position_size_ratio"]
        >= 2.0
    ).fillna(False).astype(int)

    df["behavior_loss_streak"] = (
        df["loss_streak"]
        >= 2
    ).astype(int)

    df["behavior_revenge"] = (
        (
            df["previous_trade_is_loss"] == 1
        )
        &
        (
            df["time_since_previous_trade"] >= 0
        )
        &
        (
            df["time_since_previous_trade"] <= 15
        )
        &
        (
            df["position_size_ratio"] >= 1.5
        )
    ).fillna(False).astype(int)

    # --------------------------------------------------------
    # TARGET
    # --------------------------------------------------------

    df["target"] = df["is_win"].astype(int)

    # --------------------------------------------------------
    # FEATURES
    #
    # ONLY information available before entry.
    # --------------------------------------------------------

    feature_columns = [

        # Market / trade context
        "symbol",
        "direction",

        # Time
        "entry_hour",
        "entry_minute",
        "day_of_week_num",

        # Trading activity
        "trades_today",

        # Previous trade
        "previous_trade_pnl",
        "previous_trade_is_loss",
        "previous_trade_is_win",
        "time_since_previous_trade",

        # Streaks
        "win_streak",
        "loss_streak",
        "previous_loss_streak",

        # Position behavior
        "previous_position_size",
        "position_size_change_pct",
        "average_position_size",
        "position_size_ratio",

        # Session state
        "previous_session_pnl",

        # Behavioral state
        "behavior_overtrading",
        "behavior_rapid_reentry",
        "behavior_oversizing",
        "behavior_loss_streak",
        "behavior_revenge",
    ]

    # --------------------------------------------------------
    # CHECK MISSING FEATURES
    # --------------------------------------------------------

    missing_columns = [
        col
        for col in feature_columns
        if col not in df.columns
    ]

    if missing_columns:

        raise ValueError(
            "Missing required feature columns: "
            + ", ".join(missing_columns)
        )

    # --------------------------------------------------------
    # BUILD DATASET
    # --------------------------------------------------------

    dataset_columns = [
        "trade_id",
        "account",
        "entry_time",
        "symbol",
        "direction",
        "target",
    ] + feature_columns

    dataset = df[
        dataset_columns
    ].copy()

    # --------------------------------------------------------
    # REMOVE CURRENT-TRADE INFORMATION
    #
    # Explicitly make sure these cannot leak.
    # --------------------------------------------------------

    forbidden_columns = [
        "net_pnl",
        "gross_pnl",
        "fees",
        "exit_time",
        "exit_price",
        "holding_minutes",
        "is_win",
        "is_loss",
        "is_breakeven",
        "session_pnl",
    ]

    forbidden_present = [
        col
        for col in forbidden_columns
        if col in dataset.columns
    ]

    if forbidden_present:

        dataset = dataset.drop(
            columns=forbidden_present,
            errors="ignore"
        )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    dataset.to_csv(
        OUTPUT_FILE,
        index=False
    )

    return dataset


# ============================================================
# SUMMARY
# ============================================================

def show_summary(dataset):

    print(
        "\n========== ML DATASET SUMMARY ==========\n"
    )

    print(
        f"Total records: {len(dataset):,}"
    )

    print(
        f"Total columns: {len(dataset.columns):,}"
    )

    print(
        f"Winning trades: "
        f"{dataset['target'].sum():,}"
    )

    print(
        f"Losing trades: "
        f"{(dataset['target'] == 0).sum():,}"
    )

    print("\nTarget distribution:\n")

    print(
        dataset["target"].value_counts()
    )

    print("\nFeature columns:\n")

    for column in dataset.columns:

        print(
            f"- {column}"
        )

    print(
        "\nSaved to:"
    )

    print(
        OUTPUT_FILE
    )

    print(
        "\n========================================\n"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n========== TRADEMIND AI ==========\n"
    )

    print(
        "Starting ML dataset preparation..."
    )

    df = load_features()

    dataset = prepare_dataset(
        df
    )

    show_summary(
        dataset
    )


if __name__ == "__main__":

    main()