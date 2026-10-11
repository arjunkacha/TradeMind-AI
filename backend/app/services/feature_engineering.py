import pandas as pd
from pathlib import Path


# ============================================================
# TRADEMIND AI - FEATURE ENGINEERING
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[3]

INPUT_FILE = BASE_DIR / "data" / "processed_trades.csv"
OUTPUT_FILE = BASE_DIR / "data" / "trade_features.csv"


def load_trades():
    """Load reconstructed trades."""

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    print(f"Loaded trades: {len(df):,}")

    return df


def prepare_data(df):
    """Prepare timestamps and sort trades."""

    df["entry_time"] = pd.to_datetime(
        df["entry_time"]
    )

    df["exit_time"] = pd.to_datetime(
        df["exit_time"]
    )

    # Sort separately for each trader/account.
    # This is important because behavioral analysis
    # must be trader-specific.
    df = df.sort_values(
        by=["account", "entry_time", "exit_time"]
    ).reset_index(drop=True)

    return df


def add_basic_features(df):
    """Add basic trade outcome and time features."""

    # --------------------------------------------------------
    # Trade result
    # --------------------------------------------------------

    df["is_win"] = (
        df["net_pnl"] > 0
    ).astype(int)

    df["is_loss"] = (
        df["net_pnl"] < 0
    ).astype(int)

    df["is_breakeven"] = (
        df["net_pnl"] == 0
    ).astype(int)

    # --------------------------------------------------------
    # Date / time
    # --------------------------------------------------------

    df["trading_date"] = (
        df["entry_time"].dt.date
    )

    df["entry_hour"] = (
        df["entry_time"].dt.hour
    )

    df["entry_minute"] = (
        df["entry_time"].dt.minute
    )

    df["day_of_week"] = (
        df["entry_time"].dt.day_name()
    )

    df["day_of_week_num"] = (
        df["entry_time"].dt.dayofweek
    )

    # --------------------------------------------------------
    # Trading session
    # --------------------------------------------------------

    def classify_session(hour):

        if 0 <= hour < 6:
            return "Late Night"

        elif 6 <= hour < 12:
            return "Morning"

        elif 12 <= hour < 16:
            return "Afternoon"

        elif 16 <= hour < 20:
            return "Evening"

        else:
            return "Night"

    df["trading_session"] = (
        df["entry_hour"].apply(
            classify_session
        )
    )

    return df


def add_account_trade_sequence(df):
    """Create account-specific trade sequence."""

    # Number of previous trades for this account.
    df["trade_number"] = (
        df.groupby("account")
        .cumcount() + 1
    )

    # Number of trades on the same day.
    df["trades_today"] = (
        df.groupby(
            ["account", "trading_date"]
        ).cumcount() + 1
    )

    return df


def add_previous_trade_features(df):
    """
    Features based on the previous trade of
    the same account.
    """

    grouped = df.groupby("account")

    # --------------------------------------------------------
    # Previous P/L
    # --------------------------------------------------------

    df["previous_trade_pnl"] = (
        grouped["net_pnl"]
        .shift(1)
    )

    # --------------------------------------------------------
    # Previous trade result
    # --------------------------------------------------------

    df["previous_trade_is_loss"] = (
        grouped["is_loss"]
        .shift(1)
        .fillna(0)
        .astype(int)
    )

    df["previous_trade_is_win"] = (
        grouped["is_win"]
        .shift(1)
        .fillna(0)
        .astype(int)
    )

    # --------------------------------------------------------
    # Time since previous trade
    # --------------------------------------------------------

    previous_entry = (
        grouped["entry_time"]
        .shift(1)
    )

    df["time_since_previous_trade"] = (
        (
            df["entry_time"]
            - previous_entry
        )
        .dt.total_seconds()
        / 60
    )

    df["time_since_previous_trade"] = (
        df["time_since_previous_trade"]
        .fillna(-1)
    )

    return df


def add_streak_features(df):
    """
    Calculate consecutive winning and losing
    trade streaks for each account.
    """

    win_streaks = []
    loss_streaks = []

    current_account = None
    current_win_streak = 0
    current_loss_streak = 0

    for _, row in df.iterrows():

        account = row["account"]

        if account != current_account:

            current_account = account

            current_win_streak = 0
            current_loss_streak = 0

        if row["is_win"] == 1:

            current_win_streak += 1
            current_loss_streak = 0

        elif row["is_loss"] == 1:

            current_loss_streak += 1
            current_win_streak = 0

        else:

            current_win_streak = 0
            current_loss_streak = 0

        win_streaks.append(
            current_win_streak
        )

        loss_streaks.append(
            current_loss_streak
        )

    df["win_streak"] = win_streaks

    df["loss_streak"] = loss_streaks

    # Previous loss streak is useful for
    # revenge-trading detection.

    df["previous_loss_streak"] = (
        df.groupby("account")["loss_streak"]
        .shift(1)
        .fillna(0)
        .astype(int)
    )

    return df


def add_position_size_features(df):
    """
    Analyze position size relative to the trader's
    own historical behavior.
    """

    grouped = df.groupby("account")

    # --------------------------------------------------------
    # Previous position size
    # --------------------------------------------------------

    df["previous_position_size"] = (
        grouped["quantity"]
        .shift(1)
    )

    # --------------------------------------------------------
    # Position size change
    # --------------------------------------------------------

    df["position_size_change_pct"] = (
        (
            df["quantity"]
            - df["previous_position_size"]
        )
        / df["previous_position_size"].abs()
        * 100
    )

    df["position_size_change_pct"] = (
        df["position_size_change_pct"]
        .replace(
            [float("inf"), float("-inf")],
            pd.NA
        )
    )

    # --------------------------------------------------------
    # Rolling average position size
    # --------------------------------------------------------

    df["average_position_size"] = (
        grouped["quantity"]
        .transform(
            lambda x:
            x.shift(1)
            .rolling(
                window=20,
                min_periods=1
            )
            .mean()
        )
    )

    # --------------------------------------------------------
    # Position size relative to normal size
    # --------------------------------------------------------

    df["position_size_ratio"] = (
        df["quantity"]
        / df["average_position_size"]
    )

    return df


def add_session_pnl(df):
    """Calculate cumulative P/L during each trading day."""

    df["session_pnl"] = (
        df.groupby(
            ["account", "trading_date"]
        )["net_pnl"]
        .cumsum()
    )

    return df


def add_holding_features(df):
    """Add holding-time related features."""

    df["holding_hours"] = (
        df["holding_minutes"] / 60
    )

    df["holding_days"] = (
        df["holding_minutes"] / 1440
    )

    return df


def save_features(df):

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        f"\nSaved feature dataset to:"
    )

    print(
        OUTPUT_FILE
    )


def show_summary(df):

    print(
        "\n========== FEATURE ENGINEERING SUMMARY ==========\n"
    )

    print(
        f"Total trades: {len(df):,}"
    )

    print(
        f"Unique accounts: "
        f"{df['account'].nunique():,}"
    )

    print(
        f"Total features: "
        f"{len(df.columns):,}"
    )

    print("\nFeature columns:\n")

    for column in df.columns:

        print(
            f" - {column}"
        )

    print(
        "\nSample engineered data:\n"
    )

    columns_to_show = [
        "trade_id",
        "account",
        "symbol",
        "direction",
        "net_pnl",
        "is_win",
        "is_loss",
        "trading_date",
        "entry_hour",
        "trading_session",
        "trades_today",
        "previous_trade_pnl",
        "time_since_previous_trade",
        "loss_streak",
        "previous_loss_streak",
        "quantity",
        "position_size_change_pct",
        "position_size_ratio",
        "session_pnl",
    ]

    print(
        df[
            columns_to_show
        ].head(10).to_string(
            index=False
        )
    )

    print(
        "\n=================================================\n"
    )


def main():

    print(
        "\n========== TRADEMIND AI ==========\n"
    )

    print(
        "Starting feature engineering..."
    )

    df = load_trades()

    df = prepare_data(df)

    df = add_basic_features(df)

    df = add_account_trade_sequence(df)

    df = add_previous_trade_features(df)

    df = add_streak_features(df)

    df = add_position_size_features(df)

    df = add_session_pnl(df)

    df = add_holding_features(df)

    save_features(df)

    show_summary(df)


if __name__ == "__main__":
    main()