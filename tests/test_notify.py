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


def _totals():
    return {"value": 10000.0, "chg": -100.0, "chg_pct": -1.0, "gain": 500.0, "gain_pct": 5.2}


def _recs(n_notes=3, per_tier=2, reason_len=90):
    reason = "x" * reason_len
    return {
        "notes": [f"note {i} " + "y" * 120 for i in range(n_notes)],
        "ideas": {t: [{"ticker": f"{t[:1].upper()}{i}", "reason": reason} for i in range(per_tier)]
                  for t in ("large", "mid", "small")},
        "bench_ok": True,
    }


def test_short_message_keeps_everything():
    text = notify.compose("- one bullet", _totals(), _recs(n_notes=1, per_tier=1, reason_len=10))
    assert "Smaller caps tend to be more volatile" in text
    assert text.count("· xxxxxxxxxx") == 3


def test_long_message_trims_to_one_post():
    brief = "\n".join(f"- bullet {i} " + "z" * 100 for i in range(10))
    text = notify.compose(brief, _totals(), _recs())
    assert len(text) <= notify.LIMIT
    assert all(f"bullet {i}" in text for i in range(10))  # holdings bullets never cut


def test_trims_optional_sections_in_order():
    brief = "\n".join(f"- bullet {i} " + "z" * 100 for i in range(10))
    text = notify.compose(brief, _totals(), _recs())
    assert "note 0" in text          # first balance note survives longest
    assert "note 2" not in text      # third note is the first thing dropped