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
