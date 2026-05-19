# Agent initialization
"""
ClientIQ — Agents Package
All 11 LangGraph agents.
"""
from backend.agents.supervisor import SupervisorAgent
from backend.agents.compliance_agent import ComplianceAgent
from backend.agents.crm_sql_agent import CRMSQLAgent
from backend.agents.retrieval_agent import RetrievalAgent
from backend.agents.citation_agent import CitationAgent
from backend.agents.memory_agent import MemoryAgent
from backend.agents.sentiment_agent import SentimentAgent
from backend.agents.analytics_agent import AnalyticsAgent
from backend.agents.risk_agent import RiskAgent
from backend.agents.recommendation_agent import RecommendationAgent
from backend.agents.knowledge_graph_agent import KnowledgeGraphAgent

__all__ = [
    "SupervisorAgent", "ComplianceAgent", "CRMSQLAgent",
    "RetrievalAgent", "CitationAgent", "MemoryAgent",
    "SentimentAgent", "AnalyticsAgent", "RiskAgent",
    "RecommendationAgent", "KnowledgeGraphAgent",
]