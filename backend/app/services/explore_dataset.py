from .data_loader import load_trade_data


def explore_dataset():
    df = load_trade_data()

    print("\n========== TRADEMIND AI DATA EXPLORATION ==========\n")

    # 1. Direction distribution
    print("1. DIRECTION DISTRIBUTION")
    print("-" * 50)
    print(df["Direction"].value_counts())
    
    # 2. Side distribution
    print("\n2. SIDE DISTRIBUTION")
    print("-" * 50)
    print(df["Side"].value_counts())

    # 3. Accounts
    print("\n3. UNIQUE ACCOUNTS")
    print("-" * 50)
    print(f"Number of accounts: {df['Account'].nunique()}")

    # 4. Coins
    print("\n4. UNIQUE COINS")
    print("-" * 50)
    print(f"Number of coins: {df['Coin'].nunique()}")

    # 5. Closed PnL
    print("\n5. CLOSED PNL")
    print("-" * 50)

    pnl_zero = (df["Closed PnL"] == 0).sum()
    pnl_positive = (df["Closed PnL"] > 0).sum()
    pnl_negative = (df["Closed PnL"] < 0).sum()

    print(f"Zero PnL:     {pnl_zero:,}")
    print(f"Positive PnL: {pnl_positive:,}")
    print(f"Negative PnL: {pnl_negative:,}")

    # 6. Trade ID
    print("\n6. TRADE ID ANALYSIS")
    print("-" * 50)
    print(f"Unique Trade IDs: {df['Trade ID'].nunique():,}")

    # 7. Order ID
    print("\n7. ORDER ID ANALYSIS")
    print("-" * 50)
    print(f"Unique Order IDs: {df['Order ID'].nunique():,}")

    # 8. Sample records for each direction
    print("\n8. SAMPLE RECORDS BY DIRECTION")
    print("-" * 50)

    for direction in df["Direction"].unique():
        print(f"\n--- {direction} ---")
        
        sample = df[df["Direction"] == direction][
            [
                "Account",
                "Coin",
                "Execution Price",
                "Size Tokens",
                "Size USD",
                "Side",
                "Timestamp IST",
                "Start Position",
                "Direction",
                "Closed PnL",
                "Order ID",
                "Trade ID",
            ]
        ].head(3)

        print(sample.to_string(index=False))

    print("\n====================================================\n")


if __name__ == "__main__":
    explore_dataset()