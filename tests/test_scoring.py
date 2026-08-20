"""
Unit tests for app/scoring.py (Compliance & Risk Score Engine).
"""

from __future__ import annotations

import sys
from pathlib import Path
import pytest

# Ensure app path is on sys.path
APP_DIR = Path(__file__).parent.parent / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from schema import (
    AgentCard,
    DecisionAuthority,
    RiskClassification,
    LLMInfo,
    ToolEntry,
    DataSource,
    HumanOversightMechanism,
    IncidentContact,
)
from scoring import calculate_compliance_score


def test_perfect_card_score():
    card = AgentCard(
        agent_id="test-perfect",
        agent_name="Perfect Compliant Agent",
        purpose_and_scope="Valid purpose and scope description.",
        llm=LLMInfo(provider="OpenAI", model_name="gpt-4o", version="1.0"),
        tool_inventory=[
            ToolEntry(name="reader", description="read data", operations=["read"], data_accessed=["public info"])
        ],
        data_sources=[DataSource(name="public_db", data_type="structured DB", sensitivity="public")],
        decision_authority=DecisionAuthority.ADVISORY,
        human_oversight=[HumanOversightMechanism(description="Human reviews all drafts", trigger="all drafts")],
        risk_classification=RiskClassification.LIMITED,
        known_limitations=["Limitation 1"],
        incident_contact=IncidentContact(name="Support", email="support@example.com", escalation_path="PagerDuty"),
    )

    score = calculate_compliance_score(card)
    assert score.overall_score >= 90
    assert score.risk_level == "LOW_RISK"
    assert score.color_badge == "🟢"
    assert score.grade in ("A", "A+")
    assert len(score.strengths) > 0


def test_incomplete_card_score():
    card = AgentCard(
        agent_id="test-incomplete",
        agent_name="Incomplete Agent",
        purpose_and_scope="",  # Empty string -> completeness penalty
        llm=LLMInfo(provider="OpenAI", model_name="gpt-4o", version="1.0"),
        tool_inventory=[],     # Empty list -> completeness penalty
        data_sources=[],
        decision_authority=None,
        human_oversight=[],
        risk_classification=None,
        known_limitations=[],
        incident_contact=None,
    )

    score = calculate_compliance_score(card)
    assert score.overall_score < 70
    assert score.risk_level in ("MODERATE_RISK", "HIGH_RISK")
    assert len(score.penalties) > 0


def test_high_autonomy_unprotected_pii_score():
    card = AgentCard(
        agent_id="test-high-risk",
        agent_name="High Risk Autonomous Agent",
        purpose_and_scope="Processes sensitive customer PII without human review.",
        llm=LLMInfo(provider="Anthropic", model_name="claude-3-5", version="3.5"),
        tool_inventory=[
            ToolEntry(name="pii_writer", description="writes PII", operations=["write"], data_accessed=["customer PII", "SSN"])
        ],
        data_sources=[DataSource(name="users_db", data_type="structured DB", sensitivity="PII")],
        decision_authority=DecisionAuthority.AUTONOMOUS,
        human_oversight=[],  # Autonomous + PII + No oversight = double penalty!
        risk_classification=RiskClassification.HIGH,
        known_limitations=["Errors in edge cases"],
        incident_contact=IncidentContact(name="SecOps", email="secops@example.com"),
    )

    score = calculate_compliance_score(card)
    assert score.overall_score < 75
    assert any("PII" in p for p in score.penalties)
    assert any("Autonomy" in p or "Oversight" in p for p in score.penalties)
