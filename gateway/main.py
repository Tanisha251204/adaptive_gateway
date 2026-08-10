from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from gateway.rate_limiter import is_allowed
from gateway.feature_logger import log_request, get_features
from gateway.anomaly_scorer import score_client
import httpx
import os

app = FastAPI(title="Adaptive API Gateway")

# Map the path prefixes to backend service URLs.
# Running locally without Docker, so these point to localhost + port,
# not Docker service names.

SERVICE_MAP = {
    "service1": os.getenv("BACKEND1_URL", "http://127.0.0.1:8001"),
    "service2": os.getenv("BACKEND2_URL", "http://127.0.0.1:8002"),
}

# One shared async client for the whole app, reused across requests
# instead of opening a new TCP connection per request.

client = httpx.AsyncClient(timeout=5.0)


@app.on_event("shutdown")
async def shutdown_event():
    await client.aclose()


# IMPORTANT: these routes must be registered BEFORE the catch-all
# proxy route below, otherwise the catch-all swallows these paths too.

@app.get("/gateway/health")
async def gateway_health():
    return {
        "status": "ok",
        "service": "gateway"
    }


@app.get("/gateway/features/{client_id}")
async def gateway_features(client_id: str):
    return await get_features(client_id)


@app.get("/gateway/anomaly/{client_id}")
async def gateway_anomaly(client_id: str):
    return await score_client(client_id)


@app.api_route(
    "/{service_name}/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE"]
)
async def proxy_request(
    service_name: str,
    path: str,
    request: Request
):
    if service_name not in SERVICE_MAP:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown service: {service_name}"
        )

    # Identify the client by IP address.
    client_id = request.client.host

    await log_request(client_id, f"{service_name}/{path}")

    # Score the client's live traffic against the trained model,
    # then adjust the rate limit bucket based on how anomalous
    # they look, instead of using a fixed limit for everyone.
    anomaly_result = await score_client(client_id)

    if anomaly_result["is_anomaly"]:
        # Tighter bucket for clients whose traffic looks abnormal --
        # throttled harder, not blocked outright.
        capacity, refill_rate = 2, 0.2
    else:
        capacity, refill_rate = 10, 1.0

    allowed = await is_allowed(
        client_id,
        capacity=capacity,
        refill_rate=refill_rate
    )

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please slow down.",
            headers={"Retry-After": "1"}
        )

    target_url = f"{SERVICE_MAP[service_name]}/{path}"

    body = await request.body()

    try:
        response = await client.request(
            method=request.method,
            url=target_url,
            headers={
                k: v
                for k, v in request.headers.items()
                if k.lower() != "host"
            },
            content=body,
        )

    except httpx.ConnectError:
        raise HTTPException(
            status_code=502,
            detail=f"{service_name} is unreachable"
        )

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail=f"{service_name} timed out"
        )

    return JSONResponse(
        content=response.json(),
        status_code=response.status_code
    )