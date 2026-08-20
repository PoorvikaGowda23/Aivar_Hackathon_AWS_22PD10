"""
Compliance & Risk Score Engine for AI Agent Compliance Cards.

Calculates a quantifiable 0-100 Compliance Score for any AgentCard,
evaluating:
  1. Completeness (40% max) — field population & placeholder checks
  2. Governance & Oversight (30% max) — human triggers & incident escalation
  3. Data Privacy & Sensitivity (15% max) — PII safeguards & data classification
  4. Operational Autonomy & Risk (15% max) — decision authority vs oversight controls

Returns a structured ComplianceScore Pydantic model with category breakdowns,
grade levels (A+ to F), color badges (🟢/🟡/🔴), strengths, and penalties.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from schema import AgentCard, DecisionAuthority, RiskClassification
from completeness import check_card, CompletenessReport


class ComplianceScore(BaseModel):
    overall_score: int = Field(..., ge=0, le=100, description="Final compliance score from 0 to 100")
    risk_level: str = Field(..., description="LOW_RISK, MODERATE_RISK, or HIGH_RISK")
    color_badge: str = Field(..., description="🟢, 🟡, or 🔴")
    grade: str = Field(..., description="A+, A, B, C, D, or F")
    category_scores: Dict[str, float] = Field(..., description="Breakdown per evaluation pillar")
    strengths: List[str] = Field(default_factory=list, description="Key compliance positive points")
    penalties: List[str] = Field(default_factory=list, description="Deductions and compliance warnings")


def calculate_compliance_score(
    card: AgentCard,
    report: Optional[CompletenessReport] = None,
) -> ComplianceScore:
    """
    Computes a weighted 0-100 score for an AgentCard.
    If completeness report is not supplied, it will be executed automatically.
    """
    if report is None:
        report = check_card(card)

    strengths: List[str] = []
    penalties: List[str] = []

    # ---------------------------------------------------------------------------
    # Pillar 1: Completeness (40 Points Max)
    # ---------------------------------------------------------------------------
    completeness_max = 40.0
    issue_count = len(report.issues)
    # Deduct 8 points per completeness issue, minimum 0
    completeness_score = max(0.0, completeness_max - (issue_count * 8.0))

    if report.is_complete:
        strengths.append("Full Field Completeness: Card contains zero missing, null, or placeholder fields.")
    else:
        for issue in report.issues:
            penalties.append(f"Completeness Issue [-8 pts]: '{issue.field}' is {issue.issue_type.value} ({issue.message})")

    # ---------------------------------------------------------------------------
    # Pillar 2: Governance & Oversight (30 Points Max)
    # ---------------------------------------------------------------------------
    governance_score = 0.0

    # Human Oversight (20 pts max)
    if card.human_oversight and len(card.human_oversight) > 0:
        governance_score += 15.0
        strengths.append(f"Human Oversight Defined: {len(card.human_oversight)} mechanism(s) specified.")
        # Check if triggers are defined
        triggers = [h for h in card.human_oversight if h.trigger and h.trigger.strip()]
        if triggers:
            governance_score += 5.0
            strengths.append("Explicit Oversight Triggers: Defined clear operational criteria for human review.")
        else:
            penalties.append("Missing Oversight Triggers [-5 pts]: Human oversight lacks explicit trigger conditions.")
    else:
        penalties.append("No Human Oversight [-20 pts]: Agent lacks defined human oversight mechanisms.")

    # Incident Contact & Escalation (10 pts max)
    if card.incident_contact:
        governance_score += 5.0
        if card.incident_contact.escalation_path:
            governance_score += 5.0
            strengths.append("Incident Escalation Path: Clear on-call and escalation path documented.")
        else:
            penalties.append("Missing Escalation Path [-5 pts]: Incident contact lacks an explicit escalation channel.")
    else:
        penalties.append("Missing Incident Contact [-10 pts]: No designated human contact for incidents.")

    governance_score = min(30.0, governance_score)

    # ---------------------------------------------------------------------------
    # Pillar 3: Data Privacy & Protection (15 Points Max)
    # ---------------------------------------------------------------------------
    privacy_score = 15.0

    # Inspect data sources and tools for PII / confidential data
    pii_sources = [ds for ds in card.data_sources if ds.sensitivity.lower() == "pii"]
    confidential_sources = [ds for ds in card.data_sources if ds.sensitivity.lower() == "confidential"]

    pii_tools = []
    for tool in card.tool_inventory:
        data_accessed = " ".join(tool.data_accessed).lower()
        if "pii" in data_accessed or "personal" in data_accessed or "ssn" in data_accessed or "email" in data_accessed:
            pii_tools.append(tool.name)

    if pii_sources or pii_tools:
        if card.human_oversight and len(card.human_oversight) > 0:
            strengths.append("Protected PII Scope: Agent processes PII data with human oversight safeguards in place.")
        else:
            privacy_score -= 8.0
            penalties.append("Unprotected PII Processing [-8 pts]: Agent touches PII data without human oversight mechanisms.")
    else:
        strengths.append("Low Data Sensitivity: No raw PII data sources accessed directly.")

    if confidential_sources and not card.incident_contact:
        privacy_score -= 5.0
        penalties.append("Confidential Data Without Escalation Contact [-5 pts]: Confidential data involved without incident contact.")

    privacy_score = max(0.0, min(15.0, privacy_score))

    # ---------------------------------------------------------------------------
    # Pillar 4: Operational Autonomy & Risk Level (15 Points Max)
    # ---------------------------------------------------------------------------
    autonomy_score = 15.0
    authority = card.decision_authority

    if authority == DecisionAuthority.INFORMATIONAL or str(authority) == "informational":
        strengths.append("Safe Operational Scope: Informational decision authority poses minimal risk.")
    elif authority == DecisionAuthority.ADVISORY or str(authority) == "advisory":
        strengths.append("Advisory Decision Authority: Agent recommendations require human decision approval.")
    elif authority == DecisionAuthority.AUTONOMOUS or str(authority) == "autonomous":
        if not card.human_oversight or len(card.human_oversight) == 0:
            autonomy_score -= 15.0
            penalties.append("Unrestricted Autonomy [-15 pts]: Fully autonomous agent operates without human oversight.")
        else:
            autonomy_score -= 5.0
            strengths.append("Controlled Autonomy: Autonomous execution is bounded by oversight triggers.")

    if card.risk_classification == RiskClassification.UNACCEPTABLE or str(card.risk_classification) == "unacceptable":
        autonomy_score = 0.0
        penalties.append("UNACCEPTABLE EU AI Act Risk Tier [-15 pts]: System prohibited under EU AI Act rules.")
    elif card.risk_classification == RiskClassification.HIGH or str(card.risk_classification) == "high":
        if not card.human_oversight:
            autonomy_score -= 5.0
            penalties.append("High Risk Tier Safeguard Warning [-5 pts]: High-risk system lacks required Article 14 controls.")

    autonomy_score = max(0.0, min(15.0, autonomy_score))

    # ---------------------------------------------------------------------------
    # Overall Score Aggregation
    # ---------------------------------------------------------------------------
    total_raw = completeness_score + governance_score + privacy_score + autonomy_score
    overall_score = int(round(total_raw))
    overall_score = max(0, min(100, overall_score))

    # Determine risk level, grade, and color badge
    if overall_score >= 90:
        grade = "A+" if overall_score >= 97 else "A"
        risk_level = "LOW_RISK"
        color_badge = "🟢"
    elif overall_score >= 75:
        grade = "B"
        risk_level = "MODERATE_RISK"
        color_badge = "🟡"
    elif overall_score >= 60:
        grade = "C"
        risk_level = "MODERATE_RISK"
        color_badge = "🟡"
    elif overall_score >= 40:
        grade = "D"
        risk_level = "HIGH_RISK"
        color_badge = "🔴"
    else:
        grade = "F"
        risk_level = "HIGH_RISK"
        color_badge = "🔴"

    category_scores = {
        "completeness": round(completeness_score, 1),
        "governance_and_oversight": round(governance_score, 1),
        "data_privacy": round(privacy_score, 1),
        "operational_autonomy": round(autonomy_score, 1),
    }

    return ComplianceScore(
        overall_score=overall_score,
        risk_level=risk_level,
        color_badge=color_badge,
        grade=grade,
        category_scores=category_scores,
        strengths=strengths,
        penalties=penalties,
    )


if __name__ == "__main__":
    import json
    from pathlib import Path
    import sys

    sys.path.insert(0, str(Path(__file__).parent))
    from generator import generate_agent_card

    root = Path(__file__).parent.parent
    cfg = root / "fixtures" / "simple" / "agent_config.json"
    man = root / "fixtures" / "simple" / "tool_manifest.json"
    tra = root / "fixtures" / "simple" / "run_trace.json"

    if cfg.exists():
        card = generate_agent_card(cfg, man, tra)
        score = calculate_compliance_score(card)
        print("Calculated Score:")
        print(json.dumps(score.model_dump(), indent=2))
