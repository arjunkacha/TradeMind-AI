import asyncio
import importlib
import httpx
from fastapi import FastAPI

module = importlib.import_module(
    "backend.app.routers.simulator_isolation_test"
)

app = FastAPI()
app.include_router(module.router)

async def main():
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        for path in [
            "/api/simulator/account",
            "/api/simulator/orders",
            "/api/simulator/positions",
            "/api/simulator/trades",
            "/api/simulator/journal",
        ]:
            response = await client.get(path)
            print(f"{path}: HTTP {response.status_code}")
            if response.status_code not in (401, 403):
                print("UNEXPECTED:", response.text[:300])

asyncio.run(main())
