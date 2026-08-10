import time
import statistics

from gateway.rate_limiter import redis_client


WINDOW_SECONDS = 60

async def log_request(client_id: str, path: str):
    now = time.time()
    ts_key = f"traffic:timestamps:{client_id}"
    ep_key = f"traffic:endpoints:{client_id}"
    cutoff = now - WINDOW_SECONDS

    pipe = redis_client.pipeline(transaction=False)
    pipe.zadd(ts_key, {str(now): now})
    pipe.zremrangebyscore(ts_key, 0, cutoff)
    pipe.sadd(ep_key, path)
    pipe.expire(ts_key, WINDOW_SECONDS * 2)
    pipe.expire(ep_key, WINDOW_SECONDS * 2)
    await pipe.execute()


async def get_features(client_id: str) -> dict:
    now = time.time()
    ts_key = f"traffic:timestamps:{client_id}"
    ep_key = f"traffic:endpoints:{client_id}"
    cutoff = now - WINDOW_SECONDS

    pipe = redis_client.pipeline(transaction=False)
    pipe.zcount(ts_key, cutoff, now)
    pipe.scard(ep_key)
    pipe.zrangebyscore(ts_key, cutoff, now)
    request_count, endpoint_diversity, raw_timestamps = await pipe.execute()

    timestamps = sorted(float(t) for t in raw_timestamps)
    burstiness = 0.0
    if len(timestamps) >= 3:
        gaps = [timestamps[i] - timestamps[i - 1] for i in range(1, len(timestamps))]
        burstiness = statistics.pstdev(gaps)

    return {
        "client_id": client_id,
        "request_count_60s": request_count,
        "endpoint_diversity": endpoint_diversity,
        "burstiness": round(burstiness, 4),
    }