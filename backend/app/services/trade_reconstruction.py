import pandas as pd
from pathlib import Path

from .data_loader import load_trade_data


OPEN_LONG = "Open Long"
CLOSE_LONG = "Close Long"
OPEN_SHORT = "Open Short"
CLOSE_SHORT = "Close Short"

SUPPORTED_DIRECTIONS = {
    OPEN_LONG,
    CLOSE_LONG,
    OPEN_SHORT,
    CLOSE_SHORT,
}


def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare raw execution data for trade reconstruction.
    """

    df = df.copy()

    # Convert timestamp from string to datetime
    df["Timestamp IST"] = pd.to_datetime(
        df["Timestamp IST"],
        format="%d-%m-%Y %H:%M"
    )

    # Keep only standard futures position activity
    df = df[
        df["Direction"].isin(SUPPORTED_DIRECTIONS)
    ].copy()

    # Process executions chronologically
    df = df.sort_values(
        ["Account", "Coin", "Timestamp IST", "Order ID"]
    ).reset_index(drop=True)

    return df


def reconstruct_trades(df: pd.DataFrame) -> pd.DataFrame:
    """
    Reconstruct completed position-level trades from
    individual execution records.

    Version 1 supports:
        Open Long
        Close Long
        Open Short
        Close Short
    """

    trades = []

    # Position state for each Account + Coin
    positions = {}

    for _, row in df.iterrows():

        account = row["Account"]
        coin = row["Coin"]
        direction = row["Direction"]

        key = (account, coin)

        if key not in positions:
            positions[key] = {
                "direction": None,
                "entry_time": None,
                "entry_quantity": 0.0,
                "entry_value": 0.0,
                "exit_quantity": 0.0,
                "exit_value": 0.0,
                "gross_pnl": 0.0,
                "fees": 0.0,
            }

        position = positions[key]

        quantity = float(row["Size Tokens"])
        price = float(row["Execution Price"])
        closed_pnl = float(row["Closed PnL"])
        fee = float(row["Fee"])
        timestamp = row["Timestamp IST"]

        # ==================================================
        # OPEN LONG
        # ==================================================

        if direction == OPEN_LONG:

            # Start a new long position
            if position["direction"] is None:

                position["direction"] = "LONG"
                position["entry_time"] = timestamp
                position["entry_quantity"] = 0.0
                position["entry_value"] = 0.0
                position["exit_quantity"] = 0.0
                position["exit_value"] = 0.0
                position["gross_pnl"] = 0.0
                position["fees"] = 0.0

            # Add execution to the long position
            if position["direction"] == "LONG":

                position["entry_quantity"] += quantity
                position["entry_value"] += quantity * price
                position["fees"] += fee

        # ==================================================
        # OPEN SHORT
        # ==================================================

        elif direction == OPEN_SHORT:

            if position["direction"] is None:

                position["direction"] = "SHORT"
                position["entry_time"] = timestamp
                position["entry_quantity"] = 0.0
                position["entry_value"] = 0.0
                position["exit_quantity"] = 0.0
                position["exit_value"] = 0.0
                position["gross_pnl"] = 0.0
                position["fees"] = 0.0

            if position["direction"] == "SHORT":

                position["entry_quantity"] += quantity
                position["entry_value"] += quantity * price
                position["fees"] += fee

        # ==================================================
        # CLOSE LONG
        # ==================================================

        elif direction == CLOSE_LONG:

            if position["direction"] != "LONG":
                continue

            position["exit_quantity"] += quantity
            position["exit_value"] += quantity * price
            position["gross_pnl"] += closed_pnl
            position["fees"] += fee

            # Position completely closed
            if (
                position["entry_quantity"] > 0
                and position["exit_quantity"]
                >= position["entry_quantity"] - 1e-8
            ):

                entry_price = (
                    position["entry_value"]
                    / position["entry_quantity"]
                )

                exit_price = (
                    position["exit_value"]
                    / position["exit_quantity"]
                )

                net_pnl = (
                    position["gross_pnl"]
                    - position["fees"]
                )

                trades.append({
                    "account": account,
                    "symbol": coin,
                    "direction": "LONG",
                    "entry_time": position["entry_time"],
                    "exit_time": timestamp,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "quantity": position["entry_quantity"],
                    "gross_pnl": position["gross_pnl"],
                    "fees": position["fees"],
                    "net_pnl": net_pnl,
                })

                # Reset position
                positions[key] = {
                    "direction": None,
                    "entry_time": None,
                    "entry_quantity": 0.0,
                    "entry_value": 0.0,
                    "exit_quantity": 0.0,
                    "exit_value": 0.0,
                    "gross_pnl": 0.0,
                    "fees": 0.0,
                }

        # ==================================================
        # CLOSE SHORT
        # ==================================================

        elif direction == CLOSE_SHORT:

            if position["direction"] != "SHORT":
                continue

            position["exit_quantity"] += quantity
            position["exit_value"] += quantity * price
            position["gross_pnl"] += closed_pnl
            position["fees"] += fee

            # Position completely closed
            if (
                position["entry_quantity"] > 0
                and position["exit_quantity"]
                >= position["entry_quantity"] - 1e-8
            ):

                entry_price = (
                    position["entry_value"]
                    / position["entry_quantity"]
                )

                exit_price = (
                    position["exit_value"]
                    / position["exit_quantity"]
                )

                net_pnl = (
                    position["gross_pnl"]
                    - position["fees"]
                )

                trades.append({
                    "account": account,
                    "symbol": coin,
                    "direction": "SHORT",
                    "entry_time": position["entry_time"],
                    "exit_time": timestamp,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "quantity": position["entry_quantity"],
                    "gross_pnl": position["gross_pnl"],
                    "fees": position["fees"],
                    "net_pnl": net_pnl,
                })

                # Reset position
                positions[key] = {
                    "direction": None,
                    "entry_time": None,
                    "entry_quantity": 0.0,
                    "entry_value": 0.0,
                    "exit_quantity": 0.0,
                    "exit_value": 0.0,
                    "gross_pnl": 0.0,
                    "fees": 0.0,
                }

    return pd.DataFrame(trades)


def main():
    print("\n========== TRADEMIND AI ==========")
    print("Starting trade reconstruction...\n")

    raw_df = load_trade_data()

    print(f"Raw executions: {len(raw_df):,}")

    prepared_df = prepare_data(raw_df)

    print(
        f"Supported executions: "
        f"{len(prepared_df):,}"
    )

    trades_df = reconstruct_trades(prepared_df)

    print(
        f"Completed trades reconstructed: "
        f"{len(trades_df):,}"
    )

    if len(trades_df) > 0:

        trades_df.insert(
            0,
            "trade_id",
            [
                f"TM-{i:06d}"
                for i in range(1, len(trades_df) + 1)
            ]
        )

        # Holding duration
        trades_df["holding_minutes"] = (
            trades_df["exit_time"]
            - trades_df["entry_time"]
        ).dt.total_seconds() / 60

        # Save reconstructed trades
        project_root = Path(__file__).resolve().parents[3]
        output_path = project_root / "data" / "processed_trades.csv"

        trades_df.to_csv(
            output_path,
            index=False
        )

        print("\nSample reconstructed trades:\n")

        print(
            trades_df.head(10).to_string(
                index=False
            )
        )

        print(
            f"\nSaved to: {output_path}"
        )

    print("\n==================================\n")


if __name__ == "__main__":
    main()