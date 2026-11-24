"""Command-line entry point: `market-brief` (pip install) or `python main.py` (from the repo).

Usage:
    market-brief init       # set up this folder: .env template, portfolio/, img/, logs/
    market-brief            # build and post to Discord
    market-brief --dry-run  # print text and save img/brief_card.png, post nothing
    market-brief --force    # run even if the market is closed today
"""
import sys
import traceback

from . import config, market, notify, render
from .portfolio import load_holdings
from .recommendations import build_recommendations
from .summary import write_brief
from .trading_day import today_session


SETUP_URL = "https://github.com/Pulse-Robotics/market_brief#setup"


def run(dry_run=False, force=False):
    session = today_session()
    if session is None and not force:
        print("Market closed today (NYSE holiday or weekend). No brief. Use --force to run anyway.")
        return

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
        image = render.render_card(
            rows,
            recs["table"] if recs else None,
            config.CARD_FILE,
            cap_table=recs["cap_table"] if recs else None,
        )
    except Exception as e:  # text still posts without the image
        print(f"Table image failed: {e}")

    text = notify.compose(brief_text, t, recs, missing, session)

    if dry_run:
        print(text)
        print(f"\n[{len(text)} chars] Image: {image or 'none'}")
        return

    notify.post(text, image)
    print("Brief sent.")


def init():
    from .home import init_home

    created, kept = init_home(config.BASE)
    print(f"Set up {config.BASE}")
    for item in created:
        print(f"  + {item}")
    for item in kept:
        print(f"  = {item} (already exists, left as is)")
    print(
        "\nNext:\n"
        "  1. Put your Gemini key and Discord webhook in .env\n"
        "  2. Export your Yahoo Finance portfolio to portfolio/portfolio.csv\n"
        "  3. Run: market-brief --dry-run\n"
        f"\nSetup guide: {SETUP_URL}"
    )


def main():
    args = sys.argv[1:]
    if args[:1] == ["init"]:
        init()
        return
    if args[:1] in (["-h"], ["--help"], ["help"]):
        print(__doc__.strip())
        return

    dry_run = "--dry-run" in args
    force = "--force" in args

    issues = config.problems(need_webhook=not dry_run)
    if issues:
        print("Can't run yet:\n" + "\n".join(f"  - {i}" for i in issues))
        print(f"\nSetup guide: {SETUP_URL}")
        sys.exit(2)

    try:
        run(dry_run, force)
    except Exception as e:
        tb = traceback.format_exc()
        print(notify.redact(tb), file=sys.stderr)  # never print the webhook token
        if not dry_run:
            notify.post_alert(e, tb)  # so a broken run isn't silent
        sys.exit(1)


if __name__ == "__main__":
    main()