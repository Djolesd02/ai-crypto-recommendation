import json
from pathlib import Path

from scanner import fetch_dex

FIX = Path(__file__).parent / "fixtures" / "dex_tokens.json"


def load():
    return json.loads(FIX.read_text())


def test_parse_pair_maps_fields():
    pair = load()["pairs"][0]
    c = fetch_dex.parse_pair(pair)
    assert c.chain == "solana"
    assert c.address == "SOL_TOKEN_1"
    assert c.symbol == "PEPE2"
    assert c.price_usd == 0.00012
    assert c.price_change_h1 == 30.0
    assert c.volume_h24 == 240000
    assert c.liquidity_usd == 85000
    assert c.pair_created_at == 1700000000000


def test_best_candidates_dedupes_by_highest_liquidity():
    cands = fetch_dex.best_candidates(load())
    sol = [c for c in cands if c.address == "SOL_TOKEN_1"]
    assert len(sol) == 1
    assert sol[0].liquidity_usd == 85000  # kept the deeper pair


def test_best_candidates_filters_disallowed_chain():
    cands = fetch_dex.best_candidates(load())
    chains = {c.chain for c in cands}
    assert "fantom" not in chains
    assert "solana" in chains and "ethereum" in chains


def test_parse_pair_handles_missing_fields():
    pair = {"chainId": "solana", "baseToken": {"address": "X", "symbol": "X", "name": "X"}}
    c = fetch_dex.parse_pair(pair)
    assert c.price_usd == 0.0
    assert c.liquidity_usd == 0.0
    assert c.pair_created_at == 0
