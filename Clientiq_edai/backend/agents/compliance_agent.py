# Compliance agent
"""
ClientIQ — Compliance & Policy Agent
Enforces RBAC rules, filters sensitive data, and validates governance policies
before any query proceeds through the pipeline.
"""

import re
from typing import List
from backend.graph.state import GraphState
from backend.utils.logger import logger


# ─── RBAC permissions matrix ──────────────────────────────────────────────────

ROLE_PERMISSIONS = {
    "admin": {
        "read_crm": True,
        "read_financials": True,
        "read_contracts": True,
        "read_emails": True,
        "read_calls": True,
        "read_pii": True,
        "read_audit_logs": True,
        "export_data": True,
    },
    "manager": {
        "read_crm": True,
        "read_financials": True,
        "read_contracts": True,
        "read_emails": True,
        "read_calls": True,
        "read_pii": False,
        "read_audit_logs": False,
        "export_data": True,
    },
    "analyst": {
        "read_crm": True,
        "read_financials": True,
        "read_contracts": False,
        "read_emails": True,
        "read_calls": True,
        "read_pii": False,
        "read_audit_logs": False,
        "export_data": False,
    },
    "viewer": {
        "read_crm": True,
        "read_financials": False,
        "read_contracts": False,
        "read_emails": False,
        "read_calls": False,
        "read_pii": False,
        "read_audit_logs": False,
        "export_data": False,
    },
}

# Patterns that suggest sensitive data access
SENSITIVE_PATTERNS = [
    (r"\bssn\b|\bsocial security\b", "SSN data access", "read_pii"),
    (r"\bcredit card\b|\bpayment card\b", "Payment card data", "read_pii"),
    (r"\bpassword\b|\bcredential\b", "Credential access", "admin"),
    (r"\bsalary\b|\bcompensation\b", "Employee compensation", "read_financials"),
    (r"\bexport all\b|\bdump all\b|\bextract all\b", "Mass data export", "export_data"),
    (r"\baudit log\b|\baccess log\b", "Audit log access", "read_audit_logs"),
    (r"\bcontract terms\b|\bagreement details\b", "Contract details", "read_contracts"),
]


class ComplianceAgent:
    """
    Compliance & Policy Agent.

    Runs BEFORE any data access to:
    1. Check RBAC permissions against query intent
    2. Detect sensitive data requests
    3. Redact PII if user lacks permission
    4. Log compliance events
    """

    def __init__(self):
        self.name = "compliance_agent"

    def run(self, state: GraphState) -> GraphState:
        """Main compliance check — runs on every query."""
        logger.info("[Compliance] Checking query for user_role={}", state.get("user_role"))

        user_role = state.get("user_role", "viewer")
        query = state.get("user_query", "").lower()
        flags: List[str] = []
        redacted: List[str] = []
        blocked = False

        permissions = ROLE_PERMISSIONS.get(user_role, ROLE_PERMISSIONS["viewer"])

        # Check sensitive patterns
        for pattern, description, required_permission in SENSITIVE_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                if not permissions.get(required_permission, False):
                    flags.append(f"BLOCKED: {description} (requires {required_permission})")
                    blocked = True
                    logger.warning("[Compliance] Blocked pattern '{}' for role '{}'", description, user_role)
                else:
                    flags.append(f"PERMITTED: {description}")

        # Check intent-based permission
        intent = state.get("intent", "")
        if intent == "crm_query" and not permissions.get("read_crm"):
            flags.append("BLOCKED: CRM access denied for role")
            blocked = True

        # PII redaction for non-admin users
        if not permissions.get("read_pii"):
            redacted.extend(["phone_numbers", "personal_emails", "ssn"])

        # Determine financial data access
        if "revenue" in query and not permissions.get("read_financials"):
            flags.append("BLOCKED: Financial data requires manager+ role")
            blocked = True

        state["compliance_flags"] = flags
        state["redacted_fields"] = redacted
        state["compliance_cleared"] = not blocked
        state["agent_trace"].append(self.name)

        if blocked:
            state["final_response"] = (
                "⛔ Access Denied: Your role does not have permission to access this information. "
                f"Please contact your administrator. Details: {'; '.join(flags)}"
            )
            state["completed"] = True
            logger.warning("[Compliance] Query blocked | role={} | flags={}", user_role, flags)
        else:
            logger.info("[Compliance] Query cleared | role={}", user_role)

        return state