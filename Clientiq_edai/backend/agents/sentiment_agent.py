# Sentiment agent
"""
ClientIQ — Sentiment Agent
Detects sentiment, emotion signals, and dissatisfaction patterns
from retrieved communication data.
"""

from typing import List
from backend.graph.state import GraphState, RetrievedChunk
from backend.services.mistral_client import MistralClient
from backend.utils.logger import logger

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _vader = SentimentIntensityAnalyzer()
except ImportError:
    _vader = None


NEGATIVE_SIGNALS = [
    "frustrated", "disappointed", "unhappy", "dissatisfied", "angry",
    "unacceptable", "worst", "terrible", "failure", "escalate", "cancel",
    "churning", "leaving", "competitor", "considering alternatives",
    "breach", "violation", "delayed", "overdue",
]

POSITIVE_SIGNALS = [
    "excellent", "fantastic", "love", "impressed", "delighted", "great",
    "outstanding", "recommend", "renewal", "expand", "growing",
    "satisfied", "pleased", "valuable", "success",
]


class SentimentAgent:
    """
    Sentiment Agent.

    Analyzes sentiment across retrieved communication chunks:
    - Runs VADER for fast rule-based scoring
    - Uses LLM for nuanced emotion analysis
    - Detects churn signals and dissatisfaction patterns
    """

    def __init__(self):
        self.llm = MistralClient()
        self.name = "sentiment_agent"

    def run(self, state: GraphState) -> GraphState:
        """Analyze sentiment across all retrieved content."""
        logger.info("[Sentiment] Analyzing sentiment across {} chunks", len(state.get("retrieved_chunks", [])))

        chunks: List[RetrievedChunk] = state.get("retrieved_chunks", [])
        combined_text = " ".join(c.get("text", "") for c in chunks[:10])

        if not combined_text.strip():
            state["agent_trace"].append(self.name)
            return state

        # VADER scoring
        vader_score = self._vader_score(combined_text)

        # Emotion signal detection
        emotion_signals = self._detect_signals(combined_text)

        # LLM nuanced analysis
        llm_analysis = self._llm_sentiment(state["user_query"], combined_text[:1500])

        # Aggregate score: blend VADER + LLM
        state["sentiment_score"] = vader_score
        state["sentiment_label"] = self._label(vader_score)
        state["emotion_signals"] = emotion_signals

        # Append analysis to analytics data
        analytics = state.get("analytics_data", {})
        analytics["sentiment_analysis"] = {
            "score": vader_score,
            "label": self._label(vader_score),
            "signals": emotion_signals,
            "llm_summary": llm_analysis,
            "chunk_count": len(chunks),
        }
        state["analytics_data"] = analytics

        logger.info("[Sentiment] Score={:.3f} | Label={} | Signals={}", vader_score, self._label(vader_score), emotion_signals[:3])

        state["agent_trace"].append(self.name)
        return state

    def _vader_score(self, text: str) -> float:
        """Return compound VADER sentiment score (-1 to 1)."""
        if _vader:
            scores = _vader.polarity_scores(text[:5000])
            return scores["compound"]
        # Fallback: keyword counting
        text_lower = text.lower()
        pos = sum(1 for s in POSITIVE_SIGNALS if s in text_lower)
        neg = sum(1 for s in NEGATIVE_SIGNALS if s in text_lower)
        total = pos + neg
        if total == 0:
            return 0.0
        return (pos - neg) / total

    def _detect_signals(self, text: str) -> List[str]:
        """Detect specific emotion/risk signal keywords."""
        text_lower = text.lower()
        detected = []
        for signal in NEGATIVE_SIGNALS:
            if signal in text_lower:
                detected.append(f"⚠️ {signal}")
        for signal in POSITIVE_SIGNALS:
            if signal in text_lower:
                detected.append(f"✓ {signal}")
        return detected[:10]

    def _llm_sentiment(self, query: str, text: str) -> str:
        """Use LLM for nuanced sentiment interpretation."""
        prompt = f"""Analyze the sentiment and emotional tone of these client communications.
Identify: overall sentiment, key concerns, relationship health signals.
Be concise (2-3 sentences).

Query context: {query}
Communications:
{text}

Analysis:"""
        return self.llm.complete(prompt, temperature=0.2)

    def _label(self, score: float) -> str:
        if score >= 0.05:
            return "positive"
        elif score <= -0.05:
            return "negative"
        return "neutral"
