"""Coercing raw CSV cells into Python values.

The export writes Python literals rather than JSON -- single quotes, ``None``
instead of ``null`` -- so structured cells go through ``ast.literal_eval``, not
``json.loads``. Dates arrive at three precisions ("2019", "2019-10", "2019-10-08")
and counts sometimes arrive as floats ("3761.0").

Every helper here is total: it returns a clean value or ``None`` and never raises.
Rejecting a whole profile because one cell is malformed would be the wrong call
on a dataset this dirty; the field is dropped and the rest of the row is kept.
"""

import ast
import datetime
from decimal import Decimal, InvalidOperation

# Spellings the export uses to mean "absent".
EMPTY_TOKENS = frozenset({"", "none", "null", "nan", "n/a", "-"})

DATE_FORMATS = ("%Y-%m-%d", "%Y-%m", "%Y")

# Column ceilings. Ragged rows shift text into numeric columns, and an
# unbounded int would take the whole profile down with a DataError.
INT16_MIN, INT16_MAX = -32768, 32767
INT32_MIN, INT32_MAX = -2147483648, 2147483647

MAX_LATITUDE = Decimal("90")
MAX_LONGITUDE = Decimal("180")
COORDINATE_PLACES = Decimal("0.000001")


def text(value, *, max_length=None):
    """Strip a cell, mapping the export's empty spellings to ``None``."""
    if not isinstance(value, str):
        value = "" if value is None else str(value)
    cleaned = value.strip()
    if cleaned.lower() in EMPTY_TOKENS:
        return None
    return cleaned[:max_length] if max_length else cleaned


def literal(value, default=None):
    """Evaluate a Python-literal cell, falling back to ``default``."""
    cleaned = text(value)
    if cleaned is None:
        return default
    try:
        return ast.literal_eval(cleaned)
    except (ValueError, SyntaxError, MemoryError, RecursionError):
        return default


def string_list(value):
    parsed = literal(value, [])
    if not isinstance(parsed, (list, tuple, set)):
        return []
    return [item for item in (text(entry) for entry in parsed) if item]


def dict_list(value):
    parsed = literal(value, [])
    if not isinstance(parsed, (list, tuple)):
        return []
    return [entry for entry in parsed if isinstance(entry, dict)]


def mapping(value):
    parsed = literal(value, None)
    return parsed if isinstance(parsed, dict) else None


def integer(value, *, minimum=None, maximum=None):
    """Parse an int, tolerating the float spellings the export emits.

    Values outside ``[minimum, maximum]`` are treated as absent rather than
    stored, because the alternative is a column overflow that fails the row.
    """
    cleaned = text(value)
    if cleaned is None:
        return None
    try:
        parsed = int(float(cleaned))
    except (TypeError, ValueError, OverflowError):
        return None
    if minimum is not None and parsed < minimum:
        return None
    if maximum is not None and parsed > maximum:
        return None
    return parsed


def small_integer(value):
    """An int that has to fit a ``SmallIntegerField``."""
    return integer(value, minimum=INT16_MIN, maximum=INT16_MAX)


def standard_integer(value):
    """An int that has to fit an ``IntegerField``."""
    return integer(value, minimum=INT32_MIN, maximum=INT32_MAX)


def year(value):
    parsed = integer(value)
    if parsed is None or not 1800 <= parsed <= 2200:
        return None
    return parsed


def date(value):
    """Parse a full or partial date; partials resolve to their first day."""
    cleaned = text(value)
    if cleaned is None:
        return None
    candidate = cleaned[:10]
    for fmt in DATE_FORMATS:
        try:
            return datetime.datetime.strptime(candidate, fmt).date()
        except ValueError:
            continue
    return None


def coordinates(value):
    """Split a ``"lat,lon"`` cell into two bounded decimals."""
    cleaned = text(value)
    if cleaned is None or "," not in cleaned:
        return None, None
    raw_latitude, _, raw_longitude = cleaned.partition(",")
    return (
        _coordinate(raw_latitude, MAX_LATITUDE),
        _coordinate(raw_longitude, MAX_LONGITUDE),
    )


def _coordinate(raw, limit):
    cleaned = text(raw)
    if cleaned is None:
        return None
    try:
        parsed = Decimal(cleaned).quantize(COORDINATE_PLACES)
    except (InvalidOperation, ValueError):
        return None
    # The column is numeric(9, 6); anything out of range is bad data, not a
    # place, and would otherwise overflow the column.
    return parsed if abs(parsed) <= limit else None
