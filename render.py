"""Render the holdings and sector tables as one PNG card for Discord.

Discord can't display Markdown tables, so the numbers go in an image and
the message text carries the AI commentary.
"""
from datetime import datetime

import matplotlib

matplotlib.use("Agg")  # headless: no display needed on the server
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

import config  # noqa: E402
import market  # noqa: E402

# Dark theme that sits well in Discord
BG = "#15171c"
STRIPE = "#1c1f26"
RULE = "#2b303a"
TEXT = "#e7e9ec"
MUTED = "#8a919e"
GREEN = "#3fb950"
RED = "#f85149"
BLUE = "#58a6ff"
SLATE = "#7d8590"

W = 1000          # canvas width in layout units (exported at 2x)
PAD = 40
ROW = 42
HEAD = 34
TITLE = 56
GAP = 30
FOOT = 44

LEFT, RIGHT = PAD, W - PAD


def _pct(v, decimals=1):
    return f"{v:+.{decimals}f}%"


def _color(v):
    return GREEN if v >= 0 else RED


def _bar(ax, x, yc, width, color, height=10, alpha=1.0):
    if width <= 0:
        return
    ax.add_patch(FancyBboxPatch(
        (x, yc - height / 2), width, height,
        boxstyle="round,pad=0,rounding_size=4",
        linewidth=0, facecolor=color, alpha=alpha,
    ))


def _title(ax, y, title, subtitle):
    ax.text(LEFT, y + TITLE / 2 + 4, title, color=TEXT, fontsize=17,
            fontweight="bold", va="center", ha="left")
    ax.text(RIGHT, y + TITLE / 2 + 6, subtitle, color=MUTED, fontsize=10,
            va="center", ha="right")
    return y + TITLE


def _header(ax, y, cols):
    for label, x, ha in cols:
        ax.text(x, y + HEAD / 2, label.upper(), color=MUTED, fontsize=9.5,
                fontweight="bold", va="center", ha=ha)
    ax.plot([LEFT, RIGHT], [y + HEAD, y + HEAD], color=RULE, linewidth=1)
    return y + HEAD


def _stripe(ax, y, i):
    if i % 2 == 0:
        ax.add_patch(Rectangle((LEFT, y), RIGHT - LEFT, ROW, facecolor=STRIPE, linewidth=0))
    return y + ROW / 2


# ---------------------------------------------------------------- sections

def _holdings(ax, y, rows, total_value):
    y = _title(ax, y, "Holdings", "Day = last session  ·  Gain = since purchase")
    cols = [("Ticker", LEFT + 20, "left"), ("Price", 300, "right"), ("Day", 420, "right"),
            ("Weight", 530, "right"), ("Gain", RIGHT - 20, "right")]
    y = _header(ax, y, cols)

    max_w = max((r["value"] / total_value for r in rows), default=1) or 1
    for i, r in enumerate(rows):
        yc = _stripe(ax, y, i)
        weight = r["value"] / total_value * 100 if total_value else 0
        ax.text(LEFT + 20, yc, r["symbol"], color=TEXT, fontsize=12.5,
                fontweight="bold", va="center", ha="left")
        ax.text(300, yc, f"${r['price']:,.2f}", color=TEXT, fontsize=12, va="center", ha="right")
        ax.text(420, yc, _pct(r["pct"], 2), color=_color(r["pct"]), fontsize=12,
                fontweight="bold", va="center", ha="right")
        ax.text(530, yc, f"{weight:.1f}%", color=TEXT, fontsize=12, va="center", ha="right")
        # weight bar
        bar_x, bar_max = 548, 230
        _bar(ax, bar_x, yc, bar_max, RULE)
        _bar(ax, bar_x, yc, bar_max * (weight / 100) / max_w, BLUE)
        if r["gain_pct"] is not None:
            ax.text(RIGHT - 20, yc, _pct(r["gain_pct"]), color=_color(r["gain_pct"]),
                    fontsize=12, va="center", ha="right")
        else:
            ax.text(RIGHT - 20, yc, "–", color=MUTED, fontsize=12, va="center", ha="right")
        y += ROW
    return y


def _sectors(ax, y, table):
    y = _title(ax, y, "Sector Balance", f"vs {config.BENCHMARK}  ·  1M = sector ETF")
    center, half = 640, 130
    cols = [("Sector", LEFT + 20, "left"), ("You", 300, "right"), ("Mkt", 380, "right"),
            ("Over / Under", center, "center"), ("1M", RIGHT - 20, "right")]
    y = _header(ax, y, cols)

    diffs = [abs(r["you"] - r["mkt"]) for r in table if r["mkt"] is not None]
    scale = max(max(diffs, default=0), 10)  # at least ±10 pts across the bar

    for i, r in enumerate(table):
        yc = _stripe(ax, y, i)
        label = market.SECTOR_LABELS.get(r["sector"], r["sector"])
        ax.text(LEFT + 20, yc, label, color=TEXT, fontsize=12.5, va="center", ha="left")
        ax.text(300, yc, f"{r['you']:.0f}%", color=TEXT, fontsize=12,
                fontweight="bold", va="center", ha="right")
        if r["mkt"] is not None:
            ax.text(380, yc, f"{r['mkt']:.0f}%", color=MUTED, fontsize=12, va="center", ha="right")
            diff = round(r["you"] - r["mkt"])
            # diverging bar: right = overweight, left = underweight
            ax.plot([center, center], [yc - 12, yc + 12], color=RULE, linewidth=1)
            length = half * min(abs(diff), scale) / scale
            if diff == 0:
                ax.text(center + 8, yc, "0", color=MUTED, fontsize=10.5, va="center", ha="left")
            elif diff > 0:
                _bar(ax, center, yc, length, BLUE)
                tx, ha = center + length + 8, "left"
            else:
                _bar(ax, center - length, yc, length, SLATE)
                tx, ha = center - length - 8, "right"
            if diff != 0:
                ax.text(tx, yc, f"{diff:+d}", color=BLUE if diff > 0 else MUTED,
                        fontsize=10.5, va="center", ha=ha)
        if r["1m"] is not None:
            ax.text(RIGHT - 20, yc, _pct(r["1m"]), color=_color(r["1m"]),
                    fontsize=12, va="center", ha="right")
        y += ROW
    return y


def _caps(ax, y, table):
    y = _title(ax, y, "Market Cap", "Large >$10B  ·  Mid $2–10B  ·  Small $300M–2B  ·  1M = size ETF")
    cols = [("Size", LEFT + 20, "left"), ("You", 300, "right"),
            ("Holdings", 548, "left"), ("1M", RIGHT - 20, "right")]
    y = _header(ax, y, cols)

    for i, r in enumerate(table):
        yc = _stripe(ax, y, i)
        ax.text(LEFT + 20, yc, market.CAP_LABELS.get(r["tier"], r["tier"]), color=TEXT,
                fontsize=12.5, va="center", ha="left")
        ax.text(300, yc, f"{r['you']:.0f}%", color=TEXT, fontsize=12,
                fontweight="bold", va="center", ha="right")
        bar_x, bar_max = 318, 200
        _bar(ax, bar_x, yc, bar_max, RULE)
        _bar(ax, bar_x, yc, bar_max * r["you"] / 100, BLUE)
        held = r["holdings"]
        names = ", ".join(held[:4]) + (f"  +{len(held) - 4}" if len(held) > 4 else "") if held else "–"
        ax.text(548, yc, names, color=MUTED, fontsize=10.5, va="center", ha="left")
        if r["1m"] is not None:
            label = f"{_pct(r['1m'])}"
            ax.text(RIGHT - 20, yc, label, color=_color(r["1m"]), fontsize=12,
                    va="center", ha="right")
            ax.text(RIGHT - 95, yc, r["etf"], color=MUTED, fontsize=9.5,
                    va="center", ha="right")
        y += ROW
    return y


# ---------------------------------------------------------------- public

def render_card(rows, sector_table, path, cap_table=None):
    """Draw the card and save it to `path`. Returns the path."""
    good = sorted((r for r in rows if r["ok"]), key=lambda r: r["value"], reverse=True)
    total_value = sum(r["value"] for r in good)
    sectors = [
        s for s in (sector_table or [])
        if s["you"] >= 0.5 or (s["mkt"] or 0) >= 0.5
    ]

    caps = cap_table or []

    height = PAD + TITLE + HEAD + ROW * len(good) + FOOT + PAD
    if caps:
        height += GAP + TITLE + HEAD + ROW * len(caps)
    if sectors:
        height += GAP + TITLE + HEAD + ROW * len(sectors)

    fig = plt.figure(figsize=(W / 100, height / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(height, 0)
    ax.axis("off")
    fig.patch.set_facecolor(BG)

    y = _holdings(ax, PAD, good, total_value)
    if caps:
        y = _caps(ax, y + GAP, caps)
    if sectors:
        y = _sectors(ax, y + GAP, sectors)

    d = datetime.now()
    ax.text(LEFT, y + FOOT / 2 + 6, f"{d:%a %b} {d.day}, {d:%Y}  ·  Prices: Yahoo Finance",
            color=MUTED, fontsize=9.5, va="center", ha="left")

    fig.savefig(path, dpi=200, facecolor=BG)
    plt.close(fig)
    return path