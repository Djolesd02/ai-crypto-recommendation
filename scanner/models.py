"""Typed data structures passed between modules."""
from dataclasses import dataclass


@dataclass
class Candidate:
    chain: str
    address: str
    symbol: str
    name: str
    price_usd: float
    price_change_m5: float
    price_change_h1: float
    price_change_h24: float
    volume_h1: float
    volume_h24: float
    liquidity_usd: float
    pair_created_at: int   # unix ms
    dex_url: str


@dataclass
class RugReport:
    address: str
    risk_normalised: float   # 0-100, higher = riskier
    danger: bool
    top_risk_names: list[str]


@dataclass
class ScoredCoin:
    candidate: Candidate
    momentum: float
    liquidity: float
    safety: float
    freshness: float
    total: float
    risk_level: str          # "low" | "medium" | "high"
    rugcheck_url: str | None
