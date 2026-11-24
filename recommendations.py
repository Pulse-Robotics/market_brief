"""Sector balance vs the market, plus AI ideas for rebalancing."""
from collections import defaultdict

import ai
import config
import market

STYLE_RULES = {
    "stocks": ("individual stocks only, no ETFs or funds. Established large or mid caps "
               "in underweight sectors, each from a different sector where possible"),
    "etfs": "broad sector or index ETFs only, no individual stocks",
    "mixed": "a mix of individual stocks and ETFs",
}
ALLOWED_TYPES = {
    "stocks": {"EQUITY"},
    "etfs": {"ETF"},
    "mixed": {"EQUITY", "ETF"},
}

PROMPT = """You help with a personal portfolio review tool. Below is the portfolio's sector mix
compared with the S&P 500 ({benchmark}), plus each sector ETF's recent performance as a
rough read on market sentiment. Holdings already owned are listed.

{sector_lines}

Holdings: {holdings}

Return JSON only, in this shape:
{{"balance_notes": ["..."], "suggestions": [{{"ticker": "XYZ", "reason": "..."}}]}}

Rules:
- balance_notes: 2 bullets, max 22 words each. Name the biggest over/underweights and
  how they line up with current sector momentum (concentration risk, missing exposure).
- suggestions: 4 ideas to research that would improve balance: {style}.
  Real US-listed tickers only. Never suggest something already held.
  Reason max 16 words: say which gap it fills and one concrete trait of the company.
- These are ideas to research, not advice. No price targets, no buy/sell calls, no hype."""


def portfolio_sectors(rows):
    """Portfolio sector mix in percent, with funds looked through."""
    good = [r for r in rows if r["ok"]]
    total = sum(r["value"] for r in good)
    weights = defaultdict(float)
    for r in good:
        secs = r["sectors"] or {"unknown": 1.0}
        for sector, frac in secs.items():
            weights[sector] += r["value"] * frac
    return {k: v / total * 100 for k, v in weights.items()} if total else {}


def sector_table(port, bench, momentum):
    sectors = set(port) | set(bench)
    table = [{
        "sector": s,
        "you": port.get(s, 0.0),
        "mkt": bench.get(s),
        "1m": momentum.get(s, {}).get("1m"),
        "5d": momentum.get(s, {}).get("5d"),
    } for s in sectors]
    return sorted(table, key=lambda r: (r["you"], r["mkt"] or 0), reverse=True)


def sector_lines_for_ai(table):
    out = []
    for r in table:
        label = market.SECTOR_LABELS.get(r["sector"], r["sector"])
        mkt = f"{r['mkt']:.1f}%" if r["mkt"] is not None else "n/a"
        mom = (f"ETF 5d {r['5d']:+.1f}%, 1m {r['1m']:+.1f}%"
               if r["1m"] is not None else "ETF n/a")
        out.append(f"- {label}: portfolio {r['you']:.1f}% vs market {mkt} | {mom}")
    return "\n".join(out)


def validate_suggestions(suggestions, held, limit=3):
    """Keep real, not-already-held tickers of the configured type."""
    allowed = ALLOWED_TYPES.get(config.SUGGESTIONS, ALLOWED_TYPES["stocks"])
    good = []
    for s in suggestions or []:
        ticker = str(s.get("ticker", "")).strip().upper()
        if not ticker or ticker in held or any(g["ticker"] == ticker for g in good):
            continue
        if market.lookup_type(ticker) in allowed:
            good.append({"ticker": ticker, "reason": str(s.get("reason", "")).strip()})
        if len(good) == limit:
            break
    return good


def build_recommendations(rows):
    """Returns {"table", "notes", "ideas", "bench_ok"} for rendering and posting."""
    port = portfolio_sectors(rows)
    bench = market.benchmark_sectors(config.BENCHMARK)
    momentum = market.sector_momentum()
    table = sector_table(port, bench, momentum)

    held = {r["symbol"] for r in rows}
    try:
        data = ai.generate_json(PROMPT.format(
            benchmark=config.BENCHMARK,
            sector_lines=sector_lines_for_ai(table),
            holdings=", ".join(sorted(held)),
            style=STYLE_RULES.get(config.SUGGESTIONS, STYLE_RULES["stocks"]),
        ))
        notes = [str(n).strip() for n in data.get("balance_notes", []) if str(n).strip()]
        ideas = validate_suggestions(data.get("suggestions"), held)
    except Exception as e:
        print(f"Recommendations AI failed: {e}")
        notes, ideas = [], []

    return {"table": table, "notes": notes, "ideas": ideas, "bench_ok": bool(bench)}
