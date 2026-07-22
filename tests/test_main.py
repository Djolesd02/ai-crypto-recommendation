import json

from scanner import main


def test_save_and_load_last_good(tmp_path, monkeypatch):
    f = tmp_path / "last_good.json"
    monkeypatch.setattr(main.config, "LAST_GOOD_FILE", str(f))
    payload = {"generated_at": 5, "count": 0, "coins": []}
    main.save_last_good(payload)
    assert main.load_last_good() == payload


def test_load_last_good_missing_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(main.config, "LAST_GOOD_FILE",
                        str(tmp_path / "nope.json"))
    assert main.load_last_good() is None


def test_run_once_pipeline(monkeypatch):
    from scanner.models import Candidate
    c = Candidate(chain="solana", address="A", symbol="S", name="N",
                  price_usd=0.001, price_change_m5=1.0, price_change_h1=20.0,
                  price_change_h24=50.0, volume_h1=8000.0, volume_h24=80000.0,
                  liquidity_usd=200000.0, pair_created_at=0, dex_url="http://d")
    monkeypatch.setattr(main.fetch_dex, "get_candidates", lambda: [c])
    monkeypatch.setattr(main.fetch_rugcheck, "get_reports", lambda addrs: {})
    published = {}
    monkeypatch.setattr(main.publish, "publish",
                        lambda payload, token: published.update(payload))
    monkeypatch.setattr(main, "save_last_good", lambda payload: None)

    result = main.run_once(token="t", now_ms=10 * 3_600_000)
    assert result["count"] == 1
    assert published["count"] == 1
