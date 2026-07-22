from scanner.models import Candidate, RugReport, ScoredCoin


def make_candidate(**kw):
    base = dict(
        chain="solana", address="AbC123", symbol="DOGE2", name="Doge Two",
        price_usd=0.0001, price_change_m5=1.0, price_change_h1=10.0,
        price_change_h24=50.0, volume_h1=5000.0, volume_h24=80000.0,
        liquidity_usd=40000.0, pair_created_at=1_700_000_000_000, dex_url="http://x",
    )
    base.update(kw)
    return Candidate(**base)


def test_candidate_fields():
    c = make_candidate()
    assert c.symbol == "DOGE2"
    assert c.liquidity_usd == 40000.0


def test_rugreport_fields():
    r = RugReport(address="AbC123", risk_normalised=20.0, danger=False,
                  top_risk_names=["Low LP"])
    assert r.danger is False


def test_scoredcoin_fields():
    c = make_candidate()
    s = ScoredCoin(candidate=c, momentum=80.0, liquidity=60.0, safety=70.0,
                   freshness=90.0, total=75.0, risk_level="low", rugcheck_url=None)
    assert s.total == 75.0
    assert s.candidate.symbol == "DOGE2"
