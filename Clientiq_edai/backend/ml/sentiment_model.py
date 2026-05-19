# TextBlob-VADER sentiment
"""
ClientIQ — Sentiment Model
Multi-source sentiment scoring: VADER for speed, TextBlob for accuracy,
with ensemble averaging for robustness.
"""

from typing import Dict, Tuple
from backend.utils.logger import logger

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _vader = SentimentIntensityAnalyzer()
except ImportError:
    _vader = None

try:
    from textblob import TextBlob
    _has_textblob = True
except ImportError:
    _has_textblob = False


class SentimentModel:
    """
    Ensemble sentiment scorer.

    Combines VADER (rule-based, great for business text) and
    TextBlob (ML-based) into a weighted score.
    """

    VADER_WEIGHT = 0.6
    TEXTBLOB_WEIGHT = 0.4

    def score(self, text: str) -> Tuple[float, str]:
        """
        Score a piece of text.

        Returns:
            (score: float, label: str)
            score: -1.0 (very negative) to 1.0 (very positive)
            label: "positive" | "neutral" | "negative"
        """
        if not text or not text.strip():
            return 0.0, "neutral"

        scores = []

        # VADER
        if _vader:
            vader_scores = _vader.polarity_scores(text[:5000])
            scores.append((vader_scores["compound"], self.VADER_WEIGHT))

        # TextBlob
        if _has_textblob:
            blob = TextBlob(text[:3000])
            tb_score = blob.sentiment.polarity  # -1 to 1
            scores.append((tb_score, self.TEXTBLOB_WEIGHT))

        if not scores:
            return 0.0, "neutral"

        # Weighted average
        total_weight = sum(w for _, w in scores)
        composite = sum(s * w for s, w in scores) / total_weight
        composite = max(-1.0, min(1.0, composite))

        label = "positive" if composite >= 0.05 else "negative" if composite <= -0.05 else "neutral"
        return round(composite, 4), label

    def score_batch(self, texts: list) -> list:
        """Score a list of texts. Returns list of (score, label) tuples."""
        return [self.score(t) for t in texts]

    def get_detailed_scores(self, text: str) -> Dict:
        """Return all component scores for analysis."""
        result = {"composite": 0.0, "label": "neutral"}
        if _vader:
            v = _vader.polarity_scores(text[:5000])
            result["vader"] = v
        if _has_textblob:
            blob = TextBlob(text[:3000])
            result["textblob"] = {
                "polarity": blob.sentiment.polarity,
                "subjectivity": blob.sentiment.subjectivity,
            }
        composite, label = self.score(text)
        result["composite"] = composite
        result["label"] = label
        return result


sentiment_model = SentimentModel()