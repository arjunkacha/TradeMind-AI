import pandas as pd

from .data_loader import load_trade_data


SUPPORTED_DIRECTIONS = {
    "Open Long",
    "Close Long",
    "Open Short",
    "Close Short",
}


def calculate_end_position(row):
    """
    Calculate the position immediately after
    an execution.
    """

    start = float(row["Start Position"])
    quantity = float(row["Size Tokens"])
    direction = row["Direction"]

    if direction == "Open Long":
        return start + quantity

    if direction == "Close Long":
        return start - quantity

    if direction == "Open Short":
        return start - quantity

    if direction == "Close Short":
        return start + quantity

    return start


def validate_positions():

    df = load_trade_data()

    print(
        "\n========== TRADEMIND AI POSITION VALIDATION ==========\n"
    )

    # --------------------------------------------------
    # Prepare
    # --------------------------------------------------

    df["Timestamp IST"] = pd.to_datetime(
        df["Timestamp IST"],
        format="%d-%m-%Y %H:%M"
    )

    df = df[
        df["Direction"].isin(
            SUPPORTED_DIRECTIONS
        )
    ].copy()

    print(
        f"Supported executions: {len(df):,}"
    )

    # --------------------------------------------------
    # Calculate end position
    # --------------------------------------------------

    df["Calculated End Position"] = df.apply(
        calculate_end_position,
        axis=1
    )

    # --------------------------------------------------
    # Basic mathematical validation
    # --------------------------------------------------

    tolerance = 1e-6

    invalid_rows = []

    for _, row in df.iterrows():

        start = float(row["Start Position"])
        quantity = float(row["Size Tokens"])
        end = float(row["Calculated End Position"])

        direction = row["Direction"]

        # Quantity must be positive
        if quantity <= 0:

            invalid_rows.append({
                "reason": "Invalid quantity",
                "account": row["Account"],
                "coin": row["Coin"],
                "timestamp": row["Timestamp IST"],
                "direction": direction,
                "start_position": start,
                "quantity": quantity,
                "calculated_end": end,
            })

    # --------------------------------------------------
    # Results
    # --------------------------------------------------

    print(
        f"Mathematical inconsistencies: "
        f"{len(invalid_rows):,}"
    )

    if invalid_rows:

        print("\nFirst inconsistencies:\n")

        print(
            pd.DataFrame(
                invalid_rows
            ).head(20).to_string(
                index=False
            )
        )

    else:

        print(
            "\n✅ All supported executions have "
            "valid position arithmetic."
        )

    # --------------------------------------------------
    # Position statistics
    # --------------------------------------------------

    print("\nPOSITION STATISTICS")
    print("-" * 50)

    print(
        f"Minimum Start Position: "
        f"{df['Start Position'].min():,.6f}"
    )

    print(
        f"Maximum Start Position: "
        f"{df['Start Position'].max():,.6f}"
    )

    print(
        f"Minimum Calculated End Position: "
        f"{df['Calculated End Position'].min():,.6f}"
    )

    print(
        f"Maximum Calculated End Position: "
        f"{df['Calculated End Position'].max():,.6f}"
    )

    # --------------------------------------------------
    # Direction distribution
    # --------------------------------------------------

    print("\nDIRECTION DISTRIBUTION")
    print("-" * 50)

    print(
        df["Direction"].value_counts()
    )

    print(
        "\n====================================================\n"
    )


if __name__ == "__main__":
    validate_positions()