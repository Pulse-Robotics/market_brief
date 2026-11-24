"""Morning portfolio brief -> Discord.

Usage:
    python market_brief.py            # build and post to Discord
    python market_brief.py --dry-run  # print text and save the image, post nothing
"""
import sys

import config
import market
import notify
import render
from brief import write_brief
from portfolio import load_holdings
from recommendations import build_recommendations


def main():
    dry_run = "--dry-run" in sys.argv

    rows = market.get_quotes(load_holdings(config.HOLDINGS_FILE))
    t = market.totals(rows)
    missing = [r["symbol"] for r in rows if not r["ok"]]

    brief_text = write_brief(rows, t["value"])

    recs = None
    if config.RECOMMENDATIONS:
        try:
            recs = build_recommendations(rows)
        except Exception as e:  # never let this section block the brief
            print(f"Recommendations failed: {e}")

    image = None
    try:
        image = render.render_card(rows, recs["table"] if recs else None, config.CARD_FILE)
    except Exception as e:  # text still posts without the image
        print(f"Table image failed: {e}")

    text = notify.compose(brief_text, t, recs, missing)

    if dry_run:
        print(text)
        print(f"\n[{len(text)} chars] Image: {image or 'none'}")
        return

    notify.post(text, image)
    print("Brief sent.")


if __name__ == "__main__":
    main()
