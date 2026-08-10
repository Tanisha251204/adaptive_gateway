import os
import time
import redis.asyncio as redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# Connects to Memurai/Redis running on localhost:6379.
# decode_responses=True means Redis returns Python strings,
# not raw bytes -- simpler to work with.
redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)

# This Lua script is the core of the whole day. It runs entirely
# INSIDE Redis, atomically -- no other request can interleave
# partway through it, which is what eliminates the race condition.
TOKEN_BUCKET_SCRIPT = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])

local bucket = redis.call("HMGET", key, "tokens", "last_refill")
local tokens = tonumber(bucket[1])
local last_refill = tonumber(bucket[2])

-- First request ever for this client: start with a full bucket.
if tokens == nil then
    tokens = capacity
    last_refill = now
end

-- Refill based on how much time has passed since we last touched this bucket.
local elapsed = math.max(0, now - last_refill)
local refilled = elapsed * refill_rate

tokens = math.min(capacity, tokens + refilled)

local allowed = 0

if tokens >= requested then
    tokens = tokens - requested
    allowed = 1
end

redis.call("HMSET", key, "tokens", tokens, "last_refill", now)
redis.call("EXPIRE", key, 3600)

return allowed
"""

# register_script compiles the Lua script once and gives back a
# callable -- avoids re-sending the script text on every request.
rate_limit_script = redis_client.register_script(TOKEN_BUCKET_SCRIPT)


async def is_allowed(
    client_id: str,
    capacity: int = 10,
    refill_rate: float = 1.0
) -> bool:
    key = f"ratelimit:{client_id}"
    now = time.time()

    result = await rate_limit_script(
        keys=[key],
        args=[capacity, refill_rate, now, 1]
    )

    return result == 1