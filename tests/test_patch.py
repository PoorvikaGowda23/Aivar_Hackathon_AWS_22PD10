"""
Unit tests for Feature 4: Card Update PATCH endpoint (app/main.py).
"""

from __future__ import annotations

import sys
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

APP_DIR = Path(__file__).parent.parent / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from main import app
from database import init_db

client = TestClient(app)


def setup_module():
    init_db()


def test_patch_card_flow():
    # 1. Generate an initial card using fixtures
    root = Path(__file__).parent.parent
    fixtures_dir = root / "fixtures" / "simple"

    with open(fixtures_dir / "agent_config.json", "rb") as f_cfg, \
         open(fixtures_dir / "tool_manifest.json", "rb") as f_man, \
         open(fixtures_dir / "run_trace.json", "rb") as f_tra:
        
        response = client.post(
            "/agents/cards/generate",
            files={
                "config_file": ("agent_config.json", f_cfg, "application/json"),
                "manifest_file": ("tool_manifest.json", f_man, "application/json"),
                "trace_file": ("run_trace.json", f_tra, "application/json"),
            },
        )
    
    assert response.status_code == 201
    gen_data = response.json()
    agent_id = gen_data["agent_id"]
    initial_version = gen_data["version"]

    # 2. Issue a PATCH update to update human oversight & incident contact
    patch_payload = {
        "human_oversight": [
            {
                "description": "All high risk operations require 2-person managerial sign-off",
                "trigger": "Transactions > $5,000"
            }
        ],
        "incident_contact": {
            "name": "SecOps Escalation Team",
            "email": "secops-escalation@example.com",
            "escalation_path": "PagerDuty #secops-critical"
        }
    }

    patch_resp = client.patch(f"/agents/cards/{agent_id}", json=patch_payload)
    assert patch_resp.status_code == 200
    patch_data = patch_resp.json()

    assert patch_data["agent_id"] == agent_id
    assert patch_data["previous_version"] == initial_version
    assert patch_data["new_version"] == initial_version + 1
    assert "human_oversight" in patch_data["updated_fields"]
    assert "incident_contact" in patch_data["updated_fields"]

    # 3. Verify card history has 2 versions
    history_resp = client.get("/agents")
    assert history_resp.status_code == 200
    agents = history_resp.json()["agents"]
    matching = [a for a in agents if a["agent_id"] == agent_id]
    assert len(matching) == 1
    assert matching[0]["latest_version"] == initial_version + 1
