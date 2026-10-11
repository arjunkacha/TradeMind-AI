import hashlib
from io import BytesIO
from pathlib import Path

import pandas as pd


# ============================================================
# TRADEMIND AI
# TRADINGVIEW PAPER TRADING PARSER
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[4]

DATA_DIR = BASE_DIR / "data"

OUTPUT_FILE = DATA_DIR / "tradingview_trades.csv"


# ============================================================
# HELPERS
# ============================================================

def clean_number(value, default=0.0):
    """
    Convert TradingView numeric values safely.
    """

    try:
        if pd.isna(value):
            return default

        return float(
            str(value)
            .replace(",", "")
            .replace("%", "")
            .strip()
        )

    except (ValueError, TypeError):
        return default


def clean_symbol(symbol):
    """
    Preserve the TradingView symbol exactly.

    Example:
        OANDA:XAUUSD
    """

    return str(symbol).strip()


def generate_trade_id(
    symbol,
    trade_number,
    direction,
    entry_time,
    exit_time,
):
    """
    Generate a stable TradeMind ID.
    """

    raw = "|".join(
        [
            str(symbol),
            str(trade_number),
            str(direction),
            str(entry_time),
            str(exit_time),
        ]
    )

    digest = hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:12].upper()

    return f"TV-{digest}"


# ============================================================
# LOAD CSV
# ============================================================

def load_csv(file_bytes):
    """
    Read uploaded TradingView CSV.
    """

    try:
        df = pd.read_csv(
            BytesIO(file_bytes)
        )

    except Exception as exc:
        raise ValueError(
            f"Could not read TradingView CSV: {exc}"
        )

    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    return df


# ============================================================
# VALIDATE TRADE HISTORY
# ============================================================

def validate_trade_history(df):

    required_columns = {
        "Symbol",
        "Trade number",
        "Type",
        "Date and time",
        "Price",
        "Size (qty)",
        "Net PnL INR",
        "Commission INR",
    }

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:

        raise ValueError(
            "TradingView Trade History CSV is missing "
            f"required columns: {', '.join(missing)}"
        )


# ============================================================
# PARSE DATE
# ============================================================

def parse_datetime(value):

    try:

        return pd.to_datetime(
            value,
            errors="coerce",
        )

    except Exception:

        return pd.NaT


# ============================================================
# BUILD COMPLETED TRADES
# ============================================================

def build_trades(df, account):

    completed_trades = []

    # --------------------------------------------------------
    # Process each TradingView trade number
    # --------------------------------------------------------

    grouped = df.groupby(
        [
            "Symbol",
            "Trade number",
        ],
        sort=False,
    )

    for (
        symbol,
        trade_number,
    ), group in grouped:

        group = group.copy()

        # ----------------------------------------------------
        # Normalize type
        # ----------------------------------------------------

        group["Type"] = (
            group["Type"]
            .astype(str)
            .str.strip()
        )

        entry_rows = group[
            group["Type"].str.lower().str.startswith(
                "entry"
            )
        ]

        exit_rows = group[
            group["Type"].str.lower().str.startswith(
                "exit"
            )
        ]

        # ----------------------------------------------------
        # We need exactly one entry and one exit
        # ----------------------------------------------------

        if entry_rows.empty:
            continue

        if exit_rows.empty:
            continue

        entry = entry_rows.iloc[0]

        exit_trade = exit_rows.iloc[0]

        # ----------------------------------------------------
        # Direction
        # ----------------------------------------------------

        entry_type = str(
            entry["Type"]
        ).lower()

        if "long" in entry_type:

            direction = "LONG"

        elif "short" in entry_type:

            direction = "SHORT"

        else:

            continue

        # ----------------------------------------------------
        # Times
        # ----------------------------------------------------

        entry_time = parse_datetime(
            entry["Date and time"]
        )

        exit_time = parse_datetime(
            exit_trade["Date and time"]
        )

        if pd.isna(entry_time):
            continue

        if pd.isna(exit_time):
            continue

        # ----------------------------------------------------
        # Prices
        # ----------------------------------------------------

        entry_price = clean_number(
            entry["Price"]
        )

        exit_price = clean_number(
            exit_trade["Price"]
        )

        # ----------------------------------------------------
        # Quantity
        # ----------------------------------------------------

        quantity = clean_number(
            entry["Size (qty)"]
        )

        if quantity <= 0:
            continue

        # ----------------------------------------------------
        # P&L
        #
        # TradingView provides the completed trade's
        # Net PnL directly.
        # ----------------------------------------------------

        net_pnl = clean_number(
            exit_trade["Net PnL INR"]
        )

        # ----------------------------------------------------
        # Commission
        # ----------------------------------------------------

        entry_commission = clean_number(
            entry["Commission INR"]
        )

        exit_commission = clean_number(
            exit_trade["Commission INR"]
        )

        fees = (
            abs(entry_commission)
            + abs(exit_commission)
        )

        # ----------------------------------------------------
        # Gross P&L
        #
        # Since TradingView gives us Net PnL and fees,
        # reconstruct gross PnL.
        # ----------------------------------------------------

        gross_pnl = (
            net_pnl
            + fees
        )

        # ----------------------------------------------------
        # Holding time
        # ----------------------------------------------------

        holding_minutes = (
            exit_time
            - entry_time
        ).total_seconds() / 60

        # Prevent impossible negative duration
        if holding_minutes < 0:
            holding_minutes = 0.0

        # ----------------------------------------------------
        # Trade ID
        # ----------------------------------------------------

        trade_id = generate_trade_id(
            symbol,
            trade_number,
            direction,
            entry_time,
            exit_time,
        )

        # ----------------------------------------------------
        # Build normalized TradeMind record
        # ----------------------------------------------------

        trade = {

            "trade_id":
                trade_id,

            "account":
                account,

            "symbol":
                clean_symbol(symbol),

            "direction":
                direction,

            "entry_time":
                entry_time,

            "exit_time":
                exit_time,

            "entry_price":
                entry_price,

            "exit_price":
                exit_price,

            "quantity":
                quantity,

            "gross_pnl":
                gross_pnl,

            "fees":
                fees,

            "net_pnl":
                net_pnl,

            "holding_minutes":
                holding_minutes,
        }

        completed_trades.append(
            trade
        )

    # --------------------------------------------------------
    # DataFrame
    # --------------------------------------------------------

    result = pd.DataFrame(
        completed_trades
    )

    if result.empty:

        return pd.DataFrame(
            columns=[
                "trade_id",
                "account",
                "symbol",
                "direction",
                "entry_time",
                "exit_time",
                "entry_price",
                "exit_price",
                "quantity",
                "gross_pnl",
                "fees",
                "net_pnl",
                "holding_minutes",
            ]
        )

    # --------------------------------------------------------
    # Sort by entry time
    # --------------------------------------------------------

    result = result.sort_values(
        "entry_time"
    ).reset_index(
        drop=True
    )

    return result


# ============================================================
# PUBLIC PARSER
# ============================================================

def parse_tradingview_csv(
    file_bytes,
    account="TradingView-Paper",
):

    df = load_csv(
        file_bytes
    )

    validate_trade_history(
        df
    )

    trades = build_trades(
        df,
        account,
    )

    return trades


# ============================================================
# SAVE
# ============================================================

def save_trades(df):

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    return OUTPUT_FILE