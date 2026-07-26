"""Central configuration: scoring weights, filters, thresholds, repo info."""

# --- Scoring weights (must sum to 1.0) ---
WEIGHTS = {
    "momentum": 0.45,
    "liquidity": 0.25,
    "safety": 0.20,
    "freshness": 0.10,
}

TOP_N = 10

# --- Hard filters (candidates below these are dropped before scoring) ---
MIN_LIQUIDITY_USD = 10_000.0
MIN_VOLUME_H24 = 20_000.0

# --- Normalization thresholds (see score.py) ---
LIQ_GOOD_USD = 500_000.0        # liquidity considered "full marks"
VOL_GOOD_USD = 1_000_000.0      # 24h volume considered "full marks"

# --- Momentum shape (recency-first, catches blow-off tops) ---
MOMENTUM_M5_FULL = 5.0          # +5% in 5min = full recent-climb marks
MOMENTUM_H1_FULL = 50.0         # +50% in 1h = full short-climb marks
MOMENTUM_M5_WEIGHT = 0.6        # how much the 5min window outweighs the 1h window
REVERSAL_H1_MIN = 50.0          # 1h pumped past this + negative 5min = rolling over
REVERSAL_M5_FULL = 5.0          # 5min of -5% => full reversal penalty
SELL_PRESSURE_MIN = 0.55        # recent sells share above this starts a penalty
SELL_PRESSURE_FULL = 0.80       # recent sells share at/above this = max penalty
SELL_PRESSURE_FLOOR = 0.30      # heaviest sell pressure still leaves 30% of the score
RECENT_DUMP_M5 = -12.0          # falling knife: down >12% in 5min -> hard drop

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
