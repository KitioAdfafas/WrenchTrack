from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from flask import current_app

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

def parse_utc(value):
    """Read a UTC timestamp from SQLite. Returns None if it is not one."""
    try:
        return datetime.strptime(value, TIMESTAMP_FORMAT).replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None

def utc_text(moment):
    """Write a time the way SQLite stores UTC timestamps."""
    return moment.astimezone(timezone.utc).strftime(TIMESTAMP_FORMAT)

def shop_zone():
    """The shop time zone from SHOP_TIMEZONE."""
    return ZoneInfo(current_app.config["SHOP_TIMEZONE"])

def shop_now():
    """The current time in the shop."""
    return datetime.now(shop_zone())

def shop_today():
    """Today's date in the shop, which can differ from the UTC date around midnight."""
    return shop_now().date()

def days_in_shop(date_received):
    """Whole days since the car came in, counted by the shop calendar."""
    try:
        received = date.fromisoformat(date_received)
    except (TypeError, ValueError):
        return 0
    return max(0, (shop_today() - received).days)

def localtime(value):
    """Turn a UTC timestamp from SQLite into the shop time, like 2026-10-24 15:00."""
    if not value:
        return ""
    moment = parse_utc(value)
    if moment is None:
        return value
    return moment.astimezone(shop_zone()).strftime("%Y-%m-%d %H:%M")

def money(value):
    """Format an amount with two decimals and the shop currency."""
    text = f"{value or 0:.2f}"
    currency = current_app.config["CURRENCY"].strip()
    if not currency:
        return text
    return f"{text} {currency}"

def init_app(app):
    """Make the time and money helpers usable in every template."""
    app.add_template_filter(localtime)
    app.add_template_filter(money)
    app.add_template_global(days_in_shop)