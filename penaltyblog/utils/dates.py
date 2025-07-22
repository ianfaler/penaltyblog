from datetime import datetime, timedelta, timezone

TODAY = datetime.now(tz=timezone.utc).date()
START = TODAY
END = TODAY + timedelta(days=7)

def in_next_week(d):
    """Check if a date is within the next 7 days."""
    return START <= d <= END