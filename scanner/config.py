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
