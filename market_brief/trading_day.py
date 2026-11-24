"""Is the US stock market open today? Uses the NYSE calendar (holidays + early closes)."""
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")


def today_session(now=None):
    """Today's NYSE session, or None if the market is closed.

    Returns {"close": datetime, "early": bool}. If the calendar library is
    missing or errors, assume the market is open rather than skip a brief.
    """
    now = now or datetime.now(ET)
    try:
        import pandas_market_calendars as mcal

        sched = mcal.get_calendar("NYSE").schedule(start_date=now.date(), end_date=now.date())
    except Exception as e:
        print(f"Market calendar unavailable ({e}); assuming open.")
        return {"close": None, "early": False}

    if sched.empty:
        return None
    close = sched.iloc[0]["market_close"].tz_convert(ET).to_pydatetime()
    return {"close": close, "early": (close.hour, close.minute) < (16, 0)}