"""Parse the Yahoo Finance portfolio export."""
import csv
from pathlib import Path


def to_float(s):
    try:
        return float(str(s).replace(",", "").replace("$", "").strip())
    except (TypeError, ValueError):
        return None


def load_holdings(path):
    """Parse a Yahoo Finance portfolio export (CSV or tab-separated).

    Returns {symbol: {"shares", "cost", "cost_known"}}.
    Lots of the same symbol are combined; rows with no quantity are skipped.
    """
    lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    delim = "\t" if "\t" in lines[0] else ","
    holdings = {}
    for row in csv.DictReader(lines, delimiter=delim):
        symbol = (row.get("Symbol") or "").strip().upper()
        qty = to_float(row.get("Quantity"))
        if not symbol or not qty:
            continue
        price = to_float(row.get("Purchase Price"))
        h = holdings.setdefault(symbol, {"shares": 0.0, "cost": 0.0, "cost_known": True})
        h["shares"] += qty
        if price is None:
            h["cost_known"] = False
        else:
            h["cost"] += qty * price
    return holdings
