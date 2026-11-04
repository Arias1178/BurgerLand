import calendar
import datetime as dt
from decimal import InvalidOperation


def format_currency_es_co(value) -> str:
    """Formato monetario colombiano, por ejemplo: $1.234.567."""
    try:
        number = float(value)
    except (TypeError, ValueError, InvalidOperation):
        return "$0"
    if abs(number) < 0.01:
        return "$0"
    integer_part = f"{number:,.0f}".replace(",", ".")
    return f"${integer_part}"


def format_percentage_es_co(value) -> str:
    try:
        return f"{float(value):,.1f}%".replace(",", ".")
    except (TypeError, ValueError, InvalidOperation):
        return "0,0%"


def _last_day_of_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def _previous_fortnight_for_current(current_start: dt.date, current_end: dt.date) -> tuple[dt.date, dt.date]:
    if current_start.day == 1 and current_end.day <= 15:
        prev_month = (current_start.month - 1) if current_start.month > 1 else 12
        prev_year = current_start.year if current_start.month > 1 else current_start.year - 1
        prev_last_day = _last_day_of_month(prev_year, prev_month)
        return dt.date(prev_year, prev_month, 16), dt.date(prev_year, prev_month, prev_last_day)

    if current_start.day == 16:
        mid_month = current_start.replace(day=15)
        return dt.date(mid_month.year, mid_month.month, 1), dt.date(mid_month.year, mid_month.month, 15)

    return current_start, current_end


def get_fortnight_periods(reference_date: dt.date, mode: str = "preview"):
    """
    Returns (current_period, previous_period) for the requested mode.

    Modes:
      - "official": enabled only on day 15 and on the last day of the month.
      - "preview": always enabled, showing the fortnight in progress up to today.
    """
    mode = (mode or "preview").lower()
    year = reference_date.year
    month = reference_date.month
    last_day = _last_day_of_month(year, month)

    if mode == "official":
        if reference_date.day == 15:
            current_start = dt.date(year, month, 1)
            current_end = dt.date(year, month, 15)
            prev_year = year if month > 1 else year - 1
            prev_month = month - 1 if month > 1 else 12
            prev_last = _last_day_of_month(prev_year, prev_month)
            prev_start = dt.date(prev_year, prev_month, 16)
            prev_end = dt.date(prev_year, prev_month, prev_last)
        elif reference_date.day == last_day:
            current_start = dt.date(year, month, 16)
            current_end = dt.date(year, month, last_day)
            prev_start = dt.date(year, month, 1)
            prev_end = dt.date(year, month, 15)
        else:
            return get_fortnight_periods(reference_date, mode="preview")

        current = {
            "start": current_start,
            "end": current_end,
            "label": f"{current_start:%d/%m/%Y} - {current_end:%d/%m/%Y}",
            "kind": "official",
        }
        previous = {
            "start": prev_start,
            "end": prev_end,
            "label": f"{prev_start:%d/%m/%Y} - {prev_end:%d/%m/%Y}",
            "kind": "official",
        }
        return current, previous

    current_start = dt.date(year, month, 1)
    if reference_date.day <= 15:
        current_end = reference_date
        current_start = dt.date(year, month, 1)
        prev_year = year if month > 1 else year - 1
        prev_month = month - 1 if month > 1 else 12
        prev_last = _last_day_of_month(prev_year, prev_month)
        prev_start = dt.date(prev_year, prev_month, 16)
        prev_end = dt.date(prev_year, prev_month, prev_last)
        label = f"Quincena en curso: {reference_date.day} de 15 días"
    else:
        current_start = dt.date(year, month, 16)
        current_end = reference_date
        prev_start = dt.date(year, month, 1)
        prev_end = dt.date(year, month, 15)
        label = f"Quincena en curso: {reference_date.day - 15} de 15 días"

    current = {
        "start": current_start,
        "end": current_end,
        "label": label,
        "kind": "preview",
    }
    previous = {
        "start": prev_start,
        "end": prev_end,
        "label": f"{prev_start:%d/%m/%Y} - {prev_end:%d/%m/%Y}",
        "kind": "preview",
    }
    return current, previous


__all__ = [
    "format_currency_es_co",
    "format_percentage_es_co",
    "get_fortnight_periods",
]
