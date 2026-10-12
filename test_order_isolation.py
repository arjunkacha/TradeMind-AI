import asyncio
import importlib
import httpx
from fastapi import FastAPI

module = importlib.import_module(
    "backend.app.routers.simulator_isolation_test"
)

# Use a fake quote so the test does not depend on a live market-data provider.
module.quote = lambda symbol, require_fresh=False: {
    "stale": False,
    "market_state": "open",
    "bid": 100.0,
    "ask": 101.0
}

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

        response = await client.post(
            "/api/simulator/orders",
            json={
                "symbol": "BTCUSD",
                "side": "BUY",
                "order_type": "LIMIT",
                "quantity": 0.01,
                "price": 50000
            }
        )

        print("Create order status:", response.status_code)
        print("Create order response:", response.text[:500])

        if response.status_code not in (200, 201):
            print("STOP: Order creation failed; inspect the error above.")
            return

        order = response.json()
        order_id = order.get("order_id")
        print("Created test order:", order_id)

        for user_id in (2, 1):
            active_user["id"] = user_id
            active_user["email"] = (
                "isolation-test-2@example.com"
                if user_id == 2
                else "trademind.test@example.com"
            )

            response = await client.get("/api/simulator/orders")
            print(f"\nUser {user_id} GET orders:", response.status_code)

            if response.status_code != 200:
                print(response.text[:500])
                continue

            payload = response.json()
            rows = payload if isinstance(payload, list) else payload.get("orders", [])
            visible_ids = [row.get("order_id") for row in rows]
            print("Visible order count:", len(rows))
            print("Can see newly created order:", order_id in visible_ids)

asyncio.run(main())
