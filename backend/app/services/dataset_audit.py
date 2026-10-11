from .data_loader import load_trade_data


def audit_dataset():
    df = load_trade_data()

    print("\n========== TRADEMIND AI DATASET AUDIT ==========\n")

    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns)}")

    print("\nColumns:")
    for column in df.columns:
        print(f"  - {column}")

    print("\nMissing Values:")
    print(df.isnull().sum())

    print("\nDuplicate Rows:")
    print(df.duplicated().sum())

    print("\nData Types:")
    print(df.dtypes)

    print("\nBasic Statistics:")
    print(df.describe(include="all").transpose())

    print("\n=================================================\n")


if __name__ == "__main__":
    audit_dataset()