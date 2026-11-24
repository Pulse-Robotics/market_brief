"""Everything that talks to Yahoo Finance: prices, headlines, sectors, momentum."""
import math
import re

import yfinance as yf

# yfinance sector keys -> short display labels
SECTOR_LABELS = {
    "technology": "Tech",
    "financial_services": "Financials",
    "healthcare": "Health",
    "consumer_cyclical": "Cons Disc",
    "consumer_defensive": "Cons Stap",
    "communication_services": "Comm Svcs",
    "industrials": "Industrials",
    "energy": "Energy",
    "basic_materials": "Materials",
    "realestate": "Real Est",
    "utilities": "Utilities",
    "unknown": "Unknown",
}

# SPDR sector ETFs, used as a market-sentiment proxy per sector
SECTOR_ETFS = {
    "technology": "XLK",
    "financial_services": "XLF",
    "healthcare": "XLV",
    "consumer_cyclical": "XLY",
    "consumer_defensive": "XLP",
    "communication_services": "XLC",
    "industrials": "XLI",
    "energy": "XLE",
    "basic_materials": "XLB",
    "realestate": "XLRE",
    "utilities": "XLU",
}

# Corporate suffixes to strip so "NVIDIA Corporation" -> "NVIDIA"
SUFFIXES = re.compile(
    r"\b(inc|incorporated|corp|corporation|co|company|ltd|limited|plc|"
    r"holdings|group|class [a-c]|the)\b",
    re.I,
)


def norm_sector(s):
    """'Financial Services' / 'realestate' / 'Real Estate' -> yfinance key."""
    key = (s or "").strip().lower().replace(" ", "_")
    return "realestate" if key == "real_estate" else key


def safe_info(stock):
    try:
        return stock.info or {}
    except Exception:
        return {}


def fund_sectors(stock):
    """Sector mix of an ETF/fund as {sector: fraction}, or {} if unavailable."""
    try:
        raw = stock.funds_data.sector_weightings or {}
    except Exception:
        return {}
    weights = {norm_sector(k): float(v) for k, v in raw.items() if v}
    total = sum(weights.values())
    return {k: v / total for k, v in weights.items()} if total else {}


def holding_sectors(stock, info):
    """{sector: fraction} for one holding. Funds are looked through."""
    qtype = info.get("quoteType")
    if qtype == "EQUITY" and info.get("sector"):
        return {norm_sector(info["sector"]): 1.0}
    if qtype in ("ETF", "MUTUALFUND"):
        return fund_sectors(stock)
    return {}


# ---------------------------------------------------------------- headlines

def search_terms(symbol, info):
    """Regexes that identify headlines about this holding."""
    terms = []
    if len(symbol) >= 3:  # 1-2 letter tickers (T, F) match too much
        terms.append(re.compile(rf"\b{re.escape(symbol)}\b"))  # case-sensitive

    raw = info.get("shortName") or info.get("longName") or ""
    name = " ".join(SUFFIXES.sub(" ", re.sub(r"[,.]", " ", raw)).split()).strip(" &-")
    if name:
        terms.append(re.compile(rf"\b{re.escape(name)}\b", re.I))
        first = name.split()[0]
        # For single stocks the first word is usually enough ("Apple", "Nvidia").
        # Skip for ETFs: "Vanguard" alone would match unrelated fund news.
        if info.get("quoteType") == "EQUITY" and len(first) > 3:
            terms.append(re.compile(rf"\b{re.escape(first)}\b", re.I))
    return terms


def headline_titles(stock, symbol, info, n=2):
    terms = search_terms(symbol, info)
    try:
        news = stock.get_news(count=20)
    except Exception:
        news = stock.news or []

    titles = []
    for item in news:
        title = (item.get("content") or {}).get("title") or item.get("title")
        if title and any(t.search(title) for t in terms):
            titles.append(title)
            if len(titles) == n:
                break
    return titles


# ---------------------------------------------------------------- quotes

def _finite(x):
    try:
        return x is not None and math.isfinite(float(x)) and float(x) > 0
    except (TypeError, ValueError):
        return False


def last_and_prev(stock, info):
    """(last price, previous close).

    Prefers Yahoo's quote fields, which are split-aware and don't depend on
    daily bars. Daily history can have gaps (e.g. SNDK around its Nov 2026
    split), which makes 'previous close' silently wrong.
    """
    last = info.get("regularMarketPrice") or info.get("currentPrice")
    prev = info.get("regularMarketPreviousClose") or info.get("previousClose")
    if _finite(last) and _finite(prev):
        return float(last), float(prev)

    try:  # fallback: last two valid daily closes
        close = stock.history(period="5d")["Close"].dropna()
    except Exception:
        return None
    if len(close) < 2:
        return None
    return float(close.iloc[-1]), float(close.iloc[-2])


def get_quotes(holdings):
    rows = []
    for symbol, h in holdings.items():
        stock = yf.Ticker(symbol)
        info = safe_info(stock)
        prices = last_and_prev(stock, info)
        if not prices:
            print(f"{symbol}: no usable price data from Yahoo")
            rows.append({"symbol": symbol, "ok": False})
            continue
        last, prev = prices
        value = last * h["shares"]
        cost = h["cost"] if h["cost_known"] and h["cost"] > 0 else None
        rows.append({
            "symbol": symbol,
            "ok": True,
            "price": last,
            "pct": (last - prev) / prev * 100,
            "value": value,
            "dollar_chg": (last - prev) * h["shares"],
            "cost": cost,
            "gain_pct": (value - cost) / cost * 100 if cost else None,
            "sectors": holding_sectors(stock, info),
            "news": headline_titles(stock, symbol, info),
        })
    return rows


def totals(rows):
    good = [r for r in rows if r["ok"]]
    value = sum(r["value"] for r in good)
    chg = sum(r["dollar_chg"] for r in good)
    with_cost = [r for r in good if r["cost"]]
    cost = sum(r["cost"] for r in with_cost)
    gain = sum(r["value"] for r in with_cost) - cost
    return {
        "value": value,
        "chg": chg,
        "chg_pct": chg / (value - chg) * 100 if value - chg else 0.0,
        "gain": gain,
        "gain_pct": gain / cost * 100 if cost else 0.0,
    }


# ---------------------------------------------------------------- market-wide

def benchmark_sectors(symbol):
    """Benchmark sector mix in percent, e.g. {'technology': 33.1, ...}."""
    return {k: v * 100 for k, v in fund_sectors(yf.Ticker(symbol)).items()}


def sector_momentum():
    """{sector: {"5d": pct, "1m": pct}} from sector ETF prices."""
    out = {}
    for sector, etf in SECTOR_ETFS.items():
        try:
            close = yf.Ticker(etf).history(period="1mo")["Close"].dropna()
        except Exception:
            continue
        if len(close) < 6:
            continue
        last = close.iloc[-1]
        out[sector] = {
            "5d": (last / close.iloc[-6] - 1) * 100,
            "1m": (last / close.iloc[0] - 1) * 100,
        }
    return out


def lookup_type(symbol):
    """Yahoo quoteType ('EQUITY', 'ETF', ...) if the symbol trades, else None."""
    stock = yf.Ticker(symbol)
    try:
        if len(stock.history(period="5d")) == 0:
            return None
    except Exception:
        return None
    return safe_info(stock).get("quoteType") or "UNKNOWN"
