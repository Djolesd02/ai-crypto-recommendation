"""Scoring: normalize signals to 0-100, apply hard filters, rank top N."""
from scanner import config
from scanner.models import Candidate, RugReport, ScoredCoin


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def score_momentum(c: Candidate) -> float:
    """Blend of 1h price change and volume acceleration (hourly vs daily rate)."""
    price_part = clamp(c.price_change_h1, 0.0, config.PRICE_CHANGE_CAP)
    price_part = price_part / config.PRICE_CHANGE_CAP * 100.0

    if c.volume_h24 > 0:
        vol_accel = (c.volume_h1 * 24.0) / c.volume_h24
    else:
        vol_accel = 0.0
    vol_part = clamp((vol_accel - 1.0) / (config.VOL_ACCEL_CAP - 1.0), 0.0, 1.0) * 100.0

    return clamp(0.5 * price_part + 0.5 * vol_part, 0.0, 100.0)


def score_liquidity(c: Candidate) -> float:
    """Blend of liquidity depth and 24h volume, each scaled to a 'good' target."""
    liq_part = clamp(
        (c.liquidity_usd - config.MIN_LIQUIDITY_USD)
        / (config.LIQ_GOOD_USD - config.MIN_LIQUIDITY_USD),
        0.0, 1.0,
    ) * 100.0
    vol_part = clamp(
        (c.volume_h24 - config.MIN_VOLUME_H24)
        / (config.VOL_GOOD_USD - config.MIN_VOLUME_H24),
        0.0, 1.0,
    ) * 100.0
    return clamp(0.5 * liq_part + 0.5 * vol_part, 0.0, 100.0)


def score_freshness(c: Candidate, now_ms: int) -> float:
    """Piecewise: brand-new is risky, hours-to-2days is the sweet spot, old fades."""
    age_hours = (now_ms - c.pair_created_at) / 3_600_000.0
    if age_hours < 0:
        return 50.0
    if age_hours < 1:
        return 70.0
    if age_hours <= 48:
        return 100.0
    if age_hours <= 168:  # up to 7 days: fade 100 -> 40
        return clamp(100.0 - (age_hours - 48) / (168 - 48) * 60.0, 40.0, 100.0)
    return 30.0


def score_safety(rug: RugReport | None, c: Candidate, now_ms: int) -> float:
    """RugCheck score for Solana; a liquidity+age proxy when no report exists."""
    if rug is not None:
        return clamp(100.0 - rug.risk_normalised, 0.0, 100.0)

    # Proxy for non-Solana / unknown: deeper liquidity + older pair = safer.
    liq_part = clamp(c.liquidity_usd / config.LIQ_GOOD_USD, 0.0, 1.0) * 100.0
    age_hours = max(0.0, (now_ms - c.pair_created_at) / 3_600_000.0)
    age_part = clamp(age_hours / 168.0, 0.0, 1.0) * 100.0   # 7 days = full marks
    proxy = 0.6 * liq_part + 0.4 * age_part
    # Keep proxy in the "unknown/medium" band so it never reads as fully safe.
    return clamp(proxy, 0.0, 65.0)


def passes_hard_filters(c: Candidate, rug: RugReport | None) -> bool:
    if c.price_usd <= 0:
        return False
    if c.liquidity_usd < config.MIN_LIQUIDITY_USD:
        return False
    if c.volume_h24 < config.MIN_VOLUME_H24:
        return False
    if rug is not None and rug.danger:
        return False
    return True


def risk_level(safety: float, rug: RugReport | None) -> str:
    if rug is not None and rug.danger:
        return "high"
    if safety >= config.RISK_LOW_MIN:
        return "low"
    if safety >= config.RISK_MEDIUM_MIN:
        return "medium"
    return "high"


def _rugcheck_url(c: Candidate) -> str | None:
    if c.chain == "solana":
        return f"https://rugcheck.xyz/tokens/{c.address}"
    return None


def rank_top(
    candidates: list[Candidate],
    rug_by_addr: dict[str, RugReport],
    now_ms: int,
) -> list[ScoredCoin]:
    scored: list[ScoredCoin] = []
    for c in candidates:
        rug = rug_by_addr.get(c.address)
        if not passes_hard_filters(c, rug):
            continue
        m = score_momentum(c)
        liq = score_liquidity(c)
        saf = score_safety(rug, c, now_ms)
        fr = score_freshness(c, now_ms)
        total = (
            config.WEIGHTS["momentum"] * m
            + config.WEIGHTS["liquidity"] * liq
            + config.WEIGHTS["safety"] * saf
            + config.WEIGHTS["freshness"] * fr
        )
        scored.append(ScoredCoin(
            candidate=c, momentum=round(m, 1), liquidity=round(liq, 1),
            safety=round(saf, 1), freshness=round(fr, 1), total=round(total, 1),
            risk_level=risk_level(saf, rug), rugcheck_url=_rugcheck_url(c),
        ))
    scored.sort(key=lambda s: s.total, reverse=True)
    return scored[: config.TOP_N]
