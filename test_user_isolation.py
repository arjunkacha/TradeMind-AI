import asyncio
import sqlite3
import importlib
import httpx
from fastapi import FastAPI

module = importlib.import_module(
    "backend.app.routers.simulator_isolation_test"
)
db_path = module.DB_PATH

with sqlite3.connect(db_path) as conn:
    conn.execute("""
        INSERT OR IGNORE INTO users (id, email, password_hash, created_at)
        VALUES (2, 'isolation-test-2@example.com', 'test-only', '2026-10-12')
    """)
    conn.execute("""
        INSERT OR IGNORE INTO simulator_accounts (user_id, balance, currency)
        VALUES (2, 10000, 'USD')
    """)

app = FastAPI()
app.include_router(module.router)

active_user = {"id": 1, "email": "trademind.test@example.com"}

def fake_current_user():
    return active_user

app.dependency_overrides[module.current_user] = fake_current_user

async def main():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        endpoints = [
            "/api/simulator/account",
            "/api/simulator/orders",
            "/api/simulator/positions",
            "/api/simulator/trades",
            "/api/simulator/journal",
        ]

        for user_id in (1, 2):
            active_user["id"] = user_id
            active_user["email"] = (
                "trademind.test@example.com"
                if user_id == 1
                else "isolation-test-2@example.com"
            )

            print(f"\n--- USER {user_id} ---")
            for endpoint in endpoints:
                response = await client.get(endpoint)
                print(endpoint, "HTTP", response.status_code)

                if response.status_code != 200:
                    print("ERROR:", response.text[:500])
                    continue

                payload = response.json()
                if endpoint.endswith("/account"):
                    print("Account:", payload)
                elif isinstance(payload, list):
                    print("Returned records:", len(payload))
                elif isinstance(payload, dict):
                    records = next(
                        (v for v in payload.values() if isinstance(v, list)),
                        None
                    )
                    print(
                        "Returned records:" if records is not None
                        else "Response keys:",
                        len(records) if records is not None
                        else list(payload.keys())
                    )

asyncio.run(main())
