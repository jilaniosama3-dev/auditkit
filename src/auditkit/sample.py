"""Audit sampling: monetary unit sampling (MUS) and simple random sampling."""

from __future__ import annotations

import random
from decimal import Decimal
from typing import List

from .records import Record


def mus(records: List[Record], n: int, seed: int = None):
    """Monetary unit (probability-proportional-to-size) sample of `n` items.

    Systematic selection: interval = total absolute value / n, random start
    inside the first interval. Items whose value is >= interval are always
    selected (high-value items). Returns (selected_records, interval).
    Zero-value items cannot be selected by MUS and are ignored.
    """
    if n <= 0:
        raise ValueError("sample size must be positive")
    items = [r for r in records if r.amount != 0]
    total = sum((abs(r.amount) for r in items), Decimal(0))
    if total == 0:
        raise ValueError("population has no monetary value")
    interval = total / n
    rng = random.Random(seed)
    start = Decimal(str(rng.random())) * interval

    selected, cumulative = [], Decimal(0)
    point = start
    for r in items:
        lo, hi = cumulative, cumulative + abs(r.amount)
        hit = False
        while point < hi:         # a large item can be hit more than once
            if point >= lo:
                hit = True
            point += interval
        if hit:
            selected.append(r)
        cumulative = hi
    return selected, interval


def random_sample(records: List[Record], n: int, seed: int = None):
    if not 0 < n <= len(records):
        raise ValueError(f"sample size must be between 1 and {len(records)}")
    rng = random.Random(seed)
    picked = rng.sample(range(len(records)), n)
    return [records[i] for i in sorted(picked)]
