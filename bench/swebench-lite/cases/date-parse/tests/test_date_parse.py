import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1] / "repo"
sys.path.insert(0, str(REPO))

from dates.parser import parse_date  # noqa: E402
from dates.utils import to_utc  # noqa: E402


def test_parse_iso_date():
    dt = parse_date("2024-03-15")
    assert dt.year == 2024
    assert dt.month == 3
    assert dt.day == 15


def test_parse_us_date():
    dt = parse_date("03/15/2024")
    assert dt.month == 3
    assert dt.day == 15


def test_invalid_date_raises():
    try:
        parse_date("not-a-date")
        assert False, "expected ValueError"
    except (ValueError, TypeError):
        pass


def test_naive_to_utc():
    dt = datetime(2024, 1, 1, 12, 0, 0)
    utc = to_utc(dt)
    assert utc.tzinfo == timezone.utc
