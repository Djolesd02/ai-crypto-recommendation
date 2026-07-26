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
    txns_m5 = (pair.get("txns", {}) or {}).get("m5", {}) or {}
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
        buys_m5=_f(txns_m5.get("buys")),
        sells_m5=_f(txns_m5.get("sells")),
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
