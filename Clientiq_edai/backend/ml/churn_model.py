# RandomForest churn model
"""
ClientIQ — Churn Prediction Model
Trains and serves a RandomForest churn classifier using CRM signals.
"""

import os
import pickle
from typing import Dict, List, Optional
import numpy as np
from backend.utils.logger import logger

MODEL_PATH = "models/churn_model.pkl"
SCALER_PATH = "models/churn_scaler.pkl"

FEATURE_NAMES = [
    "health_score",
    "sentiment_avg",
    "ticket_count",
    "days_since_contact",
    "contract_value_log",
    "renewal_days",
    "open_tickets",
    "avg_response_hrs",
    "engagement_rate",
    "account_age_months",
]


class ChurnPredictor:
    """
    RandomForest-based churn probability predictor.

    Features:
    - health_score (0–100)
    - sentiment_avg (-1 to 1)
    - ticket_count (integer)
    - days_since_contact (integer)
    - contract_value_log (log10 of contract value)
    - renewal_days (days until renewal)
    - open_tickets (integer)
    - avg_response_hrs (float)
    - engagement_rate (0–1)
    - account_age_months (integer)
    """

    def __init__(self):
        self._model = None
        self._scaler = None
        self._load_or_initialize()

    def _load_or_initialize(self):
        """Load saved model or initialize with heuristic weights."""
        os.makedirs("models", exist_ok=True)
        if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
            try:
                with open(MODEL_PATH, "rb") as f:
                    self._model = pickle.load(f)
                with open(SCALER_PATH, "rb") as f:
                    self._scaler = pickle.load(f)
                logger.info("[ChurnModel] Loaded saved model from {}", MODEL_PATH)
                return
            except Exception as e:
                logger.warning("[ChurnModel] Failed to load model: {}", e)

        # Generate synthetic training data if no model exists
        self._train_on_synthetic_data()

    def _train_on_synthetic_data(self):
        """Train on synthetic CRM data with realistic churn patterns."""
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.preprocessing import StandardScaler
        from sklearn.model_selection import train_test_split
        import numpy as np

        logger.info("[ChurnModel] Training on synthetic data...")
        np.random.seed(42)
        n = 2000

        # Synthetic features
        health      = np.random.uniform(0, 100, n)
        sentiment   = np.random.uniform(-1, 1, n)
        tickets     = np.random.poisson(3, n).astype(float)
        days_since  = np.random.exponential(30, n)
        contract_v  = np.log10(np.random.uniform(5000, 500000, n))
        renewal_d   = np.random.uniform(0, 365, n)
        open_t      = np.random.poisson(1.5, n).astype(float)
        resp_hrs    = np.random.exponential(12, n)
        engagement  = np.clip(np.random.normal(0.6, 0.2, n), 0, 1)
        age_months  = np.random.uniform(1, 60, n)

        X = np.column_stack([health, sentiment, tickets, days_since, contract_v,
                              renewal_d, open_t, resp_hrs, engagement, age_months])

        # Churn rule: low health + negative sentiment + high tickets = high churn
        churn_score = (
            -0.4 * (health / 100)
            - 0.25 * sentiment
            + 0.15 * (tickets / 10)
            + 0.10 * (days_since / 90)
            - 0.05 * (renewal_d / 365)
            + np.random.normal(0, 0.05, n)
        )
        y = (churn_score > np.percentile(churn_score, 70)).astype(int)

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        self._scaler = StandardScaler()
        X_train_s = self._scaler.fit_transform(X_train)

        self._model = RandomForestClassifier(
            n_estimators=100,
            max_depth=8,
            min_samples_split=10,
            class_weight="balanced",
            random_state=42,
        )
        self._model.fit(X_train_s, y_train)

        X_test_s = self._scaler.transform(X_test)
        accuracy = self._model.score(X_test_s, y_test)
        logger.info("[ChurnModel] Trained | accuracy={:.3f}", accuracy)

        # Persist
        with open(MODEL_PATH, "wb") as f:
            pickle.dump(self._model, f)
        with open(SCALER_PATH, "wb") as f:
            pickle.dump(self._scaler, f)

    def predict_single(self, features: Dict[str, float]) -> float:
        """Predict churn probability for a single client. Returns 0.0–1.0."""
        import math
        x = np.array([
            features.get("health_score", 70),
            features.get("sentiment_avg", 0),
            features.get("ticket_count", 0),
            features.get("days_since_contact", 30),
            math.log10(max(1, features.get("contract_value", 50000))),
            features.get("renewal_days", 180),
            features.get("open_tickets", 0),
            features.get("avg_response_hrs", 24),
            features.get("engagement_rate", 0.5),
            features.get("account_age_months", 12),
        ]).reshape(1, -1)

        x_scaled = self._scaler.transform(x)
        prob = self._model.predict_proba(x_scaled)[0][1]
        return float(np.clip(prob, 0.0, 1.0))

    def predict_batch(self, features_list: List[Dict]) -> List[float]:
        """Predict churn for a list of clients."""
        return [self.predict_single(f) for f in features_list]

    def get_feature_importance(self) -> Dict[str, float]:
        """Return feature importance scores."""
        if self._model is None:
            return {}
        importances = self._model.feature_importances_
        return dict(zip(FEATURE_NAMES, importances.tolist()))