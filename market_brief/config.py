"""Settings loaded from .env. Every other module imports from here."""
import os
from pathlib import Path

from dotenv import load_dotenv

# Repo root (this file lives in market_brief/)
BASE = Path(__file__).resolve().parent.parent
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


def problems(need_webhook=True):
    """Setup problems as readable messages; empty list means ready to run."""
    out = []
    missing = [name for name, value, needed in (
        ("GEMINI_API_KEY", GEMINI_API_KEY, True),
        ("DISCORD_WEBHOOK", DISCORD_WEBHOOK, need_webhook),
    ) if needed and not value]
    if missing:
        out.append(f"Missing in .env: {', '.join(missing)}. Copy .env.example to .env and fill it in.")
    if not HOLDINGS_FILE.exists():
        out.append(
            f"Portfolio file not found: {HOLDINGS_FILE.relative_to(BASE)}. Export your portfolio "
            "from Yahoo Finance (see portfolio/portfolio.example.csv for the format)."
        )
    return out