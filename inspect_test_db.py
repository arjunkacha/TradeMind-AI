import sqlite3
from pathlib import Path

db = Path("data/simulator_migration_test.db")
con = sqlite3.connect(db)
cur = con.cursor()

print("\nDATABASE:", db.resolve())
print("\nTABLES:")
cur.execute("""
    SELECT name FROM sqlite_master
    WHERE type='table' ORDER BY name
""")
tables = [row[0] for row in cur.fetchall()]
print(tables)

for table in ["users", "simulator_accounts", "account", "orders",
              "positions", "trades", "auto_journal"]:
    if table not in tables:
        print(f"\n{table}: MISSING")
        continue

    cur.execute(f'PRAGMA table_info("{table}")')
    columns = [row[1] for row in cur.fetchall()]
    cur.execute(f'SELECT COUNT(*) FROM "{table}"')
    count = cur.fetchone()[0]

    print(f"\n{table}: {count} rows")
    print("Columns:", columns)

    if table == "simulator_accounts":
        cur.execute("SELECT user_id, balance, currency FROM simulator_accounts")
        print("Accounts:", cur.fetchall())
    elif table in ["orders", "positions", "trades", "auto_journal"] and "user_id" in columns:
        cur.execute(f'SELECT user_id, COUNT(*) FROM "{table}" GROUP BY user_id')
        print("Rows by user:", cur.fetchall())

con.close()
