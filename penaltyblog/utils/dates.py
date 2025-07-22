from datetime import datetime, timedelta, timezone

def today_utc():
    return datetime.now(tz=timezone.utc).date()

def week_window():
    start = today_utc()
    end   = start + timedelta(days=7)
    return start, end

def in_next_week(d):
    """Check if a date is within the next 7 days."""
    start, end = week_window()
    return start <= d <= end

# Legacy compatibility
TODAY = today_utc()
START = TODAY
END = TODAY + timedelta(days=7)