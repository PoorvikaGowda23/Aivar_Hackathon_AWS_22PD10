"""
Unit tests for AI-Powered Card Review Endpoint & Generator (app/llm_extractor.py).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

APP_DIR = Path(__file__).parent.parent / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from schema import AgentCard, DecisionAuthority, RiskClassification, LLMInfo
from scoring import calculate_compliance_score
from llm_extractor import AuditReport, AuditRecommendation, generate_audit_review


def test_audit_report_schema():
    rec = AuditRecommendation(
        category="Human Oversight",
        severity="HIGH",
        finding="No human kill-switch configured",
        remediation="Add emergency stop trigger in tool_manifest.json"
    )
    report = AuditReport(
        agent_id="test-agent",
        eu_ai_act_tier="High-Risk (Art. 6)",
        audit_summary="Solid card structure but requires oversight kill-switch.",
        governance_gaps=["Missing emergency stop trigger"],
        recommendations=[rec]
    )

    assert report.agent_id == "test-agent"
    assert report.eu_ai_act_tier == "High-Risk (Art. 6)"
    assert len(report.recommendations) == 1
    assert report.recommendations[0].severity == "HIGH"
    assert report.audited_at != ""


@patch("llm_extractor.Groq")
def test_generate_audit_review_mocked(mock_groq):
    mock_client = MagicMock()
    mock_groq.return_value = mock_client

    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content="""{
  "agent_id": "test-agent",
  "eu_ai_act_tier": "Transparency Risk (Art. 50)",
  "audit_summary": "The agent operates within expected parameters.",
  "governance_gaps": ["No escalation email provided"],
  "recommendations": [
    {
      "category": "Governance",
      "severity": "LOW",
      "finding": "Missing escalation contact",
      "remediation": "Add incident contact email"
    }
  ]
}"""
            )
        )
    ]
    mock_client.chat.completions.create.return_value = mock_response

    card_dict = {
        "agent_id": "test-agent",
        "agent_name": "Test Agent",
        "purpose_and_scope": "Testing audit review",
        "llm": {"provider": "OpenAI", "model_name": "gpt-4o", "version": "1.0"},
        "tool_inventory": [],
        "data_sources": [],
    }
    score_dict = {"overall_score": 85, "risk_level": "MODERATE_RISK", "penalties": []}

    report = generate_audit_review(card_dict, score_dict)
    assert report.agent_id == "test-agent"
    assert report.eu_ai_act_tier == "Transparency Risk (Art. 50)"
    assert len(report.recommendations) == 1
    assert report.recommendations[0].category == "Governance"
