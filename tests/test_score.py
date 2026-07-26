from scanner import score
from scanner.models import Candidate, RugReport


def make_candidate(**kw):
    base = dict(
        chain="solana", address="AbC123", symbol="DOGE2", name="Doge Two",
        price_usd=0.0001, price_change_m5=1.0, price_change_h1=10.0,
        price_change_h24=50.0, volume_h1=5000.0, volume_h24=80000.0,
        liquidity_usd=40000.0, pair_created_at=0, dex_url="http://x",
    )
    base.update(kw)
    return Candidate(**base)


def test_clamp():
    assert score.clamp(150, 0, 100) == 100
    assert score.clamp(-5, 0, 100) == 0
    assert score.clamp(50, 0, 100) == 50


def test_momentum_rises_with_price_and_volume():
    calm = make_candidate(price_change_h1=0.0, volume_h1=1000.0, volume_h24=24000.0)
    hot = make_candidate(price_change_h1=80.0, volume_h1=8000.0, volume_h24=24000.0)
    assert score.score_momentum(hot) > score.score_momentum(calm)


def test_momentum_bounded_0_100():
    extreme = make_candidate(price_change_h1=9999.0, volume_h1=1e9, volume_h24=1.0)
    s = score.score_momentum(extreme)
    assert 0.0 <= s <= 100.0


def test_momentum_negative_price_change_not_negative():
    dumping = make_candidate(price_change_h1=-90.0, volume_h1=0.0, volume_h24=24000.0)
    assert score.score_momentum(dumping) >= 0.0


def test_liquidity_rises_with_liquidity_and_volume():
    thin = make_candidate(liquidity_usd=15000.0, volume_h24=25000.0)
    deep = make_candidate(liquidity_usd=400000.0, volume_h24=800000.0)
    assert score.score_liquidity(deep) > score.score_liquidity(thin)


def test_freshness_sweet_spot_beats_old():
    now = 1_000_000_000_000
    hour = 3_600_000
    fresh = make_candidate(pair_created_at=now - 12 * hour)   # 12h old
    old = make_candidate(pair_created_at=now - 30 * 24 * hour)  # 30d old
    assert score.score_freshness(fresh, now) > score.score_freshness(old, now)


def test_safety_uses_rugcheck_when_present():
    now = 1_000_000_000_000
    safe = RugReport(address="a", risk_normalised=10.0, danger=False, top_risk_names=[])
    risky = RugReport(address="a", risk_normalised=90.0, danger=False, top_risk_names=[])
    c = make_candidate()
    assert score.score_safety(safe, c, now) > score.score_safety(risky, c, now)


def test_safety_none_is_neutral():
    now = 1_000_000_000_000
    c = make_candidate(chain="ethereum")
    s = score.score_safety(None, c, now)
    assert 30.0 <= s <= 70.0


def test_hard_filter_drops_low_liquidity():
    c = make_candidate(liquidity_usd=500.0)
    assert score.passes_hard_filters(c, None) is False


def test_hard_filter_drops_low_volume():
    c = make_candidate(volume_h24=100.0)
    assert score.passes_hard_filters(c, None) is False


def test_hard_filter_drops_danger_token():
    c = make_candidate()
    danger = RugReport(address="a", risk_normalised=95.0, danger=True, top_risk_names=["Mint"])
    assert score.passes_hard_filters(c, danger) is False


def test_hard_filter_keeps_unknown_rug():
    c = make_candidate()
    assert score.passes_hard_filters(c, None) is True


def test_risk_level_bands():
    assert score.risk_level(80.0, None) == "low"
    assert score.risk_level(50.0, None) == "medium"
    assert score.risk_level(20.0, None) == "high"


def test_rank_top_filters_and_limits():
    now = 1_000_000_000_000
    good = [make_candidate(address=f"a{i}", symbol=f"S{i}",
                           price_change_h1=float(i), volume_h1=8000.0,
                           volume_h24=80000.0, liquidity_usd=200000.0,
                           pair_created_at=now - 10 * 3_600_000)
            for i in range(15)]
    scam = make_candidate(address="scam", liquidity_usd=100.0)  # fails filter
    result = score.rank_top(good + [scam], {}, now)
    assert len(result) == 10
    addrs = [s.candidate.address for s in result]
    assert "scam" not in addrs


def test_rank_top_sorted_descending():
    now = 1_000_000_000_000
    cands = [make_candidate(address=f"a{i}", price_change_h1=float(i * 5),
                            volume_h1=8000.0, volume_h24=80000.0,
                            liquidity_usd=200000.0,
                            pair_created_at=now - 10 * 3_600_000)
             for i in range(5)]
    result = score.rank_top(cands, {}, now)
    totals = [s.total for s in result]
    assert totals == sorted(totals, reverse=True)


def test_rank_top_applies_rugcheck():
    now = 1_000_000_000_000
    c = make_candidate(address="sol1", chain="solana",
                       liquidity_usd=200000.0, volume_h24=80000.0,
                       pair_created_at=now - 10 * 3_600_000)
    danger = RugReport(address="sol1", risk_normalised=99.0, danger=True,
                       top_risk_names=["Freeze"])
    result = score.rank_top([c], {"sol1": danger}, now)
    assert result == []
