import pytest

from scanner import build_data
from scanner.models import Candidate, ScoredCoin


def make_scored(rank_hint=0):
    c = Candidate(
        chain="solana", address=f"A{rank_hint}", symbol=f"S{rank_hint}", name="N",
        price_usd=0.001, price_change_m5=1.0, price_change_h1=10.0,
        price_change_h24=50.0, volume_h1=5000.0, volume_h24=80000.0,
        liquidity_usd=40000.0, pair_created_at=0, dex_url="http://dex",
    )
    return ScoredCoin(candidate=c, momentum=80.0, liquidity=60.0, safety=70.0,
                      freshness=90.0, total=float(100 - rank_hint), risk_level="low",
                      rugcheck_url="http://rug")


def test_build_payload_structure():
    coins = [make_scored(0), make_scored(1)]
    p = build_data.build_payload(coins, generated_at_ms=1234)
    assert p["generated_at"] == 1234
    assert p["count"] == 2
    assert p["coins"][0]["rank"] == 1
    assert p["coins"][1]["rank"] == 2
    assert p["coins"][0]["symbol"] == "S0"
    assert p["coins"][0]["risk_level"] == "low"
    assert p["coins"][0]["dex_url"] == "http://dex"


def test_validate_payload_accepts_good():
    p = build_data.build_payload([make_scored(0)], generated_at_ms=1)
    build_data.validate_payload(p)  # must not raise


def test_validate_payload_rejects_missing_key():
    with pytest.raises(ValueError):
        build_data.validate_payload({"coins": []})


def test_validate_payload_rejects_bad_coin():
    bad = {"generated_at": 1, "count": 1, "coins": [{"symbol": "X"}]}
    with pytest.raises(ValueError):
        build_data.validate_payload(bad)
