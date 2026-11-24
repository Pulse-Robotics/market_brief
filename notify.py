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
FOOTER = "-# Ideas to research, not financial advice. AI-generated from prices, headlines and sector weights."


def money(x):
    return f"{'+' if x >= 0 else '-'}${abs(x):,.2f}"


def compose(brief_text, t, recs=None, missing=()):
    d = datetime.now()
    day = "🟢" if t["chg"] >= 0 else "🔴"
    gain = "🟢" if t["gain"] >= 0 else "🔴"
    parts = [
        f"## 📈 Morning Brief · {d:%a %b} {d.day}",
        f"> **${t['value']:,.2f}**  ·  {day} **{money(t['chg'])}** ({t['chg_pct']:+.2f}%) last session"
        f"  ·  {gain} **{money(t['gain'])}** ({t['gain_pct']:+.2f}%) total",
        "",
        brief_text.strip(),
    ]
    if recs and recs["notes"]:
        parts += ["", "### ⚖️ Balance"] + [f"- {n}" for n in recs["notes"]]
    if recs and recs["ideas"]:
        parts += ["", "### 💡 Ideas to research"]
        parts += [f"- **{i['ticker']}** · {i['reason']}" for i in recs["ideas"]]
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
