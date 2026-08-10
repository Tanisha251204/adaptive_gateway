import time
import statistics
import redis
import joblib
import pandas as pd
import streamlit as st
import os 


# Synchronous client -- fine here since this isn't on the
# gateway's request-handling hot path (see Part 1.4).

import os
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

model = joblib.load("models/anomaly_model.pkl")

WINDOW_SECONDS = 60


st.set_page_config(
    page_title="Adaptive Gateway Dashboard",
    layout="wide"
)

st.title("Adaptive API Gateway -- Live Traffic")


def get_active_clients():
    # NOTE: Redis KEYS is O(N) and blocks the server -- fine for a
    # small local dev dashboard, but SCAN would be the production-safe
    # choice for a large keyspace. Worth naming as a known trade-off.

    keys = r.keys("traffic:timestamps:*")

    return [
        k.split("traffic:timestamps:")[1]
        for k in keys
    ]


def compute_features(client_id):
    now = time.time()
    cutoff = now - WINDOW_SECONDS

    ts_key = f"traffic:timestamps:{client_id}"
    ep_key = f"traffic:endpoints:{client_id}"

    request_count = r.zcount(
        ts_key,
        cutoff,
        now
    )

    endpoint_diversity = r.scard(ep_key)

    timestamps = sorted(
        float(t)
        for t in r.zrangebyscore(
            ts_key,
            cutoff,
            now
        )
    )

    burstiness = 0.0

    if len(timestamps) >= 3:
        gaps = [
            timestamps[i] - timestamps[i - 1]
            for i in range(1, len(timestamps))
        ]

        burstiness = statistics.pstdev(gaps)

    return (
        request_count,
        endpoint_diversity,
        round(burstiness, 4)
    )


rows = []

st.markdown(
    """
    
    """,
    unsafe_allow_html=True
)

rows = []

for client_id in get_active_clients():
    rc, ed, b = compute_features(client_id)

    if rc < 3:
        is_anomaly, score = False, None

    else:
        vector = [[rc, ed, b]]

        pred = model.predict(vector)[0]

        score = round(
            float(
                model.decision_function(vector)[0]
            ),
            4
        )

        is_anomaly = pred == -1

    rows.append({
        "Client": client_id,
        "Requests (60s)": rc,
        "Endpoint Diversity": ed,
        "Burstiness": b,
        "Anomaly Score": score,
        "Flagged": "Anomalous" if is_anomaly else "Normal",
    })


df = pd.DataFrame(rows)


# --- Summary metrics row ---

total_clients = len(df)

flagged_count = (
    (df["Flagged"] == "Anomalous").sum()
    if not df.empty
    else 0
)

avg_requests = (
    round(df["Requests (60s)"].mean(), 1)
    if not df.empty
    else 0
)


col1, col2, col3 = st.columns(3)

col1.metric(
    "Active Clients",
    total_clients
)

col2.metric(
    "Flagged as Anomalous",
    flagged_count
)

col3.metric(
    "Avg Requests / Client (60s)",
    avg_requests
)


st.divider()


# --- Color-coded table: red-tinted rows for flagged clients ---

def highlight_flagged(row):
    color = (
        "background-color: rgba(220, 53, 69, 0.25)"
        if row["Flagged"] == "Anomalous"
        else ""
    )

    return [color] * len(row)


if not df.empty:
    styled_df = df.style.apply(
        highlight_flagged,
        axis=1
    )

    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True
    )

    st.subheader("Request Volume by Client")

    chart_df = df.set_index("Client")["Requests (60s)"]

    st.bar_chart(chart_df)

else:
    st.info(
        "No active client traffic yet. "
        "Send a few requests to the gateway to see live data here."
    )


st.caption(
    "Refresh the page to see updated traffic."
)