import pandas as pd
from .data_loader import load_trade_data


def inspect_position():
    df = load_trade_data()

    df["Timestamp IST"] = pd.to_datetime(
        df["Timestamp IST"],
        format="%d-%m-%Y %H:%M"
    )

    account = "0xae5eacaf9c6b9111fd53034a602c192a04e082ed"
    coin = "AAVE"

    position = df[
        (df["Account"] == account)
        & (df["Coin"] == coin)
        & (
            df["Direction"].isin(
                ["Open Long", "Close Long"]
            )
        )
    ].sort_values("Timestamp IST")

    columns = [
        "Timestamp IST",
        "Direction",
        "Side",
        "Execution Price",
        "Size Tokens",
        "Size USD",
        "Start Position",
        "Closed PnL",
        "Order ID",
        "Trade ID",
    ]

    print("\n========== POSITION INSPECTION ==========\n")
    print(position[columns].head(100).to_string(index=False))
    print("\n==========================================\n")


if __name__ == "__main__":
    inspect_position()