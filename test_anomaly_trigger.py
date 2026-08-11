import asyncio
import httpx

GATEWAY_URL = "https://adaptive-gateway-1.onrender.com"


async def hammer_one_endpoint(client, n=25):
    # High volume, single endpoint, fired back-to-back --
    # deliberately matches the simulated bot pattern from Day 4.

    results = []

    for i in range(n):
        r = await client.get(
            f"{GATEWAY_URL}/service1/data"
        )

        results.append(r.status_code)

    return results


async def main():
    async with httpx.AsyncClient() as client:
        results = await hammer_one_endpoint(
            client,
            n=25
        )

        print("Status codes:", results)


asyncio.run(main())