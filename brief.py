"""The daily summary: what moved and why."""
import ai

PROMPT = """You are writing a morning portfolio brief, read on a phone before the US market opens.
The data is the previous session's close plus recent headlines.
Write under 110 words in Discord Markdown: a one-line overall takeaway, then 3-5 short "- "
bullets on the moves that matter most: big % moves, large weights, real news. Bold tickers.
A table with every ticker's numbers is attached, so don't list every holding or restate
numbers without adding context. Don't use headers or tables.
Only attribute news to a ticker if the headline is clearly about that company.
If a ticker has no headlines, don't invent a reason for its move.
No investment advice, no hype.

{notes}"""


def build_notes(rows, total_value):
    """What the AI sees: % moves, weights, % gain since purchase. No dollars."""
    lines = []
    for r in sorted(rows, key=lambda r: r.get("value", 0), reverse=True):
        if not r["ok"]:
            lines.append(f"- {r['symbol']}: price unavailable")
            continue
        weight = r["value"] / total_value * 100 if total_value else 0
        gain = f", {r['gain_pct']:+.0f}% since purchase" if r["gain_pct"] is not None else ""
        news = "; ".join(r["news"]) or "No major headlines"
        lines.append(
            f"- {r['symbol']}: {r['pct']:+.2f}% (weight {weight:.1f}%{gain}) | News: {news}"
        )
    return "\n".join(lines)


def write_brief(rows, total_value):
    notes = build_notes(rows, total_value)
    try:
        return ai.generate(PROMPT.format(notes=notes))
    except Exception as e:
        print(f"Brief AI failed: {e}")
        return "⚠️ AI summary unavailable. Raw data:\n" + notes
