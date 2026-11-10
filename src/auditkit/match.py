"""Trace ledger entries to bank statement lines (payment tracing)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from .records import Record

_TOKEN = re.compile(r"[a-z0-9]{3,}")


def _tokens(text: str) -> set:
    return set(_TOKEN.findall(text.lower()))


@dataclass
class Match:
    ledger: Record
    bank: Optional[Record]
    day_gap: Optional[int] = None
    text_score: float = 0.0
    status: str = "unmatched"     # matched | unmatched


def _score(ledger: Record, bank: Record, window: int):
    """Return (score, day_gap, text_score) or None if not a candidate."""
    gap = 0
    if ledger.date and bank.date:
        gap = abs((bank.date - ledger.date).days)
        if gap > window:
            return None
    lt, bt = _tokens(ledger.text), _tokens(bank.text)
    text = len(lt & bt) / len(lt) if lt else 0.0
    # Closer dates and stronger reference overlap rank higher.
    return (text * 10) - gap, gap, text


def match(ledger: List[Record], bank: List[Record], tolerance: Decimal = Decimal("0"),
          window: int = 7):
    """Pair each ledger entry with at most one bank line.

    A bank line is a candidate when amounts agree within `tolerance` and the
    dates are within `window` days. All candidate pairs are ranked globally by
    reference overlap then date proximity, and assigned greedily so one bank
    line is never used twice.
    """
    pairs = []
    for li, l in enumerate(ledger):
        for bi, b in enumerate(bank):
            if abs(l.amount - b.amount) > tolerance:
                continue
            s = _score(l, b, window)
            if s:
                pairs.append((s[0], li, bi, s[1], s[2]))
    pairs.sort(key=lambda p: (-p[0], p[1], p[2]))

    used_l, used_b, results = set(), set(), {}
    for _, li, bi, gap, text in pairs:
        if li in used_l or bi in used_b:
            continue
        used_l.add(li)
        used_b.add(bi)
        results[li] = Match(ledger[li], bank[bi], gap, round(text, 2), "matched")

    matches = [results.get(i, Match(l, None)) for i, l in enumerate(ledger)]
    unmatched_bank = [b for bi, b in enumerate(bank) if bi not in used_b]
    return matches, unmatched_bank
