# Adaptive API Gateway

An API gateway that learns normal traffic patterns per client and dynamically tightens rate limits for clients whose behavior looks anomalous — instead of applying one fixed limit to everyone.

## Live Demo

- **Gateway:** https://adaptive-gateway-1.onrender.com/gateway/health
- **Dashboard:** https://adaptivegateway-rpgqqk9rircptogalgvpcg.streamlit.app

> Note: backend services run on Render's free tier and spin down after 15 minutes of inactivity — the first request after a period of idle time may take 30–60 seconds to respond while the service wakes up.

## Screenshots

<img width="1920" height="475" alt="image" src="https://github.com/user-attachments/assets/6573d7ca-3e55-4d04-adfd-99d58e9fa1e5" />

*The gateway's health endpoint confirming the service is live.*


<img width="1876" height="862" alt="image" src="https://github.com/user-attachments/assets/87a82e8d-d8f5-464f-a754-15e5fc317266" />

*A client flagged as anomalous after a simulated burst of high-volume, single-endpoint traffic, shown with a red-highlighted row.*

## Architecture

```
Client → [Gateway] → routes to → [Backend 1] / [Backend 2]
              |
              +--> Redis (atomic rate limiting + traffic feature tracking)
              +--> Isolation Forest model (live anomaly scoring)
              |
[Streamlit Dashboard] --> reads Redis directly for live observability
```

## Key Results

- **100% recall, 9% false-positive rate** detecting simulated abusive traffic — Isolation Forest trained on 800 simulated normal + 100 simulated abusive traffic samples, using request rate, endpoint diversity, and timing burstiness as features.
- **~30 RPS sustained at 50 concurrent clients** under Locust load testing, with correct rate-limiting behavior (429s) under contention — verified with a dedicated concurrency test proving the Redis Lua script prevents race conditions under simultaneous requests.
- **Found and fixed two real performance bottlenecks** during load testing: redundant sequential Redis round trips (fixed via pipelining) and synchronous ML inference blocking the async event loop under concurrency (fixed via `asyncio.to_thread`).

## Tech Stack

FastAPI · Redis (Upstash) · scikit-learn (Isolation Forest) · httpx · Streamlit · Locust · Render

## How It Works

1. A request hits the gateway and is routed to the correct backend based on a path prefix (`/service1/*`, `/service2/*`).
2. The request is logged into Redis, tracking per-client request timestamps and endpoint diversity in a rolling 60-second window.
3. The client's recent traffic is scored against a trained Isolation Forest model.
4. If the client looks anomalous, their rate limit bucket is tightened (lower capacity, slower refill) instead of being blocked outright — a deliberate trade-off given the model's measured 9% false-positive rate.
5. The rate limit check itself runs as an atomic Redis Lua script, eliminating the check-then-act race condition a naive implementation would have under concurrent requests.
6. Allowed requests are proxied to the real backend; rejected ones get a `429` with a `Retry-After` header.

## Local Setup

```bash
pip install -r requirements.txt

# Terminal 1
python -m uvicorn backend1.main:app --port 8001

# Terminal 2
python -m uvicorn backend2.main:app --port 8002

# Terminal 3
python -m uvicorn gateway.main:app --port 8000

# Terminal 4 (optional dashboard)
streamlit run dashboard.py
```

Requires a Redis instance reachable via the `REDIS_URL` environment variable (see `.env.example`).

To retrain the anomaly detection model:
```bash
python ml/train_model.py
```

## What I'd Build Next

- A service registry instead of the hardcoded `SERVICE_MAP`, to scale past two backends
- A circuit breaker for backend failures
- A smoother throttling curve based on the continuous anomaly score, instead of the current two-tier normal/anomalous split
- Periodic retraining on real (labeled) production traffic instead of only simulated data
