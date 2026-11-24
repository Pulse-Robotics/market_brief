from market_brief import notify


def test_split_respects_discord_limit():
    chunks = notify.split_message("line\n" * 1000)
    assert len(chunks) > 1
    assert all(len(c) <= notify.LIMIT for c in chunks)
    assert "".join(chunks) == "line\n" * 1000


def test_short_message_is_one_chunk():
    assert notify.split_message("hello") == ["hello"]


def test_redact_hides_webhook_token(monkeypatch):
    url = "https://discord.com/api/webhooks/123/SECRET"
    monkeypatch.setattr(notify.config, "DISCORD_WEBHOOK", url)
    text = f"failed posting to {url} (url: /api/webhooks/123/SECRET)"
    out = notify.redact(text)
    assert "SECRET" not in out
    assert "<DISCORD_WEBHOOK>" in out