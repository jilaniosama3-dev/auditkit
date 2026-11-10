"""CSV loading and normalisation shared by all tools."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

DATE_FORMATS = (
    "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d-%b-%Y", "%d-%b-%y",
    "%d %b %Y", "%m/%d/%Y", "%Y/%m/%d", "%d.%m.%Y",
)


@dataclass
class Record:
    row: int                      # 1-based data row number in the source file
    amount: Decimal
    date: Optional[date] = None
    text: str = ""
    raw: dict = field(default_factory=dict)


def parse_amount(value: str) -> Decimal:
    """Parse '1,234.50', '(500)', '-500', 'Rs 1,000' into a Decimal.

    Parentheses mean negative, as in accounting exports.
    """
    s = (value or "").strip()
    if not s:
        raise ValueError("empty amount")
    negative = s.startswith("(") and s.endswith(")")
    cleaned = "".join(ch for ch in s if ch.isdigit() or ch in ".-")
    if cleaned.endswith("-"):          # trailing minus, e.g. '500-'
        negative, cleaned = True, cleaned[:-1]
    try:
        amt = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"cannot parse amount {value!r}") from exc
    return -abs(amt) if negative else amt


def parse_date(value: str, fmt: Optional[str] = None) -> Optional[date]:
    s = (value or "").strip()
    if not s:
        return None
    for f in ([fmt] if fmt else DATE_FORMATS):
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            continue
    raise ValueError(f"cannot parse date {value!r}")


def read_records(path, amount_col="amount", date_col="date", text_col="reference",
                 date_format=None, require_date=False):
    """Read a CSV into Records. Raises ValueError with row numbers on bad data."""
    records = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        headers = {h.strip().lower(): h for h in (reader.fieldnames or [])}

        def col(name):
            return headers.get(name.lower()) if name else None

        a_col = col(amount_col)
        if a_col is None:
            raise ValueError(f"{path}: no column named {amount_col!r} (found: {list(headers)})")
        d_col, t_col = col(date_col), col(text_col)
        if require_date and d_col is None:
            raise ValueError(f"{path}: no column named {date_col!r}")
        for i, row in enumerate(reader, start=1):
            try:
                rec = Record(
                    row=i,
                    amount=parse_amount(row[a_col]),
                    date=parse_date(row[d_col], date_format) if d_col else None,
                    text=(row[t_col] or "").strip() if t_col else "",
                    raw=row,
                )
            except ValueError as exc:
                raise ValueError(f"{path} row {i}: {exc}") from exc
            records.append(rec)
    return records
