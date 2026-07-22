import json
from pathlib import Path

from scanner import fetch_rugcheck

FIX = Path(__file__).parent / "fixtures" / "rugcheck_summary.json"


def test_parse_summary_maps_fields():
    data = json.loads(FIX.read_text())
    r = fetch_rugcheck.parse_summary("MINT123", data)
    assert r.address == "MINT123"
    assert r.risk_normalised == 82
    assert r.danger is True
    assert "Large amount of LP unlocked" in r.top_risk_names


def test_parse_summary_no_danger():
    data = {"score_normalised": 15, "risks": [{"name": "Minor", "level": "warn"}]}
    r = fetch_rugcheck.parse_summary("M", data)
    assert r.danger is False
    assert r.risk_normalised == 15


def test_parse_summary_missing_fields_defaults_safe_side():
    r = fetch_rugcheck.parse_summary("M", {})
    assert r.risk_normalised == 50.0   # unknown -> medium
    assert r.danger is False
    assert r.top_risk_names == []
