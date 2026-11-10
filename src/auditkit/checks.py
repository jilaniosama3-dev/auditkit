"""Completeness and duplicate tests."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import List

from .records import Record


def duplicates(records: List[Record], by_reference: bool = True):
    """Group records that look like duplicate postings.

    Two keys are checked: (amount, date) and, optionally, (amount, reference).
    Returns a list of (reason, [records]) groups with 2+ members.
    """
    groups = []
    keys = [("same amount and date", lambda r: (r.amount, r.date) if r.date else None)]
    if by_reference:
        keys.append(("same amount and reference",
                     lambda r: (r.amount, r.text.lower()) if r.text else None))
    for reason, keyfn in keys:
        buckets = defaultdict(list)
        for r in records:
            k = keyfn(r)
            if k is not None:
                buckets[k].append(r)
        groups += [(reason, v) for v in buckets.values() if len(v) > 1]
    return groups


def sequence_gaps(records: List[Record]):
    """Find missing numbers in a document sequence (cheque, invoice, GRN no.).

    The number is the last run of digits in each record's text; a common
    prefix is ignored. Returns (missing_numbers, duplicate_numbers).
    """
    nums = []
    for r in records:
        m = re.findall(r"\d+", r.text)
        if m:
            nums.append(int(m[-1]))
    if not nums:
        raise ValueError("no numbers found in the text column")
    seen, dups = set(), set()
    for n in nums:
        (dups if n in seen else seen).add(n)
    missing = [n for n in range(min(seen), max(seen) + 1) if n not in seen]
    return missing, sorted(dups)
