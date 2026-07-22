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


def build_put_body(payload: dict, sha: str | None) -> dict:
    content = json.dumps(payload, indent=2).encode()
    body = {
        "message": f"data: update at {payload.get('generated_at')}",
        "content": base64.b64encode(content).decode(),
        "branch": config.DATA_BRANCH,
    }
    if sha:
        body["sha"] = sha
    return body


def _get_current_sha(token: str) -> str | None:
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
