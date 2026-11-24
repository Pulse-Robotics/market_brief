"""Settings loaded from .env. Every other module imports from here."""
import os
from pathlib import Path

from dotenv import load_dotenv

# Where .env, portfolio/, img/ and logs/ live:
#   - MARKET_BRIEF_HOME if set
#   - otherwise the repo root, when running from a checkout
#   - otherwise the current directory (pip-installed package)
_PKG_PARENT = Path(__file__).resolve().parent.parent
BASE = Path(
    os.getenv("MARKET_BRIEF_HOME")
    or (_PKG_PARENT if (_PKG_PARENT / "main.py").exists() else Path.cwd())
).resolve()
load_dotenv(BASE / ".env", override=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK", "").strip()

# Comma-separated: first is primary, the rest are fallbacks
GEMINI_MODELS = [
    m.strip()
    for m in os.getenv(
        "GEMINI_MODELS",
        os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite,gemini-3.1-flash-lite"),
    ).split(",")
    if m.strip()
]

HOLDINGS_FILE = BASE / os.getenv("HOLDINGS_FILE", "portfolio/portfolio.csv")
CARD_FILE = BASE / "img" / "brief_card.png"

# Fund whose sector mix is "the market" for comparison
BENCHMARK = os.getenv("BENCHMARK", "SPY")

# Turn the sector/cap/ideas section off with RECOMMENDATIONS=0
RECOMMENDATIONS = os.getenv("RECOMMENDATIONS", "1") != "0"

# What kind of ideas to suggest: stocks | etfs | mixed
SUGGESTIONS = os.getenv("SUGGESTIONS", "stocks").strip().lower()


def _is_placeholder(value):
    """Empty, or still the template's example value."""
    return not value or value.startswith("your_") or value.endswith("...")


def problems(need_webhook=True):
    """Setup problems as readable messages; empty list means ready to run."""
    out = []
    missing = [name for name, value, needed in (
        ("GEMINI_API_KEY", GEMINI_API_KEY, True),
        ("DISCORD_WEBHOOK", DISCORD_WEBHOOK, need_webhook),
    ) if needed and _is_placeholder(value)]
    if not (BASE / ".env").exists() and missing:
        out.append(f"No .env in {BASE}. Run `market-brief init` here, or copy .env.example to .env.")
    elif missing:
        out.append(f"Fill in .env: {', '.join(missing)}.")
    if not HOLDINGS_FILE.exists():
        out.append(
            f"Portfolio file not found: {HOLDINGS_FILE.relative_to(BASE)}. Export your portfolio "
            "from Yahoo Finance (format: portfolio/portfolio.example.csv; `market-brief init` creates it)."
        )
    return out