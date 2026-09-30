import json

import pytest

from sb_webex import client


def test_finish_login_rejects_a_mismatched_state(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(
            {
                "state": "expected",
                "verifier": "verifier",
                "redirect_uri": "http://127.0.0.1:8787/webex/callback",
                "expires_at": 9_999_999_999,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(client, "_STATE_PATH", state_path)

    def fail_network() -> dict:
        raise AssertionError("state mismatch must not call the token endpoint")

    monkeypatch.setattr(client, "authorization_metadata", fail_network)
    with pytest.raises(client.WebexAuthError, match="did not match"):
        client.finish_login("code", "other")
