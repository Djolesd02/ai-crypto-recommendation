"""Assemble and validate the data.json payload the site consumes."""
from scanner.models import ScoredCoin

REQUIRED_TOP = {"generated_at", "count", "coins"}
REQUIRED_COIN = {
    "rank", "symbol", "name", "chain", "address", "price_usd",
    "change_m5", "change_h1", "change_h24", "volume_h24", "liquidity_usd",
    "total", "momentum", "liquidity", "safety", "freshness", "risk_level",
    "dex_url", "rugcheck_url",
}


def build_payload(coins: list[ScoredCoin], generated_at_ms: int) -> dict:
    out = []
    for rank, s in enumerate(coins, start=1):
        c = s.candidate
        out.append({
            "rank": rank,
            "symbol": c.symbol,
            "name": c.name,
            "chain": c.chain,
            "address": c.address,
            "price_usd": c.price_usd,
            "change_m5": c.price_change_m5,
            "change_h1": c.price_change_h1,
            "change_h24": c.price_change_h24,
            "volume_h24": c.volume_h24,
            "liquidity_usd": c.liquidity_usd,
            "total": s.total,
            "momentum": s.momentum,
            "liquidity": s.liquidity,
            "safety": s.safety,
            "freshness": s.freshness,
            "risk_level": s.risk_level,
            "dex_url": c.dex_url,
            "rugcheck_url": s.rugcheck_url,
        })
    return {"generated_at": generated_at_ms, "count": len(out), "coins": out}


def validate_payload(payload: dict) -> None:
    if not isinstance(payload, dict) or not REQUIRED_TOP.issubset(payload):
        raise ValueError(f"payload missing top-level keys: {REQUIRED_TOP}")
    if not isinstance(payload["coins"], list):
        raise ValueError("coins must be a list")
    if payload["count"] != len(payload["coins"]):
        raise ValueError("count does not match number of coins")
    for coin in payload["coins"]:
        missing = REQUIRED_COIN - set(coin)
        if missing:
            raise ValueError(f"coin missing keys: {missing}")
