"""Sector and market-cap balance vs the market, plus AI ideas by cap tier."""
from collections import defaultdict

from . import ai, config, market

TIERS = ("large", "mid", "small")
IDEAS_PER_TIER = 2

STYLE_RULES = {
    "stocks": "individual stocks only, no ETFs or funds",
    "etfs": "ETFs only, no individual stocks",
    "mixed": "individual stocks or ETFs",
}
ALLOWED_TYPES = {
    "stocks": {"EQUITY"},
    "etfs": {"ETF"},
    "mixed": {"EQUITY", "ETF"},
}

PROMPT = """You help with a personal portfolio review tool. Below is the portfolio's sector mix
compared with the S&P 500 ({benchmark}), its market-cap mix, and recent ETF performance for each
sector and size tier as a rough read on market sentiment. Holdings already owned are listed.

Sectors:
{sector_lines}

Market cap (large >$10B, mid $2-10B, small $300M-2B):
{cap_lines}

Holdings: {holdings}

Return JSON only, in this shape:
{{"balance_notes": ["..."],
  "suggestions": {{"large": [{{"ticker": "XYZ", "reason": "..."}}], "mid": [...], "small": [...]}}}}

Rules:
- balance_notes: 2-3 bullets, max 18 words each. Cover the biggest sector over/underweights
  and the market-cap mix, and how they line up with current momentum.
- suggestions: 3 ideas per tier ({style}) that would improve sector balance, favoring
  underweight sectors. Large: established leaders. Mid: profitable, growing companies.
  Small: established small caps with real revenue, not speculative names.
  Real US-listed tickers only, sized correctly for their tier. Never suggest anything held.
  Reason max 12 words: which gap it fills and one concrete trait of the company.
- These are ideas to research, not advice. No price targets, no buy/sell calls, no hype."""


# ---------------------------------------------------------------- sectors

def portfolio_sectors(rows):
    """Portfolio sector mix in percent, with funds looked through."""
    good = [r for r in rows if r["ok"]]
    total = sum(r["value"] for r in good)
    weights = defaultdict(float)
    for r in good:
        for sector, frac in (r["sectors"] or {"unknown": 1.0}).items():
            weights[sector] += r["value"] * frac
    return {k: v / total * 100 for k, v in weights.items()} if total else {}


def sector_table(port, bench, momentum):
    table = [{
        "sector": s,
        "you": port.get(s, 0.0),
        "mkt": bench.get(s),
        "1m": momentum.get(s, {}).get("1m"),
        "5d": momentum.get(s, {}).get("5d"),
    } for s in set(port) | set(bench)]
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


# ---------------------------------------------------------------- market cap

def cap_table(rows, momentum):
    """Portfolio weight per cap tier, with that tier's ETF momentum."""
    good = sorted((r for r in rows if r["ok"]), key=lambda r: r["value"], reverse=True)
    total = sum(r["value"] for r in good)
    weights = defaultdict(float)
    for r in good:
        weights[r.get("tier") or "unknown"] += r["value"]

    table = []
    for tier in ("large", "mid", "small", "micro", "unknown"):
        you = weights.get(tier, 0.0) / total * 100 if total else 0.0
        if tier in ("micro", "unknown") and you < 0.5:
            continue  # only show these when you actually hold some
        table.append({
            "tier": tier,
            "you": you,
            "etf": market.CAP_ETFS.get(tier),
            "1m": momentum.get(tier, {}).get("1m"),
            "5d": momentum.get(tier, {}).get("5d"),
            "holdings": [r["symbol"] for r in good if (r.get("tier") or "unknown") == tier],
        })
    return table


def cap_lines_for_ai(table):
    out = []
    for r in table:
        mom = (f"{r['etf']} 5d {r['5d']:+.1f}%, 1m {r['1m']:+.1f}%"
               if r["1m"] is not None else "ETF n/a")
        names = ", ".join(r["holdings"]) or "none"
        out.append(f"- {market.CAP_LABELS[r['tier']]}: {r['you']:.1f}% ({names}) | {mom}")
    return "\n".join(out)


# ---------------------------------------------------------------- ideas

def validate_ideas(suggestions, held):
    """Check every suggested ticker on Yahoo and file it under its *actual* tier.

    Drops anything held, not found, the wrong type, or micro cap. Keeps up to
    IDEAS_PER_TIER per tier.
    """
    allowed = ALLOWED_TYPES.get(config.SUGGESTIONS, ALLOWED_TYPES["stocks"])
    ideas = {t: [] for t in TIERS}
    seen = set(held)

    candidates = []
    for tier in TIERS:  # AI's large picks first, then mid, then small
        candidates += (suggestions or {}).get(tier) or []

    for s in candidates:
        ticker = str(s.get("ticker", "")).strip().upper()
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        qtype, tier = market.lookup(ticker)
        if qtype in allowed and tier in ideas and len(ideas[tier]) < IDEAS_PER_TIER:
            ideas[tier].append({"ticker": ticker, "reason": str(s.get("reason", "")).strip()})
    return ideas


def build_recommendations(rows):
    """Returns data for rendering and posting:
    {"table", "cap_table", "notes", "ideas": {tier: [...]}, "bench_ok"}"""
    bench = market.benchmark_sectors(config.BENCHMARK)
    table = sector_table(portfolio_sectors(rows), bench, market.sector_momentum())
    caps = cap_table(rows, market.size_momentum())

    held = {r["symbol"] for r in rows}
    try:
        data = ai.generate_json(PROMPT.format(
            benchmark=config.BENCHMARK,
            sector_lines=sector_lines_for_ai(table),
            cap_lines=cap_lines_for_ai(caps),
            holdings=", ".join(sorted(held)),
            style=STYLE_RULES.get(config.SUGGESTIONS, STYLE_RULES["stocks"]),
        ))
        notes = [str(n).strip() for n in data.get("balance_notes", []) if str(n).strip()]
        ideas = validate_ideas(data.get("suggestions"), held)
    except Exception as e:
        print(f"Recommendations AI failed: {e}")
        notes, ideas = [], {t: [] for t in TIERS}

    return {"table": table, "cap_table": caps, "notes": notes,
            "ideas": ideas, "bench_ok": bool(bench)}