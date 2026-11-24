"""Discord webhook output: one Markdown message with the table image attached.

Plain messages render headers (#, ##, ###), subtext (-#), bold, lists and
quotes. Discord caps a message at 2000 characters, so if the text ever runs
long it's split on line breaks and the image rides on the last chunk.
"""
import json
from datetime import datetime

import requests

import config

LIMIT = 1990
FOOTER = ("-# AI-generated from prices and headlines · Ideas to research, not financial advice"
          " · Smaller caps tend to be more volatile")


def money(x):
    return f"{'+' if x >= 0 else '-'}${abs(x):,.2f}"


def compose(brief_text, t, recs=None, missing=(), session=None):
    d = datetime.now()
    day = "🟢" if t["chg"] >= 0 else "🔴"
    gain = "🟢" if t["gain"] >= 0 else "🔴"
    parts = [
        f"## 📈 Morning Brief · {d:%a %b} {d.day}",
        f"> **${t['value']:,.2f}**  ·  {day} **{money(t['chg'])}** ({t['chg_pct']:+.2f}%) last session"
        f"  ·  {gain} **{money(t['gain'])}** ({t['gain_pct']:+.2f}%) total",
    ]
    if session and session.get("early") and session.get("close"):
        c = session["close"]
        parts.append(f"> 🕐 Early close today at **{c.hour % 12 or 12}:{c:%M} {c:%p} ET**")
    parts += ["", brief_text.strip()]
    if recs and recs["notes"]:
        parts += ["", "### ⚖️ Balance"] + [f"- {n}" for n in recs["notes"]]
    if recs and any(recs["ideas"].values()):
        parts += ["", "### 💡 Ideas to research"]
        for tier, label in (("large", "Large cap"), ("mid", "Mid cap"), ("small", "Small cap")):
            picks = recs["ideas"].get(tier) or []
            if picks:
                parts.append(f"**{label}**")
                parts += [f"- **{i['ticker']}** · {i['reason']}" for i in picks]
    if recs and not recs["bench_ok"]:
        parts.append(f"-# Couldn't load {config.BENCHMARK} sector weights today.")
    if missing:
        parts.append(f"-# ⚠️ No price data from Yahoo: {', '.join(missing)}")
    parts += ["", FOOTER]
    return "\n".join(parts)


def split_message(text, limit=LIMIT):
    """Split on line breaks so no chunk exceeds Discord's limit."""
    chunks, current = [], ""
    for line in text.splitlines(keepends=True):
        while len(line) > limit:  # a single giant line
            if current:
                chunks.append(current)
                current = ""
            chunks.append(line[:limit])
            line = line[limit:]
        if len(current) + len(line) > limit:
            chunks.append(current)
            current = ""
        current += line
    if current.strip():
        chunks.append(current)
    return chunks


def redact(text):
    """Hide the webhook URL (it contains the secret token) in logs and alerts."""
    url = config.DISCORD_WEBHOOK or ""
    text = str(text)
    if url:
        text = text.replace(url, "<DISCORD_WEBHOOK>")
        token_path = url.split("/api/webhooks/")[-1]
        if token_path and token_path != url:
            text = text.replace(token_path, "<redacted>")
    return text


def post_alert(error, tb=""):
    """Short failure notice so a broken run isn't silent. Never raises."""
    d = datetime.now()
    tail = redact(tb).strip()[-1200:]
    text = (
        f"## ⚠️ Market brief failed · {d:%a %b} {d.day}\n"
        f"`{type(error).__name__}: {redact(error)[:300]}`\n"
        + (f"```\n{tail}\n```\n" if tail else "")
        + "-# Run `python market_brief.py --dry-run` on the server to reproduce."
    )
    try:
        requests.post(
            config.DISCORD_WEBHOOK,
            json={"username": "Market Brief Bot", "content": text[:LIMIT],
                  "allowed_mentions": {"parse": []}},
            timeout=15,
        ).raise_for_status()
    except Exception as e:
        print(f"Couldn't post failure alert: {redact(e)}")


def post(text, image_path=None):
    chunks = split_message(text) or [""]
    for i, chunk in enumerate(chunks):
        payload = {
            "username": "Market Brief Bot",
            "content": chunk,
            "allowed_mentions": {"parse": []},  # AI text can't @everyone
        }
        last = i == len(chunks) - 1
        if last and image_path:
            with open(image_path, "rb") as f:
                r = requests.post(
                    config.DISCORD_WEBHOOK,
                    data={"payload_json": json.dumps(payload)},
                    files={"files[0]": ("portfolio.png", f, "image/png")},
                    timeout=30,
                )
        else:
            r = requests.post(config.DISCORD_WEBHOOK, json=payload, timeout=15)
        r.raise_for_status()