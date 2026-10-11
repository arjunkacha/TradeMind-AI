from pathlib import Path
import pandas as pd


def load_processed_trades():
    project_root = Path(__file__).resolve().parents[3]

    path = project_root / "data" / "processed_trades.csv"

    if not path.exists():
        raise FileNotFoundError(
            f"Processed trades not found: {path}"
        )

    return pd.read_csv(path)


def validate_trades():

    df = load_processed_trades()

    print("\n========== TRADEMIND AI TRADE VALIDATION ==========\n")

    print(f"Total reconstructed trades: {len(df):,}")

    # --------------------------------------------------
    # Basic validation
    # --------------------------------------------------

    print("\n1. MISSING VALUES")
    print("-" * 50)

    print(df.isnull().sum())

    # --------------------------------------------------
    # Duplicate trade IDs
    # --------------------------------------------------

    print("\n2. DUPLICATE TRADE IDs")
    print("-" * 50)

    print(
        df["trade_id"].duplicated().sum()
    )

    # --------------------------------------------------
    # Direction distribution
    # --------------------------------------------------

    print("\n3. LONG / SHORT DISTRIBUTION")
    print("-" * 50)

    print(
        df["direction"].value_counts()
    )

    # --------------------------------------------------
    # P/L analysis
    # --------------------------------------------------

    print("\n4. PROFIT / LOSS")
    print("-" * 50)

    winning = (df["net_pnl"] > 0).sum()
    losing = (df["net_pnl"] < 0).sum()
    breakeven = (df["net_pnl"] == 0).sum()

    print(f"Winning trades : {winning:,}")
    print(f"Losing trades  : {losing:,}")
    print(f"Breakeven      : {breakeven:,}")

    if len(df) > 0:
        print(
            f"Win rate       : "
            f"{winning / len(df) * 100:.2f}%"
        )

    # --------------------------------------------------
    # P/L totals
    # --------------------------------------------------

    print("\n5. P/L SUMMARY")
    print("-" * 50)

    print(
        f"Gross P/L : {df['gross_pnl'].sum():,.2f}"
    )

    print(
        f"Fees      : {df['fees'].sum():,.2f}"
    )

    print(
        f"Net P/L   : {df['net_pnl'].sum():,.2f}"
    )

    # --------------------------------------------------
    # Holding time
    # --------------------------------------------------

    print("\n6. HOLDING TIME")
    print("-" * 50)

    print(
        f"Minimum : {df['holding_minutes'].min():,.2f} minutes"
    )

    print(
        f"Average : {df['holding_minutes'].mean():,.2f} minutes"
    )

    print(
        f"Maximum : {df['holding_minutes'].max():,.2f} minutes"
    )

    # --------------------------------------------------
    # Negative holding time
    # --------------------------------------------------

    print("\n7. INVALID HOLDING TIMES")
    print("-" * 50)

    invalid_time = (
        df["holding_minutes"] < 0
    ).sum()

    print(
        f"Negative holding times: {invalid_time:,}"
    )

    # --------------------------------------------------
    # Negative quantities
    # --------------------------------------------------

    print("\n8. INVALID QUANTITIES")
    print("-" * 50)

    invalid_quantity = (
        df["quantity"] <= 0
    ).sum()

    print(
        f"Invalid quantities: {invalid_quantity:,}"
    )

    # --------------------------------------------------
    # Extremely long trades
    # --------------------------------------------------

    print("\n9. LONGEST TRADES")
    print("-" * 50)

    longest = df.nlargest(
        10,
        "holding_minutes"
    )[
        [
            "trade_id",
            "account",
            "symbol",
            "direction",
            "entry_time",
            "exit_time",
            "quantity",
            "net_pnl",
            "holding_minutes",
        ]
    ]

    print(
        longest.to_string(index=False)
    )

    # --------------------------------------------------
    # Largest P/L
    # --------------------------------------------------

    print("\n10. LARGEST WINNING TRADES")
    print("-" * 50)

    largest_wins = df.nlargest(
        10,
        "net_pnl"
    )[
        [
            "trade_id",
            "symbol",
            "direction",
            "quantity",
            "net_pnl",
            "holding_minutes",
        ]
    ]

    print(
        largest_wins.to_string(index=False)
    )

    print(
        "\n====================================================\n"
    )


if __name__ == "__main__":
    validate_trades()