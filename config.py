"""Settings loaded from .env. Every other module imports from here."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / ".env", override=True)

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
DISCORD_WEBHOOK = os.environ["DISCORD_WEBHOOK"]

# Comma-separated: first is primary, the rest are fallbacks
GEMINI_MODELS = [
    m.strip()
    for m in os.getenv(
        "GEMINI_MODELS",
        os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite,gemini-3.1-flash-lite"),
    ).split(",")
    if m.strip()
]

HOLDINGS_FILE = BASE / os.getenv("HOLDINGS_FILE", "portfolio.csv")

# Fund whose sector mix is "the market" for comparison
BENCHMARK = os.getenv("BENCHMARK", "SPY")

# Turn the sector/ideas section off with RECOMMENDATIONS=0
RECOMMENDATIONS = os.getenv("RECOMMENDATIONS", "1") != "0"

# What kind of ideas to suggest: stocks | etfs | mixed
SUGGESTIONS = os.getenv("SUGGESTIONS", "stocks").strip().lower()

# Where the rendered table image is written
CARD_FILE = BASE / "brief_card.png"
