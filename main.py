"""Run the morning portfolio brief from a repo checkout.

    python main.py            # build and post to Discord
    python main.py --dry-run  # print text and save img/brief_card.png, post nothing
    python main.py --force    # run even if the market is closed today

Installed with pip? Use the `market-brief` command instead.
"""
import os
from pathlib import Path

# A checkout always uses its own folder for .env, portfolio/, img/ and logs/,
# wherever it's launched from (e.g. cron).
os.environ.setdefault("MARKET_BRIEF_HOME", str(Path(__file__).resolve().parent))

from market_brief.cli import main  # noqa: E402

if __name__ == "__main__":
    main()