"""First-digit Benford's Law test."""

from __future__ import annotations

import math
from collections import Counter
from decimal import Decimal
from typing import List

from .records import Record

EXPECTED = {d: math.log10(1 + 1 / d) for d in range(1, 10)}
CHI2_CRIT_005_DF8 = 15.507     # chi-square critical value, p=0.05, 8 d.f.


def first_digit(amount: Decimal):
    a = abs(amount)
    if a == 0:
        return None
    s = format(a.normalize(), "f").lstrip("0.")
    return int(s[0]) if s else None


def analyse(records: List[Record]):
    digits = [d for d in (first_digit(r.amount) for r in records) if d]
    n = len(digits)
    if n == 0:
        raise ValueError("no non-zero amounts to test")
    counts = Counter(digits)
    rows, chi2, mad = [], 0.0, 0.0
    for d in range(1, 10):
        actual = counts.get(d, 0) / n
        exp = EXPECTED[d]
        chi2 += (counts.get(d, 0) - exp * n) ** 2 / (exp * n)
        mad += abs(actual - exp)
        rows.append({"digit": d, "count": counts.get(d, 0),
                     "actual": actual, "expected": exp})
    mad /= 9
    # Nigrini's MAD conformity bands for first-digit tests.
    if mad <= 0.006:
        band = "close conformity"
    elif mad <= 0.012:
        band = "acceptable conformity"
    elif mad <= 0.015:
        band = "marginally acceptable conformity"
    else:
        band = "nonconformity"
    return {"n": n, "rows": rows, "chi2": chi2, "chi2_reject": chi2 > CHI2_CRIT_005_DF8,
            "mad": mad, "band": band}
