# Crypto Scanner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Local Python script that scans Solana memecoins + low-cap altcoins every 15 minutes, scores them by momentum/liquidity/safety/freshness, filters out scams via RugCheck, and publishes the top 10 as `data.json` to GitHub, where a static Vercel site displays them.

**Architecture:** A local Python package (`scanner/`) fetches candidates from DexScreener, checks Solana tokens against RugCheck, applies hard scam filters, scores survivors, and PUTs `data.json` to a dedicated `data` branch on GitHub via the Contents API. A static site (`site/`) fetches that JSON directly from raw.githubusercontent.com and re-renders every 15 minutes, showing a "last updated" freshness indicator.

**Tech Stack:** Python 3.11+, `requests`, `pytest`, `python-dotenv`; plain HTML/CSS/JS static site; GitHub Contents API; Vercel static hosting.

## Global Constraints

- Python version floor: 3.11 (uses `X | None` union syntax, `tomllib` not required).
- All external data sources must be free and keyless except GitHub (GitHub uses a Personal Access Token stored locally in `.env`, never committed).
- Repo: `Djolesd02/ai-crypto-recommendation`. Data lives on branch `data`, file `data.json`. Site deploys from `main`.
- `data.json` must ALWAYS be valid JSON with the documented schema; never publish a partial/broken payload. On any cycle failure, keep the last good payload.
- RugCheck is a HARD filter for Solana tokens flagged `danger`; unreachable RugCheck = "unknown risk" (medium), NOT dropped.
- Scoring weights (in `config.py`, tunable): momentum 0.35, liquidity 0.30, safety 0.20, freshness 0.15. Top N = 10.
- Never commit secrets. `.env` is gitignored.
- All code, commit messages, and code comments in English; user-facing site text in Serbian (Latin).
- Disclaimer required on the site: not investment advice.

---

## File Structure

```
ai-crypto-recommendation/            (local folder: "AI CRYPTO")
├── scanner/
│   ├── __init__.py
│   ├── config.py            # weights, thresholds, repo info, chains
│   ├── models.py            # Candidate, RugReport, ScoredCoin dataclasses
│   ├── fetch_dex.py         # DexScreener: boosted tokens + pair data → Candidate
│   ├── fetch_rugcheck.py    # RugCheck: Solana token report → RugReport
│   ├── score.py             # normalization, hard filters, ranking → top 10
│   ├── build_data.py        # assemble + validate data.json payload
│   ├── publish.py           # PUT data.json to GitHub data branch
│   └── main.py              # 15-min loop, orchestration, keep-last-good
├── tests/
│   ├── __init__.py
│   ├── fixtures/
│   │   ├── dex_tokens.json
│   │   └── rugcheck_summary.json
│   ├── test_score.py
│   ├── test_build_data.py
│   ├── test_fetch_dex.py
│   ├── test_fetch_rugcheck.py
│   └── test_publish.py
├── site/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── requirements.txt
├── .gitignore
├── .env.example
├── vercel.json
└── README.md
```

---

## Task 1: Project scaffolding + config

**Files:**
- Create: `.gitignore`, `requirements.txt`, `.env.example`, `scanner/__init__.py`, `tests/__init__.py`, `scanner/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `scanner.config` module with constants `WEIGHTS: dict[str, float]`, `TOP_N: int`, `MIN_LIQUIDITY_USD: float`, `MIN_VOLUME_H24: float`, `REFRESH_SECONDS: int`, `ALLOWED_CHAINS: set[str]`, `GITHUB_OWNER: str`, `GITHUB_REPO: str`, `DATA_BRANCH: str`, `DATA_PATH: str`, and normalization thresholds used by `score.py`.

- [ ] **Step 1: Initialize git and remote**

Run in the project root (`C:\Users\iwanmf\Desktop\FON\AI CRYPTO`):
```bash
git init
git branch -M main
git remote add origin https://github.com/Djolesd02/ai-crypto-recommendation.git
```
Expected: no errors; `git remote -v` shows origin.

- [ ] **Step 2: Create Python virtual environment**

```bash
python -m venv .venv
```
Then activate (PowerShell): `.\.venv\Scripts\Activate.ps1`
Expected: prompt shows `(.venv)`.

- [ ] **Step 3: Write `.gitignore`**

```gitignore
.venv/
__pycache__/
*.pyc
.env
last_good.json
scanner.log
.pytest_cache/
```

- [ ] **Step 4: Write `requirements.txt`**

```
requests==2.32.3
python-dotenv==1.0.1
pytest==8.3.3
```

- [ ] **Step 5: Install dependencies**

```bash
pip install -r requirements.txt
```
Expected: installs without error.

- [ ] **Step 6: Write `.env.example`**

```
# Copy to .env and fill in. .env is gitignored.
# GitHub Personal Access Token with "Contents: read and write" permission
# on the ai-crypto-recommendation repo.
GITHUB_TOKEN=your_token_here
```

- [ ] **Step 7: Create empty package markers**

`scanner/__init__.py` — empty file.
`tests/__init__.py` — empty file.

- [ ] **Step 8: Write the failing test for config**

`tests/test_config.py`:
```python
from scanner import config


def test_weights_sum_to_one():
    assert abs(sum(config.WEIGHTS.values()) - 1.0) < 1e-9


def test_weight_keys():
    assert set(config.WEIGHTS) == {"momentum", "liquidity", "safety", "freshness"}


def test_top_n_is_ten():
    assert config.TOP_N == 10


def test_repo_constants():
    assert config.GITHUB_OWNER == "Djolesd02"
    assert config.GITHUB_REPO == "ai-crypto-recommendation"
    assert config.DATA_BRANCH == "data"
    assert config.DATA_PATH == "data.json"
```

- [ ] **Step 9: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scanner.config'`.

- [ ] **Step 10: Write `scanner/config.py`**

```python
"""Central configuration: scoring weights, filters, thresholds, repo info."""

# --- Scoring weights (must sum to 1.0) ---
WEIGHTS = {
    "momentum": 0.35,
    "liquidity": 0.30,
    "safety": 0.20,
    "freshness": 0.15,
}

TOP_N = 10

# --- Hard filters (candidates below these are dropped before scoring) ---
MIN_LIQUIDITY_USD = 10_000.0
MIN_VOLUME_H24 = 20_000.0

# --- Normalization thresholds (see score.py) ---
LIQ_GOOD_USD = 500_000.0        # liquidity considered "full marks"
VOL_GOOD_USD = 1_000_000.0      # 24h volume considered "full marks"
PRICE_CHANGE_CAP = 100.0        # cap 1h % change contribution at 100
VOL_ACCEL_CAP = 3.0             # hourly-vs-daily volume ratio cap

# --- Risk thresholds on safety score (0-100, higher = safer) ---
RISK_LOW_MIN = 70.0
RISK_MEDIUM_MIN = 40.0

# --- Runtime ---
REFRESH_SECONDS = 15 * 60
ALLOWED_CHAINS = {"solana", "ethereum", "bsc", "base"}
CANDIDATE_LIMIT = 150            # max candidates to score per cycle

# --- Publishing target ---
GITHUB_OWNER = "Djolesd02"
GITHUB_REPO = "ai-crypto-recommendation"
DATA_BRANCH = "data"
DATA_PATH = "data.json"
LAST_GOOD_FILE = "last_good.json"
```

- [ ] **Step 11: Run test to verify it passes**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS (4 tests).

- [ ] **Step 12: Commit**

```bash
git add .gitignore requirements.txt .env.example scanner/ tests/ docs/
git commit -m "chore: project scaffolding and config"
```

---

## Task 2: Data models

**Files:**
- Create: `scanner/models.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Produces:
  - `Candidate` dataclass: `chain: str, address: str, symbol: str, name: str, price_usd: float, price_change_m5: float, price_change_h1: float, price_change_h24: float, volume_h1: float, volume_h24: float, liquidity_usd: float, pair_created_at: int (ms), dex_url: str`
  - `RugReport` dataclass: `address: str, risk_normalised: float (0-100, higher=riskier), danger: bool, top_risk_names: list[str]`
  - `ScoredCoin` dataclass: `candidate: Candidate, momentum: float, liquidity: float, safety: float, freshness: float, total: float, risk_level: str, rugcheck_url: str | None`

- [ ] **Step 1: Write the failing test**

`tests/test_models.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scanner.models'`.

- [ ] **Step 3: Write `scanner/models.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_models.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add scanner/models.py tests/test_models.py
git commit -m "feat: add Candidate, RugReport, ScoredCoin models"
```

---

## Task 3: Scoring — momentum, liquidity, freshness

**Files:**
- Create: `scanner/score.py`
- Test: `tests/test_score.py`

**Interfaces:**
- Consumes: `Candidate` from `scanner.models`; thresholds from `scanner.config`.
- Produces:
  - `score_momentum(c: Candidate) -> float` (0-100)
  - `score_liquidity(c: Candidate) -> float` (0-100)
  - `score_freshness(c: Candidate, now_ms: int) -> float` (0-100)
  - helper `clamp(x: float, lo: float, hi: float) -> float`

- [ ] **Step 1: Write the failing test**

`tests/test_score.py`:
```python
from scanner import score
from scanner.models import Candidate


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_score.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scanner.score'`.

- [ ] **Step 3: Write `scanner/score.py` (partial — these three functions)**

```python
"""Scoring: normalize signals to 0-100, apply hard filters, rank top N."""
from scanner import config
from scanner.models import Candidate


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_score.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scanner/score.py tests/test_score.py
git commit -m "feat: momentum, liquidity, freshness scoring"
```

---

## Task 4: Scoring — safety, hard filters, risk level

**Files:**
- Modify: `scanner/score.py`
- Test: `tests/test_score.py` (add tests)

**Interfaces:**
- Consumes: `Candidate`, `RugReport` from `scanner.models`; thresholds from `scanner.config`.
- Produces:
  - `score_safety(rug: RugReport | None, c: Candidate, now_ms: int) -> float` (0-100, higher=safer)
  - `passes_hard_filters(c: Candidate, rug: RugReport | None) -> bool`
  - `risk_level(safety: float, rug: RugReport | None) -> str`

- [ ] **Step 1: Add failing tests to `tests/test_score.py`**

```python
from scanner.models import RugReport


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
```

- [ ] **Step 2: Run tests to verify new ones fail**

Run: `python -m pytest tests/test_score.py -v`
Expected: FAIL — `AttributeError: module 'scanner.score' has no attribute 'score_safety'`.

- [ ] **Step 3: Append to `scanner/score.py`**

```python
from scanner.models import RugReport


def score_safety(rug: "RugReport | None", c: Candidate, now_ms: int) -> float:
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


def passes_hard_filters(c: Candidate, rug: "RugReport | None") -> bool:
    if c.price_usd <= 0:
        return False
    if c.liquidity_usd < config.MIN_LIQUIDITY_USD:
        return False
    if c.volume_h24 < config.MIN_VOLUME_H24:
        return False
    if rug is not None and rug.danger:
        return False
    return True


def risk_level(safety: float, rug: "RugReport | None") -> str:
    if rug is not None and rug.danger:
        return "high"
    if safety >= config.RISK_LOW_MIN:
        return "low"
    if safety >= config.RISK_MEDIUM_MIN:
        return "medium"
    return "high"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_score.py -v`
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add scanner/score.py tests/test_score.py
git commit -m "feat: safety scoring, hard filters, risk levels"
```

---

## Task 5: Scoring — total + ranking (top 10)

**Files:**
- Modify: `scanner/score.py`
- Test: `tests/test_score.py` (add tests)

**Interfaces:**
- Consumes: `Candidate`, `RugReport`, `ScoredCoin`; weights from `config.WEIGHTS`; `config.TOP_N`.
- Produces:
  - `rank_top(candidates: list[Candidate], rug_by_addr: dict[str, RugReport], now_ms: int) -> list[ScoredCoin]` — filters, scores, sorts desc by total, returns at most `config.TOP_N`.

- [ ] **Step 1: Add failing tests to `tests/test_score.py`**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_score.py -v`
Expected: FAIL — `AttributeError: ... 'rank_top'`.

- [ ] **Step 3: Append to `scanner/score.py`**

```python
from scanner.models import ScoredCoin


def _rugcheck_url(c: Candidate) -> "str | None":
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
```

- [ ] **Step 4: Run the full scoring test file**

Run: `python -m pytest tests/test_score.py -v`
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add scanner/score.py tests/test_score.py
git commit -m "feat: rank_top combines signals and selects top 10"
```

---

## Task 6: DexScreener fetch + parse

**Files:**
- Create: `scanner/fetch_dex.py`, `tests/fixtures/dex_tokens.json`
- Test: `tests/test_fetch_dex.py`

**Interfaces:**
- Consumes: `Candidate` from `scanner.models`; `config.ALLOWED_CHAINS`, `config.CANDIDATE_LIMIT`.
- Produces:
  - `parse_pair(pair: dict) -> Candidate` — maps one DexScreener pair dict to a Candidate.
  - `best_candidates(token_response: dict) -> list[Candidate]` — from a `/latest/dex/tokens` response, picks the highest-liquidity pair per base-token address, filtered to allowed chains.
  - `get_candidates() -> list[Candidate]` — live: fetch boosted token addresses, batch-fetch their pairs, return candidates (network; not unit-tested).

- [ ] **Step 1: Create fixture `tests/fixtures/dex_tokens.json`**

```json
{
  "pairs": [
    {
      "chainId": "solana",
      "url": "https://dexscreener.com/solana/pair1",
      "baseToken": {"address": "SOL_TOKEN_1", "symbol": "PEPE2", "name": "Pepe Two"},
      "priceUsd": "0.00012",
      "priceChange": {"m5": 2.5, "h1": 30.0, "h24": 120.0},
      "volume": {"h1": 15000, "h24": 240000},
      "liquidity": {"usd": 85000},
      "pairCreatedAt": 1700000000000
    },
    {
      "chainId": "solana",
      "url": "https://dexscreener.com/solana/pair1b",
      "baseToken": {"address": "SOL_TOKEN_1", "symbol": "PEPE2", "name": "Pepe Two"},
      "priceUsd": "0.00012",
      "priceChange": {"m5": 2.5, "h1": 30.0, "h24": 120.0},
      "volume": {"h1": 5000, "h24": 40000},
      "liquidity": {"usd": 20000},
      "pairCreatedAt": 1700000000000
    },
    {
      "chainId": "ethereum",
      "url": "https://dexscreener.com/ethereum/pair2",
      "baseToken": {"address": "ETH_TOKEN_9", "symbol": "MOON", "name": "Mooncoin"},
      "priceUsd": "1.5",
      "priceChange": {"m5": 0.0, "h1": 5.0, "h24": 10.0},
      "volume": {"h1": 3000, "h24": 90000},
      "liquidity": {"usd": 300000},
      "pairCreatedAt": 1699000000000
    },
    {
      "chainId": "fantom",
      "url": "https://dexscreener.com/fantom/pair3",
      "baseToken": {"address": "FTM_TOKEN", "symbol": "SKIP", "name": "Skip Me"},
      "priceUsd": "0.5",
      "priceChange": {"m5": 0.0, "h1": 1.0, "h24": 2.0},
      "volume": {"h1": 100, "h24": 1000},
      "liquidity": {"usd": 5000},
      "pairCreatedAt": 1699000000000
    }
  ]
}
```

- [ ] **Step 2: Write the failing test**

`tests/test_fetch_dex.py`:
```python
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_fetch_dex.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scanner.fetch_dex'`.

- [ ] **Step 4: Write `scanner/fetch_dex.py`**

```python
"""Fetch trending tokens from DexScreener and map them to Candidates."""
import logging

import requests

from scanner import config
from scanner.models import Candidate

log = logging.getLogger(__name__)

BOOSTS_LATEST = "https://api.dexscreener.com/token-boosts/latest/v1"
BOOSTS_TOP = "https://api.dexscreener.com/token-boosts/top/v1"
TOKENS_URL = "https://api.dexscreener.com/latest/dex/tokens/{addresses}"
TIMEOUT = 15


def _f(x, default=0.0) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def parse_pair(pair: dict) -> Candidate:
    base = pair.get("baseToken", {})
    change = pair.get("priceChange", {}) or {}
    volume = pair.get("volume", {}) or {}
    liquidity = pair.get("liquidity", {}) or {}
    return Candidate(
        chain=pair.get("chainId", ""),
        address=base.get("address", ""),
        symbol=base.get("symbol", ""),
        name=base.get("name", ""),
        price_usd=_f(pair.get("priceUsd")),
        price_change_m5=_f(change.get("m5")),
        price_change_h1=_f(change.get("h1")),
        price_change_h24=_f(change.get("h24")),
        volume_h1=_f(volume.get("h1")),
        volume_h24=_f(volume.get("h24")),
        liquidity_usd=_f(liquidity.get("usd")),
        pair_created_at=int(pair.get("pairCreatedAt", 0) or 0),
        dex_url=pair.get("url", ""),
    )


def best_candidates(token_response: dict) -> list[Candidate]:
    """Highest-liquidity pair per base-token address, allowed chains only."""
    best: dict[str, Candidate] = {}
    for pair in token_response.get("pairs", []) or []:
        c = parse_pair(pair)
        if c.chain not in config.ALLOWED_CHAINS or not c.address:
            continue
        prev = best.get(c.address)
        if prev is None or c.liquidity_usd > prev.liquidity_usd:
            best[c.address] = c
    return list(best.values())


def _fetch_boosted_addresses() -> list[str]:
    addresses: list[str] = []
    for url in (BOOSTS_LATEST, BOOSTS_TOP):
        try:
            resp = requests.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
            for item in resp.json() or []:
                addr = item.get("tokenAddress")
                if addr and item.get("chainId") in config.ALLOWED_CHAINS:
                    addresses.append(addr)
        except requests.RequestException as e:
            log.warning("boosts fetch failed for %s: %s", url, e)
    # dedupe, keep order
    seen: set[str] = set()
    unique = [a for a in addresses if not (a in seen or seen.add(a))]
    return unique[: config.CANDIDATE_LIMIT]


def get_candidates() -> list[Candidate]:
    """Live entry point: boosted addresses -> pair data -> candidates."""
    addresses = _fetch_boosted_addresses()
    candidates: list[Candidate] = []
    for i in range(0, len(addresses), 30):
        chunk = addresses[i : i + 30]
        url = TOKENS_URL.format(addresses=",".join(chunk))
        try:
            resp = requests.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
            candidates.extend(best_candidates(resp.json()))
        except requests.RequestException as e:
            log.warning("tokens fetch failed: %s", e)
    return candidates
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_fetch_dex.py -v`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add scanner/fetch_dex.py tests/test_fetch_dex.py tests/fixtures/dex_tokens.json
git commit -m "feat: DexScreener fetch and candidate parsing"
```

---

## Task 7: RugCheck fetch + parse

**Files:**
- Create: `scanner/fetch_rugcheck.py`, `tests/fixtures/rugcheck_summary.json`
- Test: `tests/test_fetch_rugcheck.py`

**Interfaces:**
- Consumes: `RugReport` from `scanner.models`.
- Produces:
  - `parse_summary(address: str, data: dict) -> RugReport` — maps a RugCheck summary response to RugReport (`risk_normalised` from `score_normalised`, `danger` if any risk level is "danger", `top_risk_names` = names of listed risks).
  - `get_reports(addresses: list[str]) -> dict[str, RugReport]` — live: fetch each Solana mint's summary (network; not unit-tested).

- [ ] **Step 1: Create fixture `tests/fixtures/rugcheck_summary.json`**

```json
{
  "score": 1500,
  "score_normalised": 82,
  "risks": [
    {"name": "Large amount of LP unlocked", "level": "danger", "score": 1000},
    {"name": "Top holder high ownership", "level": "warn", "score": 500}
  ]
}
```

- [ ] **Step 2: Write the failing test**

`tests/test_fetch_rugcheck.py`:
```python
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_fetch_rugcheck.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scanner.fetch_rugcheck'`.

- [ ] **Step 4: Write `scanner/fetch_rugcheck.py`**

```python
"""Fetch RugCheck risk summaries for Solana mints."""
import logging

import requests

from scanner.models import RugReport

log = logging.getLogger(__name__)

SUMMARY_URL = "https://api.rugcheck.xyz/v1/tokens/{mint}/report/summary"
TIMEOUT = 15


def parse_summary(address: str, data: dict) -> RugReport:
    risks = data.get("risks", []) or []
    normalised = data.get("score_normalised")
    if normalised is None:
        normalised = 50.0   # unknown -> medium band
    danger = any((r.get("level") == "danger") for r in risks)
    names = [r.get("name", "") for r in risks if r.get("name")]
    return RugReport(
        address=address,
        risk_normalised=float(normalised),
        danger=danger,
        top_risk_names=names,
    )


def get_reports(addresses: list[str]) -> dict[str, RugReport]:
    """Live: one summary request per Solana mint. Failures are skipped (unknown)."""
    reports: dict[str, RugReport] = {}
    for addr in addresses:
        try:
            resp = requests.get(SUMMARY_URL.format(mint=addr), timeout=TIMEOUT)
            resp.raise_for_status()
            reports[addr] = parse_summary(addr, resp.json())
        except requests.RequestException as e:
            log.warning("rugcheck failed for %s: %s", addr, e)
            # Leave absent -> treated as unknown risk downstream.
    return reports
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_fetch_rugcheck.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add scanner/fetch_rugcheck.py tests/test_fetch_rugcheck.py tests/fixtures/rugcheck_summary.json
git commit -m "feat: RugCheck summary fetch and parsing"
```

---

## Task 8: Build + validate data.json payload

**Files:**
- Create: `scanner/build_data.py`
- Test: `tests/test_build_data.py`

**Interfaces:**
- Consumes: `ScoredCoin` from `scanner.models`.
- Produces:
  - `build_payload(coins: list[ScoredCoin], generated_at_ms: int) -> dict` — schema: `{"generated_at": int, "count": int, "coins": [ {rank, symbol, name, chain, address, price_usd, change_m5, change_h1, change_h24, volume_h24, liquidity_usd, total, momentum, liquidity, safety, freshness, risk_level, dex_url, rugcheck_url} ]}`.
  - `validate_payload(payload: dict) -> None` — raises `ValueError` if schema/type invariants are violated.

- [ ] **Step 1: Write the failing test**

`tests/test_build_data.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_build_data.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scanner.build_data'`.

- [ ] **Step 3: Write `scanner/build_data.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_build_data.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add scanner/build_data.py tests/test_build_data.py
git commit -m "feat: build and validate data.json payload"
```

---

## Task 9: Publish to GitHub data branch

**Files:**
- Create: `scanner/publish.py`
- Test: `tests/test_publish.py`

**Interfaces:**
- Consumes: `config.GITHUB_OWNER/REPO/DATA_BRANCH/DATA_PATH`; `GITHUB_TOKEN` from env.
- Produces:
  - `build_put_body(payload: dict, sha: str | None) -> dict` — the JSON body for the Contents API PUT (base64 content, message, branch, and `sha` when updating).
  - `publish(payload: dict, token: str) -> None` — live: GET current file sha, PUT new content to the data branch (network; the body builder is unit-tested, the HTTP call is smoke-tested manually).

- [ ] **Step 1: Write the failing test**

`tests/test_publish.py`:
```python
import base64
import json

from scanner import publish


def test_build_put_body_encodes_content():
    payload = {"generated_at": 1, "count": 0, "coins": []}
    body = publish.build_put_body(payload, sha=None)
    decoded = base64.b64decode(body["content"]).decode()
    assert json.loads(decoded) == payload
    assert body["branch"] == "data"
    assert "message" in body
    assert "sha" not in body   # new file has no sha


def test_build_put_body_includes_sha_on_update():
    body = publish.build_put_body({"generated_at": 1, "count": 0, "coins": []},
                                  sha="abc123")
    assert body["sha"] == "abc123"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_publish.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scanner.publish'`.

- [ ] **Step 3: Write `scanner/publish.py`**

```python
"""Publish data.json to the GitHub data branch via the Contents API."""
import base64
import json
import logging

import requests

from scanner import config

log = logging.getLogger(__name__)

API = "https://api.github.com/repos/{owner}/{repo}/contents/{path}"
TIMEOUT = 20


def _url() -> str:
    return API.format(owner=config.GITHUB_OWNER, repo=config.GITHUB_REPO,
                      path=config.DATA_PATH)


def build_put_body(payload: dict, sha: "str | None") -> dict:
    content = json.dumps(payload, indent=2).encode()
    body = {
        "message": f"data: update at {payload.get('generated_at')}",
        "content": base64.b64encode(content).decode(),
        "branch": config.DATA_BRANCH,
    }
    if sha:
        body["sha"] = sha
    return body


def _get_current_sha(token: str) -> "str | None":
    headers = {"Authorization": f"Bearer {token}",
               "Accept": "application/vnd.github+json"}
    resp = requests.get(_url(), params={"ref": config.DATA_BRANCH},
                        headers=headers, timeout=TIMEOUT)
    if resp.status_code == 200:
        return resp.json().get("sha")
    return None


def publish(payload: dict, token: str) -> None:
    headers = {"Authorization": f"Bearer {token}",
               "Accept": "application/vnd.github+json"}
    sha = _get_current_sha(token)
    body = build_put_body(payload, sha)
    resp = requests.put(_url(), headers=headers, json=body, timeout=TIMEOUT)
    resp.raise_for_status()
    log.info("published data.json (%d coins)", payload.get("count", 0))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_publish.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add scanner/publish.py tests/test_publish.py
git commit -m "feat: publish data.json to GitHub data branch"
```

---

## Task 10: Orchestration loop with keep-last-good

**Files:**
- Create: `scanner/main.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: `fetch_dex.get_candidates`, `fetch_rugcheck.get_reports`, `score.rank_top`, `build_data.build_payload/validate_payload`, `publish.publish`; `config.*`.
- Produces:
  - `run_once(token: str, now_ms: int) -> dict` — one full cycle, returns the published payload.
  - `save_last_good(payload: dict) -> None` / `load_last_good() -> dict | None` — persist last valid payload to `config.LAST_GOOD_FILE`.
  - `main() -> None` — loop every `config.REFRESH_SECONDS`, catching exceptions so the loop never dies.

- [ ] **Step 1: Write the failing test**

`tests/test_main.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_main.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scanner.main'`.

- [ ] **Step 3: Write `scanner/main.py`**

```python
"""Orchestrate one scan cycle and run the 15-minute loop."""
import json
import logging
import os
import time

from dotenv import load_dotenv

from scanner import build_data, config, fetch_dex, fetch_rugcheck, publish, score

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.FileHandler("scanner.log"), logging.StreamHandler()],
)
log = logging.getLogger("scanner.main")


def save_last_good(payload: dict) -> None:
    with open(config.LAST_GOOD_FILE, "w", encoding="utf-8") as fh:
        json.dump(payload, fh)


def load_last_good() -> "dict | None":
    try:
        with open(config.LAST_GOOD_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def run_once(token: str, now_ms: int) -> dict:
    candidates = fetch_dex.get_candidates()
    log.info("fetched %d candidates", len(candidates))
    sol_addrs = [c.address for c in candidates if c.chain == "solana"]
    rug_by_addr = fetch_rugcheck.get_reports(sol_addrs)
    top = score.rank_top(candidates, rug_by_addr, now_ms)
    payload = build_data.build_payload(top, generated_at_ms=now_ms)
    build_data.validate_payload(payload)
    publish.publish(payload, token)
    save_last_good(payload)
    return payload


def main() -> None:
    load_dotenv()
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN not set. Copy .env.example to .env.")
    while True:
        try:
            run_once(token, now_ms=int(time.time() * 1000))
        except Exception:  # noqa: BLE001 - loop must never die
            log.exception("cycle failed; keeping last good data")
        time.sleep(config.REFRESH_SECONDS)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_main.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Run the full test suite**

Run: `python -m pytest -v`
Expected: PASS (all files).

- [ ] **Step 6: Commit**

```bash
git add scanner/main.py tests/test_main.py
git commit -m "feat: orchestration loop with keep-last-good"
```

---

## Task 11: Static site (fetch, render, refresh, states)

**Files:**
- Create: `site/index.html`, `site/style.css`, `site/app.js`

**Interfaces:**
- Consumes: `data.json` from `https://raw.githubusercontent.com/Djolesd02/ai-crypto-recommendation/data/data.json` (schema from Task 8).
- Produces: a static page that renders the top 10, shows freshness, auto-refreshes every 15 min, and degrades gracefully.

- [ ] **Step 1: Write `site/index.html`**

```html
<!doctype html>
<html lang="sr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Crypto Scanner — Top 10</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <header class="topbar">
    <h1>Top 10 coina za brzu priliku</h1>
    <div id="status" class="status">Učitavanje…</div>
  </header>
  <main id="list" class="list" aria-live="polite"></main>
  <footer class="disclaimer">
    Nije investicioni savet. Kripto je visokorizičan — možeš izgubiti sve što uložiš.
    Podaci sa DexScreener-a i RugCheck-a; proveri sam pre bilo kakve odluke.
  </footer>
  <script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Write `site/style.css`**

```css
:root {
  --bg: #0b0e14; --card: #151a23; --line: #232a36;
  --text: #e6e9ef; --muted: #8b93a3;
  --up: #2ecc71; --down: #ff5c5c;
  --low: #2ecc71; --medium: #f1c40f; --high: #ff5c5c;
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--text);
  font: 15px/1.4 system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
}
.topbar {
  display: flex; flex-wrap: wrap; gap: 8px 16px;
  align-items: baseline; justify-content: space-between;
  padding: 18px 20px; border-bottom: 1px solid var(--line);
}
.topbar h1 { font-size: 18px; margin: 0; }
.status { font-size: 13px; color: var(--muted); }
.status.fresh { color: var(--up); }
.status.stale { color: var(--medium); }
.status.error { color: var(--high); }
.list { display: grid; gap: 12px; padding: 16px; max-width: 820px; margin: 0 auto; }
.card {
  background: var(--card); border: 1px solid var(--line);
  border-radius: 12px; padding: 14px 16px;
  display: grid; grid-template-columns: 40px 1fr auto; gap: 4px 14px; align-items: center;
}
.rank { font-size: 22px; font-weight: 700; color: var(--muted); }
.name { font-weight: 600; }
.name .sym { font-size: 16px; }
.name .full { color: var(--muted); font-size: 12px; margin-left: 6px; }
.meta { color: var(--muted); font-size: 12px; grid-column: 2; }
.changes { grid-column: 2; display: flex; gap: 12px; font-size: 13px; margin-top: 2px; }
.up { color: var(--up); } .down { color: var(--down); }
.right { grid-column: 3; grid-row: 1 / span 3; text-align: right; }
.total { font-size: 26px; font-weight: 700; }
.risk { font-size: 12px; padding: 2px 8px; border-radius: 999px; display: inline-block; margin-top: 4px; }
.risk.low { background: rgba(46,204,113,.15); color: var(--low); }
.risk.medium { background: rgba(241,196,15,.15); color: var(--medium); }
.risk.high { background: rgba(255,92,92,.15); color: var(--high); }
.breakdown { grid-column: 2; font-size: 11px; color: var(--muted); margin-top: 4px; }
.links { grid-column: 1 / -1; display: flex; gap: 14px; margin-top: 8px; }
.links a { color: #6ea8ff; text-decoration: none; font-size: 13px; }
.disclaimer { color: var(--muted); font-size: 12px; text-align: center; padding: 20px; max-width: 640px; margin: 0 auto; }
@media (max-width: 520px) {
  .card { grid-template-columns: 32px 1fr; }
  .right { grid-column: 2; grid-row: auto; text-align: left; margin-top: 6px; }
}
```

- [ ] **Step 3: Write `site/app.js`**

```javascript
const DATA_URL =
  "https://raw.githubusercontent.com/Djolesd02/ai-crypto-recommendation/data/data.json";
const REFRESH_MS = 15 * 60 * 1000;

const fmtPrice = (p) =>
  p >= 1 ? "$" + p.toFixed(2) : "$" + Number(p).toPrecision(3);
const fmtUsd = (n) =>
  n >= 1e6 ? "$" + (n / 1e6).toFixed(1) + "M"
  : n >= 1e3 ? "$" + (n / 1e3).toFixed(0) + "k"
  : "$" + Math.round(n);
const chg = (v) => {
  const cls = v >= 0 ? "up" : "down";
  const sign = v >= 0 ? "+" : "";
  return `<span class="${cls}">${sign}${v.toFixed(1)}%</span>`;
};

function setStatus(text, cls) {
  const el = document.getElementById("status");
  el.textContent = text;
  el.className = "status " + (cls || "");
}

function agoMinutes(generatedAt) {
  return Math.round((Date.now() - generatedAt) / 60000);
}

function render(payload) {
  const list = document.getElementById("list");
  list.innerHTML = "";
  for (const c of payload.coins) {
    const el = document.createElement("div");
    el.className = "card";
    el.innerHTML = `
      <div class="rank">#${c.rank}</div>
      <div class="name"><span class="sym">${c.symbol}</span>
        <span class="full">${c.name} · ${c.chain}</span></div>
      <div class="right">
        <div class="total">${c.total}</div>
        <span class="risk ${c.risk_level}">${c.risk_level}</span>
      </div>
      <div class="meta">${fmtPrice(c.price_usd)} · Likv ${fmtUsd(c.liquidity_usd)} · Vol24h ${fmtUsd(c.volume_h24)}</div>
      <div class="changes">5m ${chg(c.change_m5)} · 1h ${chg(c.change_h1)} · 24h ${chg(c.change_h24)}</div>
      <div class="breakdown">Momentum ${c.momentum} · Likvidnost ${c.liquidity} · Bezbednost ${c.safety} · Svežina ${c.freshness}</div>
      <div class="links">
        <a href="${c.dex_url}" target="_blank" rel="noopener">Grafikon (DexScreener)</a>
        ${c.rugcheck_url ? `<a href="${c.rugcheck_url}" target="_blank" rel="noopener">Bezbednost (RugCheck)</a>` : ""}
      </div>`;
    list.appendChild(el);
  }
}

async function load() {
  try {
    const resp = await fetch(DATA_URL + "?t=" + Date.now(), { cache: "no-store" });
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    const payload = await resp.json();
    render(payload);
    const mins = agoMinutes(payload.generated_at);
    if (mins <= 20) setStatus(`Ažurirano pre ${mins} min`, "fresh");
    else setStatus(`Ažurirano pre ${mins} min — skripta je možda ugašena`, "stale");
  } catch (e) {
    setStatus("Ne mogu da dohvatim sveže podatke. Prikaz je možda prazan/star.", "error");
  }
}

load();
setInterval(load, REFRESH_MS);
```

- [ ] **Step 4: Manually verify the page renders**

Create a temporary `site/data.json` matching the schema (2-3 sample coins), temporarily point `DATA_URL` to `"data.json"`, then serve:
```bash
python -m http.server 8000 --directory site
```
Open `http://localhost:8000`. Expected: cards render, changes are colored, risk pill shows, "Ažurirano pre X min" appears. Then revert `DATA_URL` to the raw GitHub URL and delete the temporary `site/data.json`.

- [ ] **Step 5: Commit**

```bash
git add site/index.html site/style.css site/app.js
git commit -m "feat: static site renders top 10 with freshness and states"
```

---

## Task 12: Vercel config, README, one-time setup docs

**Files:**
- Create: `vercel.json`, `README.md`

**Interfaces:** none (documentation + deploy config).

- [ ] **Step 1: Write `vercel.json`**

```json
{
  "buildCommand": null,
  "outputDirectory": "site",
  "framework": null,
  "cleanUrls": true
}
```

- [ ] **Step 2: Write `README.md`**

```markdown
# AI Crypto Recommendation

Local Python scanner that finds low-cap / memecoin opportunities (Solana + EVM),
scores them, filters scams via RugCheck, and publishes the top 10 to a static site.

> Not investment advice. Crypto is high-risk. You can lose everything.

## How it works
- `scanner/` runs locally every 15 minutes, writes `data.json`, and PUTs it to
  the `data` branch on GitHub.
- `site/` is a static page deployed on Vercel that reads `data.json` from the
  `data` branch and refreshes every 15 minutes.

## One-time setup

### 1. Create the `data` branch (holds data.json, separate from code)
```bash
git checkout --orphan data
git rm -rf .
echo '{"generated_at":0,"count":0,"coins":[]}' > data.json
git add data.json
git commit -m "chore: init data branch"
git push -u origin data
git checkout main
```

### 2. GitHub token
Create a fine-grained Personal Access Token with **Contents: Read and write**
on the `ai-crypto-recommendation` repo. Then:
```bash
cp .env.example .env
# edit .env and paste the token into GITHUB_TOKEN
```

### 3. Python environment
```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows PowerShell
pip install -r requirements.txt
```

### 4. Deploy the site on Vercel
- Import the repo at vercel.com, deploy from the `main` branch.
- No build step; it serves the `site/` folder (see `vercel.json`).

## Run the scanner
```bash
.\.venv\Scripts\Activate.ps1
python -m scanner.main
```
Leave it running; it publishes fresh data every 15 minutes. When your computer
is off, the site shows the last published data with a "stale" indicator.

## Run tests
```bash
python -m pytest -v
```

## Tuning
Edit `scanner/config.py` — weights, filter thresholds, refresh interval, chains.
```

- [ ] **Step 3: Verify tests still pass**

Run: `python -m pytest -v`
Expected: PASS (all).

- [ ] **Step 4: Commit and push main**

```bash
git add vercel.json README.md
git commit -m "docs: vercel config and setup README"
git push -u origin main
```

---

## Self-Review Notes

- **Spec coverage:** combination market (Task 6 allowed chains) ✓; 15-min refresh (config + main loop) ✓; momentum/safety/freshness/liquidity signals (Tasks 3–5) ✓; RugCheck hard filter (Task 4) ✓; GitHub `data` branch transport (Tasks 9, 12) ✓; static Vercel site with freshness + error states + disclaimer (Task 11) ✓; keep-last-good error handling (Task 10) ✓; TDD for scoring/build/publish (Tasks 3–10) ✓; ML deferred to Phase 2 (out of scope, snapshots on GitHub build the dataset) ✓.
- **Placeholders:** none — all steps carry real code/commands.
- **Type consistency:** `Candidate`/`RugReport`/`ScoredCoin` field names consistent across Tasks 2–11; `rank_top(candidates, rug_by_addr, now_ms)` signature matches its call in `main.run_once`; payload keys in `build_payload` match `validate_payload` and `app.js` field reads.
