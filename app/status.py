from datetime import datetime, timezone

from .shop import parse_utc

STUCK_AFTER_DAYS = {
    "Received": 1,
    "Diagnosing": 3,
    "Waiting for parts": 5,
    "Repairing": 4,
    "Ready": 2,
    "Picked up": None,
}

STATUSES = list(STUCK_AFTER_DAYS)

LAST_STATUS = STATUSES[-1]

def next_status(status):
    """Return the status that follows this one, or None if it is the last."""
    position = STATUSES.index(status)
    if position == len(STATUSES) - 1:
        return None
    return STATUSES[position + 1]

def is_open(status):
    """True while the car is still in the shop."""
    return status != LAST_STATUS

def status_class(status):
    """Turn a status into a CSS name, so Waiting for parts becomes waiting-for-parts."""
    return status.lower().replace(" ", "-")

def days_in_status(changed_at):
    """Whole days since the last status change (stored in UTC)."""
    changed = parse_utc(changed_at)
    if changed is None:
        return 0
    return max(0, (datetime.now(timezone.utc) - changed).days)

def days_late(job):
    """Days past the stuck limit, the first late day counts as 1. Zero if not late."""
    limit = STUCK_AFTER_DAYS.get(job["status"])
    if limit is None:
        return 0
    return max(0, days_in_status(job["status_changed_at"]) - limit + 1)

def is_stuck(job):
    """True if the job has sat in its current status for too long."""
    return days_late(job) > 0

def init_app(app):
    """Make the status helpers usable in every template."""
    app.add_template_filter(status_class)
    app.add_template_global(next_status)
    app.add_template_global(is_open)
    app.add_template_global(days_in_status)
    app.add_template_global(days_late)
    app.add_template_global(is_stuck)