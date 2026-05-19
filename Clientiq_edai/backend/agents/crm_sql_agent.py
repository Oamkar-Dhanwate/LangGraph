# CRM SQL agent
"""
ClientIQ — CRM SQL Agent
Translates natural language questions into SQL queries,
executes them against TiDB, and returns structured results.
"""

import re
import asyncio
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from backend.graph.state import GraphState
from backend.services.mistral_client import MistralClient
from backend.utils.logger import logger


# ─── Schema context for SQL generation ───────────────────────────────────────

SQL_SCHEMA_CONTEXT = """
Available tables in clientiq database:

companies(id, name, industry, size_category, annual_revenue, country, account_tier, health_score, churn_risk)
contacts(id, company_id, first_name, last_name, email, phone, job_title, department, sentiment_score, last_contacted)
opportunities(id, company_id, name, stage, amount, probability, close_date, source, notes)
contracts(id, company_id, title, contract_type, value, currency, start_date, end_date, status)
emails(id, company_id, contact_id, direction, subject, sentiment_score, sentiment_label, sent_at)
meetings(id, company_id, title, meeting_type, duration_mins, sentiment_score, scheduled_at)
call_transcripts(id, company_id, call_type, duration_secs, sentiment_score, called_at)
support_tickets(id, company_id, title, description, priority, status, category, sentiment_score, first_response_hrs, resolution_hrs, opened_at)
health_snapshots(id, company_id, health_score, churn_risk, sentiment_avg, ticket_count, snapshot_date)
sentiment_timeline(id, company_id, source_type, source_id, sentiment_score, sentiment_label, recorded_at)

Important:
- SQL dialect is TiDB/MySQL, not PostgreSQL. Do not use DATE_TRUNC, ILIKE, :: casts, or quoted identifiers.
- For "this quarter", use a TiDB/MySQL-compatible range such as snapshot_date >= DATE_SUB(CURDATE(), INTERVAL 3 MONTH).
- churn_risk is numeric from 0.0 to 1.0. High churn risk means churn_risk >= 0.7, not churn_risk = 'High'.
- opportunities has no sentiment_score column. Do not calculate opportunity sentiment.
- For company-level sentiment, prefer health_snapshots.sentiment_avg or sentiment_timeline.sentiment_score.
- For communication sentiment, use emails, meetings, call_transcripts, or support_tickets sentiment_score.
"""


SQL_TABLE_COLUMNS = {
    "companies": {"id", "name", "industry", "size_category", "annual_revenue", "country", "account_tier", "health_score", "churn_risk"},
    "contacts": {"id", "company_id", "first_name", "last_name", "email", "phone", "job_title", "department", "sentiment_score", "last_contacted"},
    "opportunities": {"id", "company_id", "name", "stage", "amount", "probability", "close_date", "source", "notes"},
    "contracts": {"id", "company_id", "title", "contract_type", "value", "currency", "start_date", "end_date", "status"},
    "emails": {"id", "company_id", "contact_id", "direction", "subject", "sentiment_score", "sentiment_label", "sent_at"},
    "meetings": {"id", "company_id", "title", "meeting_type", "duration_mins", "sentiment_score", "scheduled_at"},
    "call_transcripts": {"id", "company_id", "call_type", "duration_secs", "sentiment_score", "called_at"},
    "support_tickets": {"id", "company_id", "title", "description", "priority", "status", "category", "sentiment_score", "first_response_hrs", "resolution_hrs", "opened_at"},
    "health_snapshots": {"id", "company_id", "health_score", "churn_risk", "sentiment_avg", "ticket_count", "snapshot_date"},
    "sentiment_timeline": {"id", "company_id", "source_type", "source_id", "sentiment_score", "sentiment_label", "recorded_at"},
}


def to_json_safe(value: Any) -> Any:
    """Convert DB driver values into JSON-serializable primitives."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value

UNSUPPORTED_SQL_PATTERNS = {
    r"\bDATE_TRUNC\s*\(": "DATE_TRUNC is PostgreSQL-only; use TiDB/MySQL date functions such as DATE_SUB(CURDATE(), INTERVAL 3 MONTH)",
    r"\bILIKE\b": "ILIKE is PostgreSQL-only; use LIKE with LOWER(...) if needed",
    r"::\s*[a-zA-Z_][\w]*": "PostgreSQL casts are not supported in TiDB/MySQL",
}

NUMERIC_COLUMNS = {
    "annual_revenue",
    "health_score",
    "churn_risk",
    "sentiment_score",
    "sentiment_avg",
    "amount",
    "probability",
    "duration_mins",
    "duration_secs",
    "first_response_hrs",
    "resolution_hrs",
    "ticket_count",
}


class CRMSQLAgent:
    """
    CRM SQL Agent.

    1. Uses LLM to generate SQL from natural language
    2. Validates SQL for safety (read-only, no DROP/DELETE)
    3. Executes against TiDB via SQLAlchemy
    4. Returns structured results to state
    """

    def __init__(self):
        self.llm = MistralClient()
        self.name = "crm_sql_agent"
        self._last_validation_error = None

    def run(self, state: GraphState) -> GraphState:
        """Sync compatibility wrapper for non-LangGraph callers."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.arun(state))
        raise RuntimeError("CRMSQLAgent.run() cannot be called from an active event loop; use arun()")

    async def arun(self, state: GraphState) -> GraphState:
        """Execute CRM SQL query from user's question."""
        logger.info("[CRM SQL] Generating SQL for: {}", state["user_query"][:80])

        sql = self._generate_sql(state["user_query"], state.get("entity_context", {}))
        state["sql_query"] = sql

        if not sql:
            state["sql_error"] = "Could not generate valid SQL"
            state["agent_trace"].append(self.name)
            return state

        results = await self._execute_sql(sql)
        state["sql_results"] = results

        if isinstance(results, str):  # error string
            state["sql_error"] = results
            state["sql_results"] = []
        else:
            logger.info("[CRM SQL] Query returned {} rows", len(results))

        state["agent_trace"].append(self.name)
        return state

    def _generate_sql(self, query: str, entity_context: dict) -> str:
        """Use LLM to generate safe, read-only SQL."""
        company_hint = ""
        if entity_context.get("company_name"):
            company_hint = f"\nCurrent context: company = '{entity_context['company_name']}'"

        prompt = f"""You are a SQL expert for a CRM database. Generate a single, safe SELECT query.

{SQL_SCHEMA_CONTEXT}
{company_hint}

Rules:
- Only SELECT statements
- No INSERT, UPDATE, DELETE, DROP, TRUNCATE
- Always include LIMIT (max 100)
- Use JOINs where appropriate
- Return ONLY the SQL query, no explanation

User question: {query}

SQL:"""

        response = self.llm.complete(prompt, temperature=0.1)
        sql = self._sanitize_sql(self._extract_sql(response))
        if sql:
            return sql

        if self._last_validation_error:
            retry_prompt = f"""{prompt}

The previous SQL was invalid: {self._last_validation_error}
Generate a corrected SELECT query using only the listed table columns.

Corrected SQL:"""
            response = self.llm.complete(retry_prompt, temperature=0.0)
            sql = self._sanitize_sql(self._extract_sql(response))
        return sql

    def _extract_sql(self, text: str) -> str:
        """Extract SQL from LLM response."""
        # Try to extract from code block
        match = re.search(r"```(?:sql)?\n?(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        # Otherwise take first SELECT statement
        match = re.search(r"(SELECT\s+.+?)(?:;|$)", text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return text.strip()

    def _sanitize_sql(self, sql: str) -> Optional[str]:
        """Block dangerous SQL operations."""
        self._last_validation_error = None
        if not sql:
            return None
        forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "CREATE", "ALTER", "GRANT"]
        sql_upper = sql.upper()
        for keyword in forbidden:
            if keyword in sql_upper:
                logger.warning("[CRM SQL] Blocked dangerous SQL keyword: {}", keyword)
                return None
        validation_error = self._validate_columns(sql)
        if validation_error:
            self._last_validation_error = validation_error
            logger.warning("[CRM SQL] Invalid generated SQL: {}", validation_error)
            return None
        validation_error = self._validate_dialect_and_types(sql)
        if validation_error:
            self._last_validation_error = validation_error
            logger.warning("[CRM SQL] Invalid generated SQL: {}", validation_error)
            return None
        # Ensure LIMIT exists
        if "LIMIT" not in sql_upper:
            sql = sql.rstrip(";") + " LIMIT 50"
        return sql

    def _validate_columns(self, sql: str) -> Optional[str]:
        """Validate simple alias.column references against the known CRM schema."""
        aliases = {}
        table_pattern = re.compile(
            r"\b(?:FROM|JOIN)\s+([a-zA-Z_][\w]*)(?:\s+(?:AS\s+)?(?!ON\b|WHERE\b|JOIN\b|LEFT\b|RIGHT\b|INNER\b|OUTER\b|FULL\b|GROUP\b|ORDER\b|LIMIT\b)([a-zA-Z_][\w]*))?",
            re.IGNORECASE,
        )
        for table, alias in table_pattern.findall(sql):
            table_l = table.lower()
            if table_l not in SQL_TABLE_COLUMNS:
                return f"Unknown table '{table}'"
            aliases[(alias or table).lower()] = table_l
            aliases[table_l] = table_l

        for alias, column in re.findall(r"\b([a-zA-Z_][\w]*)\.([a-zA-Z_][\w]*)\b", sql):
            alias_l = alias.lower()
            column_l = column.lower()
            table = aliases.get(alias_l)
            if not table:
                continue
            if column_l not in SQL_TABLE_COLUMNS[table]:
                return f"Unknown column '{alias}.{column}' for table '{table}'"
        return None

    def _validate_dialect_and_types(self, sql: str) -> Optional[str]:
        """Reject common PostgreSQL syntax and text comparisons against numeric CRM fields."""
        for pattern, message in UNSUPPORTED_SQL_PATTERNS.items():
            if re.search(pattern, sql, re.IGNORECASE):
                return message

        numeric_string_pattern = re.compile(
            r"(?:\b[a-zA-Z_][\w]*\.)?\b([a-zA-Z_][\w]*)\b\s*(=|!=|<>|>|<|>=|<=)\s*'([^']*)'",
            re.IGNORECASE,
        )
        for column, _operator, value in numeric_string_pattern.findall(sql):
            column_l = column.lower()
            if column_l not in NUMERIC_COLUMNS:
                continue
            try:
                float(value)
            except ValueError:
                return f"Numeric column '{column}' cannot be compared to text value '{value}'"
        return None

    async def _execute_sql(self, sql: str) -> Any:
        """Execute SQL against TiDB. Returns list of dicts or error string."""
        try:
            import sqlalchemy as sa
            from backend.database.connection import engine

            async with engine.begin() as conn:
                result = await conn.execute(sa.text(sql))
                rows = result.fetchall()
                cols = result.keys()
                return [
                    {col: to_json_safe(value) for col, value in zip(cols, row)}
                    for row in rows
                ]

        except Exception as e:
            logger.error("[CRM SQL] Execution error: {}", e)
            return f"Query error: {str(e)}"
