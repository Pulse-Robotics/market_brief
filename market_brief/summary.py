"""The daily summary: what moved and why.

The AI only writes words (a takeaway line and one short note per ticker).
Python builds the bullets, so every holding appears exactly once, in weight
order, with numbers taken from the data rather than from the model.
"""
from . import ai

PROMPT = """You are writing notes for a morning portfolio brief, read on a phone before the US market opens.
The data is the previous session's close plus recent headlines for each holding.

{notes}

Return JSON only, in this shape:
{{"takeaway": "...", "notes": {{"TICKER": "...", "...": "..."}}}}

Rules:
- takeaway: one line, max 18 words, the overall story of the session for this portfolio.
- notes: one entry for EVERY ticker listed above, max 12 words each.
  Explain the move using only what a listed headline states. Don't repeat the % change.
  Mention only that ticker; never refer to other tickers in its note.
  Never infer causes like "sentiment" or "rotation"; call an analyst note an upgrade only
  if the headline says so. If there's no relevant headline, write
  "No specific news." and nothing else.
- Plain text only: no Markdown, no emojis, no investment advice."""


def build_notes(rows, total_value):
    """What the AI sees: % moves, weights, % gain since purchase. No dollars."""
    lines = []
    for r in rows:
        if not r["ok"]:
            continue
        weight = r["value"] / total_value * 100 if total_value else 0
        gain = f", {r['gain_pct']:+.0f}% since purchase" if r["gain_pct"] is not None else ""
        news = "; ".join(r["news"]) or "No headlines"
        lines.append(
            f"- {r['symbol']}: {r['pct']:+.2f}% (weight {weight:.1f}%{gain}) | News: {news}"
        )
    return "\n".join(lines)


def _bullet(r, note):
    arrow = "🔺" if r["pct"] >= 0 else "🔻"
    return f"- {arrow} **{r['symbol']}** {r['pct']:+.2f}% · {note}"


def write_brief(rows, total_value):
    ordered = sorted((r for r in rows if r["ok"]), key=lambda r: r["value"], reverse=True)

    takeaway, notes = "", {}
    try:
        data = ai.generate_json(PROMPT.format(notes=build_notes(ordered, total_value)))
        takeaway = str(data.get("takeaway", "")).strip()
        notes = {str(k).strip().upper(): str(v).strip()
                 for k, v in (data.get("notes") or {}).items()}
    except Exception as e:
        print(f"Brief AI failed: {e}")
        takeaway = "⚠️ AI summary unavailable today. Numbers only."

    bullets = [_bullet(r, notes.get(r["symbol"]) or "No commentary.") for r in ordered]
    return "\n".join(([takeaway, ""] if takeaway else []) + bullets)