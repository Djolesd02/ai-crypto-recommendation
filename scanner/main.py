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


def load_last_good() -> dict | None:
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
