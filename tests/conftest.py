import os
import sys
from pathlib import Path

# Make the repo root importable and keep tests independent of a real .env
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("DISCORD_WEBHOOK", "https://discord.com/api/webhooks/123/SECRET")