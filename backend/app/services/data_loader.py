from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_PATH = PROJECT_ROOT / "data" / "historical_data.csv"


def load_trade_data() -> pd.DataFrame:
    """
    Load the raw historical trader dataset.

    Returns:
        pandas.DataFrame: Raw trade execution data.
    """

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found at: {DATA_PATH}"
        )

    df = pd.read_csv(DATA_PATH)

    return df