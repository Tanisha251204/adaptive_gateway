import asyncio
import joblib
from gateway.feature_logger import get_features

MODEL_PATH = "models/anomaly_model.pkl"
model = joblib.load(MODEL_PATH)

MIN_REQUESTS_FOR_SCORING = 3


def _score_sync(feature_vector):
    raw_score = model.decision_function(feature_vector)[0]
    return raw_score


async def score_client(client_id: str) -> dict:
    features = await get_features(client_id)

    if features["request_count_60s"] < MIN_REQUESTS_FOR_SCORING:
        return {
            "client_id": client_id,
            "is_anomaly": False,
            "anomaly_score": None,
            "reason": "not enough traffic history yet",
        }

    feature_vector = [[
        features["request_count_60s"],
        features["endpoint_diversity"],
        features["burstiness"],
    ]]

    raw_score = await asyncio.to_thread(_score_sync, feature_vector)

    return {
        "client_id": client_id,
        "is_anomaly": bool(raw_score < 0),
        "anomaly_score": round(float(raw_score), 4),
        "reason": None,
    }