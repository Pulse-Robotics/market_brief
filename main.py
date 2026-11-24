"""Run the morning portfolio brief from a repo checkout.

    python main.py            # build and post to Discord
    python main.py --dry-run  # print text and save img/brief_card.png, post nothing
    python main.py --force    # run even if the market is closed today

Installed with pip? Use the `market-brief` command instead.
"""
from market_brief.cli import main

if __name__ == "__main__":
    main()