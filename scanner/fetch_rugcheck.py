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
