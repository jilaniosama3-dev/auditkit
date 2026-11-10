"""Command-line interface."""

from __future__ import annotations

import argparse
import csv
import sys
from decimal import Decimal

from . import __version__, benford, checks, sample
from .match import match
from .records import read_records


def _common(p, text_default="reference"):
    p.add_argument("--amount-col", default="amount")
    p.add_argument("--date-col", default="date")
    p.add_argument("--text-col", default=text_default)
    p.add_argument("--date-format", default=None, help="strptime format, e.g. %%d/%%m/%%Y")


def _load(args, path, **kw):
    return read_records(path, args.amount_col, args.date_col, args.text_col,
                        args.date_format, **kw)


def cmd_match(args):
    ledger = _load(args, args.ledger)
    bank_args = argparse.Namespace(**vars(args))
    bank_args.text_col = args.bank_text_col
    bank = _load(bank_args, args.bank)
    matches, unmatched_bank = match(ledger, bank, Decimal(args.tolerance), args.window)

    out = open(args.out, "w", newline="") if args.out else sys.stdout
    w = csv.writer(out)
    w.writerow(["ledger_row", "ledger_date", "ledger_ref", "amount", "status",
                "bank_row", "bank_date", "bank_description", "day_gap", "ref_overlap"])
    for m in matches:
        b = m.bank
        w.writerow([m.ledger.row, m.ledger.date, m.ledger.text, m.ledger.amount, m.status,
                    b.row if b else "", b.date if b else "", b.text if b else "",
                    m.day_gap if b else "", m.text_score if b else ""])
    for b in unmatched_bank:
        w.writerow(["", "", "", b.amount, "bank_only", b.row, b.date, b.text, "", ""])
    if args.out:
        out.close()
    n_ok = sum(1 for m in matches if m.bank)
    print(f"{n_ok}/{len(matches)} ledger entries traced; "
          f"{len(matches) - n_ok} untraced; {len(unmatched_bank)} bank lines not in ledger.",
          file=sys.stderr)


def cmd_sample(args):
    recs = _load(args, args.file)
    if args.method == "mus":
        picked, interval = sample.mus(recs, args.n, args.seed)
        print(f"# MUS interval: {interval:.2f}  seed: {args.seed}", file=sys.stderr)
    else:
        picked = sample.random_sample(recs, args.n, args.seed)
    w = csv.writer(sys.stdout)
    w.writerow(["row", "date", "reference", "amount"])
    for r in picked:
        w.writerow([r.row, r.date or "", r.text, r.amount])
    print(f"# {len(picked)} items selected from {len(recs)}", file=sys.stderr)


def cmd_benford(args):
    res = benford.analyse(_load(args, args.file))
    print(f"Items tested: {res['n']}")
    print("Digit  Count  Actual   Expected")
    for r in res["rows"]:
        print(f"  {r['digit']}    {r['count']:5d}  {r['actual']:.3f}    {r['expected']:.3f}")
    print(f"Chi-square: {res['chi2']:.2f} (critical 15.51 at 5%) -> "
          f"{'REJECT conformity' if res['chi2_reject'] else 'no rejection'}")
    print(f"MAD: {res['mad']:.4f} -> {res['band']}")
    print("Note: a deviation is a reason to look closer, not proof of error or fraud.")


def cmd_duplicates(args):
    groups = checks.duplicates(_load(args, args.file), not args.no_reference)
    if not groups:
        print("No potential duplicates found.")
        return
    for reason, recs in groups:
        print(f"[{reason}]")
        for r in recs:
            print(f"  row {r.row}: {r.date or '-'}  {r.text or '-'}  {r.amount}")


def cmd_gaps(args):
    missing, dups = checks.sequence_gaps(_load(args, args.file))
    print(f"Missing numbers ({len(missing)}): {missing if missing else 'none'}")
    print(f"Duplicate numbers ({len(dups)}): {dups if dups else 'none'}")


def build_parser():
    p = argparse.ArgumentParser(prog="auditkit", description="Tools for audit working papers.")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("match", help="trace ledger entries to a bank statement")
    m.add_argument("ledger"); m.add_argument("bank")
    _common(m)
    m.add_argument("--bank-text-col", default="description")
    m.add_argument("--tolerance", default="0", help="allowed amount difference (default 0)")
    m.add_argument("--window", type=int, default=7, help="allowed day difference (default 7)")
    m.add_argument("--out", help="write result CSV here instead of stdout")
    m.set_defaults(func=cmd_match)

    s = sub.add_parser("sample", help="select an audit sample")
    s.add_argument("file"); s.add_argument("-n", type=int, required=True)
    s.add_argument("--method", choices=["mus", "random"], default="mus")
    s.add_argument("--seed", type=int, help="record this in the working paper to reperform")
    _common(s)
    s.set_defaults(func=cmd_sample)

    b = sub.add_parser("benford", help="first-digit Benford test")
    b.add_argument("file"); _common(b)
    b.set_defaults(func=cmd_benford)

    d = sub.add_parser("duplicates", help="find potential duplicate postings")
    d.add_argument("file"); _common(d)
    d.add_argument("--no-reference", action="store_true")
    d.set_defaults(func=cmd_duplicates)

    g = sub.add_parser("gaps", help="find gaps/duplicates in a document number sequence")
    g.add_argument("file"); _common(g)
    g.set_defaults(func=cmd_gaps)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
