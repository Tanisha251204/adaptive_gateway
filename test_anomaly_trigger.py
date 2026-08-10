import asyncio
import httpx


async def hammer_one_endpoint(client, n=25):
    # High volume, single endpoint, fired back-to-back --
    # deliberately matches the simulated bot pattern from Day 4.

    results = []

    for i in range(n):
        r = await client.get(
            "http://localhost:8000/service1/data"
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

        anomaly = await client.get(
            "http://localhost:8000/gateway/anomaly/127.0.0.1"
        )

        print("Anomaly check:", anomaly.json())


asyncio.run(main())