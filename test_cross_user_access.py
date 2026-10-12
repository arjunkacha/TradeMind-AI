import asyncio
import sqlite3
import importlib
import httpx
from fastapi import FastAPI

module = importlib.import_module(
    "backend.app.routers.simulator_isolation_test"
)

with sqlite3.connect(module.DB_PATH) as conn:
    journal_row = conn.execute("""
        SELECT trade_id FROM auto_journal
        WHERE user_id = 1 LIMIT 1
    """).fetchone()

    position_row = conn.execute("""
        SELECT position_id FROM positions
        WHERE user_id = 1 LIMIT 1
    """).fetchone()

if not journal_row or not position_row:
    raise SystemExit("Required User 1 test records were not found.")

trade_id = journal_row[0]
position_id = position_row[0]

app = FastAPI()
app.include_router(module.router)

active_user = {"id": 2, "email": "isolation-test-2@example.com"}

def fake_current_user():
    return active_user

app.dependency_overrides[module.current_user] = fake_current_user

async def main():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        response = await client.get(f"/api/simulator/journal/{trade_id}")
        print("User 2 accessing User 1 journal:", response.status_code)
        print("Response:", response.text[:300])

        response = await client.put(
            f"/api/simulator/positions/{position_id}/protection",
            json={"stop_loss": 90, "take_profit": 120}
        )
        print("User 2 modifying User 1 position:", response.status_code)
        print("Response:", response.text[:300])

asyncio.run(main())
