import os
import numpy as np
import joblib

from sklearn.ensemble import IsolationForest
from sklearn.metrics import classification_report, confusion_matrix


np.random.seed(42)


def generate_normal_traffic(n=800):
    # Normal users: moderate, varied request rate, visit several
    # different endpoints, irregular timing (higher burstiness value
    # = more irregular gaps between requests, i.e. more human-like).

    request_count = np.random.normal(
        loc=8,
        scale=3,
        size=n
    ).clip(0, None)

    endpoint_diversity = np.random.normal(
        loc=4,
        scale=1.5,
        size=n
    ).clip(1, None)

    burstiness = np.random.normal(
        loc=2.0,
        scale=0.8,
        size=n
    ).clip(0, None)

    return np.column_stack([
        request_count,
        endpoint_diversity,
        burstiness
    ])


def generate_abusive_traffic(n=100):
    # Bots/scrapers: high request rate, hammer very few endpoints,
    # suspiciously constant timing (low burstiness).

    request_count = np.random.normal(
        loc=40,
        scale=10,
        size=n
    ).clip(0, None)

    endpoint_diversity = np.random.normal(
        loc=1.2,
        scale=0.4,
        size=n
    ).clip(1, None)

    burstiness = np.random.normal(
        loc=0.1,
        scale=0.05,
        size=n
    ).clip(0, None)

    return np.column_stack([
        request_count,
        endpoint_diversity,
        burstiness
    ])


def main():
    normal = generate_normal_traffic(800)
    abusive = generate_abusive_traffic(100)

    # Train ONLY on normal traffic. This mirrors real deployment:
    # you rarely have reliable labeled attack data upfront, but you
    # usually do have a good sense of what normal usage looks like.

    X_train = normal

    # Build a held-out test set mixing normal and abusive examples,
    # with labels, purely to EVALUATE the model -- not to train it.

    X_test = np.vstack([
        normal[:200],
        abusive
    ])

    y_test = np.array(
        [1] * 200 + [-1] * len(abusive)
    )

    # sklearn convention:
    # 1 = normal/inlier
    # -1 = anomaly/outlier

    model = IsolationForest(
        n_estimators=100,
        contamination=0.1,
        random_state=42
    )

    model.fit(X_train)

    preds = model.predict(X_test)

    print(
        classification_report(
            y_test,
            preds,
            target_names=["anomaly", "normal"]
        )
    )

    print("Confusion matrix:")
    print(confusion_matrix(y_test, preds))

    os.makedirs("models", exist_ok=True)

    joblib.dump(
        model,
        "models/anomaly_model.pkl"
    )

    print("Model saved to models/anomaly_model.pkl")


if __name__ == "__main__":
    main()