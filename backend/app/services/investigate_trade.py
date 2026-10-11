from pathlib import Path
import pandas as pd

from .data_loader import load_trade_data


ACCOUNT = "0x3998f134d6aaa2b6a5f723806d00fd2bbbbce891"
COIN = "ETH"


def investigate():

    df = load_trade_data()

    print("\n========== TRADEMIND AI TRADE INVESTIGATION ==========\n")

    print(f"Account : {ACCOUNT}")
    print(f"Coin    : {COIN}")

    # Filter account + coin
    filtered = df[
        (df["Account"] == ACCOUNT) &
        (df["Coin"] == COIN)
    ].copy()

    # Convert timestamp
    filtered["Timestamp IST"] = pd.to_datetime(
        filtered["Timestamp IST"],
        format="%d-%m-%Y %H:%M"
    )

    filtered = filtered.sort_values(
        "Timestamp IST"
    )

    print(
        f"\nTotal raw executions for this "
        f"Account + Coin: {len(filtered):,}"
    )

    print("\nDirection distribution:")
    print(
        filtered["Direction"].value_counts()
    )

    print("\nAll executions:\n")

    columns = [
        "Timestamp IST",
        "Direction",
        "Side",
        "Execution Price",
        "Size Tokens",
        "Start Position",
        "Closed PnL",
        "Fee",
        "Order ID",
        "Trade ID",
    ]

    print(
        filtered[columns].to_string(
            index=False
        )
    )

    print(
        "\n====================================================\n"
    )


if __name__ == "__main__":
    investigate()