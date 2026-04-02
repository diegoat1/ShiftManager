from datetime import datetime, timezone


def utcnow_naive() -> datetime:
    """Return current UTC time as a naive datetime (matches DB column types)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
