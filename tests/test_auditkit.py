import csv
import io
from contextlib import redirect_stdout
from datetime import date
from decimal import Decimal

import pytest

from auditkit import benford, checks, cli, sample
from auditkit.match import match
from auditkit.records import Record, parse_amount, parse_date, read_records


def rec(amount, d=None, text="", row=1):
    return Record(row=row, amount=Decimal(str(amount)), date=d, text=text)


def test_parse_amount_variants():
    assert parse_amount("1,234.50") == Decimal("1234.50")
    assert parse_amount("(500)") == Decimal("-500")
    assert parse_amount("500-") == Decimal("-500")
    assert parse_amount("Rs 1,000") == Decimal("1000")
    with pytest.raises(ValueError):
        parse_amount("abc")


def test_parse_date_formats():
    assert parse_date("2026-06-02") == date(2026, 6, 2)
    assert parse_date("02/06/2026") == date(2026, 6, 2)
    assert parse_date("02-Jun-2026") == date(2026, 6, 2)
    assert parse_date("") is None


def test_match_prefers_reference_and_never_reuses_bank_line():
    ledger = [rec(100, date(2026, 6, 1), "CHQ 11 Alpha", 1),
              rec(100, date(2026, 6, 1), "CHQ 12 Beta", 2)]
    bank = [rec(100, date(2026, 6, 2), "CHQ 12 BETA", 1),
            rec(100, date(2026, 6, 3), "CHQ 11 ALPHA", 2)]
    matches, left = match(ledger, bank)
    assert matches[0].bank.row == 2 and matches[1].bank.row == 1
    assert left == []


def test_match_window_and_tolerance():
    ledger = [rec(100, date(2026, 6, 1), "x1")]
    far = [rec(100, date(2026, 6, 30), "x1")]
    assert match(ledger, far, window=7)[0][0].status == "unmatched"
    close = [rec("100.40", date(2026, 6, 2), "x1")]
    assert match(ledger, close, tolerance=Decimal("0.5"))[0][0].status == "matched"
    assert match(ledger, close)[0][0].status == "unmatched"


def test_duplicate_posting_leaves_one_untraced():
    ledger = [rec(42000, date(2026, 6, 9), "CHQ 1004 Alpha", 1),
              rec(42000, date(2026, 6, 12), "CHQ 1004 Alpha", 2)]
    bank = [rec(42000, date(2026, 6, 10), "CHQ 1004 ALPHA", 1)]
    matches, _ = match(ledger, bank)
    assert sorted(m.status for m in matches) == ["matched", "unmatched"]


def test_mus_selects_large_items_and_is_reproducible():
    recs = [rec(1_000_000, row=1)] + [rec(100, row=i) for i in range(2, 102)]
    picked, interval = sample.mus(recs, 5, seed=7)
    assert 1 in [r.row for r in picked]
    again, _ = sample.mus(recs, 5, seed=7)
    assert [r.row for r in picked] == [r.row for r in again]


def test_mus_rejects_bad_input():
    with pytest.raises(ValueError):
        sample.mus([rec(0)], 3)
    with pytest.raises(ValueError):
        sample.mus([rec(10)], 0)


def test_random_sample_size_and_seed():
    recs = [rec(i + 1, row=i + 1) for i in range(50)]
    a = sample.random_sample(recs, 10, seed=1)
    assert len(a) == 10
    assert [r.row for r in a] == [r.row for r in sample.random_sample(recs, 10, seed=1)]


def test_benford_conforming_vs_uniform():
    import math
    conf = []
    for d in range(1, 10):
        conf += [rec(d * 100)] * round(1000 * math.log10(1 + 1 / d))
    assert benford.analyse(conf)["band"] == "close conformity"
    uniform = [rec(d * 100) for d in range(1, 10) for _ in range(100)]
    res = benford.analyse(uniform)
    assert res["chi2_reject"] and res["band"] == "nonconformity"


def test_first_digit_small_and_negative():
    assert benford.first_digit(Decimal("0.0345")) == 3
    assert benford.first_digit(Decimal("-912")) == 9
    assert benford.first_digit(Decimal("0")) is None


def test_duplicates_and_gaps():
    recs = [rec(500, date(2026, 1, 1), "CHQ 101", 1), rec(500, date(2026, 1, 1), "CHQ 102", 2),
            rec(900, date(2026, 1, 2), "CHQ 104", 3), rec(900, date(2026, 1, 5), "CHQ 104", 4)]
    reasons = [g[0] for g in checks.duplicates(recs)]
    assert "same amount and date" in reasons and "same amount and reference" in reasons
    missing, dups = checks.sequence_gaps(recs)
    assert missing == [103] and dups == [104]


def test_cli_end_to_end(tmp_path, capsys):
    out = tmp_path / "out.csv"
    rc = cli.main(["match", "examples/ledger.csv", "examples/bank.csv", "--out", str(out)])
    assert rc == 0
    rows = list(csv.DictReader(open(out)))
    statuses = [r["status"] for r in rows]
    assert statuses.count("matched") == 4 and statuses.count("unmatched") == 2
    assert statuses.count("bank_only") == 1


def test_cli_reports_bad_file(capsys):
    assert cli.main(["benford", "nope.csv"]) == 1
