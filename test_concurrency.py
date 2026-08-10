import asyncio
import httpx


async def fire_request(client, i):
    r = await client.get(
        "http://localhost:8000/service1/data"
    )
    return r.status_code


async def main():
    async with httpx.AsyncClient() as client:
        # Fire 30 requests at the gateway all at once, from the
        # same client identity, against a bucket capacity of 10.
        tasks = [
            fire_request(client, i)
            for i in range(30)
        ]
        results = await asyncio.gather(*tasks)

        allowed = results.count(200)
        rejected = results.count(429)
        print(f"Allowed: {allowed}, Rejected: {rejected}")

        # With a capacity of 10, no more than 10 (or maybe 11 depending
        # on refill during the burst) should ever be allowed.
        assert allowed <= 11, (
            "Rate limiter allowed too many requests -- "
            "race condition present!"
        )


asyncio.run(main())