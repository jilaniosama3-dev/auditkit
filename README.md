# auditkit

Small, dependency-free command-line tools for auditors. Works on plain CSV exports, so it fits any accounting system. Python 3.9+, standard library only.

| Command | What it does |
|---|---|
| `auditkit match` | Trace ledger payments to bank statement lines (amount, date window, reference overlap) |
| `auditkit sample` | Monetary unit sampling or random sampling, reproducible with a seed |
| `auditkit benford` | First-digit Benford test with chi-square and MAD conformity |
| `auditkit duplicates` | Potential duplicate postings (same amount + date, same amount + reference) |
| `auditkit gaps` | Missing and duplicate numbers in a cheque / invoice / GRN sequence |

## Install

```
pip install -e .
```

## Payment tracing

```
auditkit match examples/ledger.csv examples/bank.csv --out tracing.csv
```

Output has one row per ledger entry (`matched` / `unmatched`) plus `bank_only` rows for bank lines with no ledger entry. Each bank line is used at most once, so a duplicate posting leaves one entry untraced.

Options: `--tolerance 0.50` (amount difference), `--window 10` (days), `--bank-text-col description`, `--date-format %d/%m/%Y`, plus `--amount-col`, `--date-col`, `--text-col` for other column names. Amounts like `1,234.50`, `(500)` and `500-` are understood.

## Sampling

```
auditkit sample population.csv -n 25 --method mus --seed 2026
```

Record the seed and interval in the working paper so the selection can be reperformed. Items larger than the interval are always selected.

## Other tests

```
auditkit benford payments.csv
auditkit duplicates payments.csv
auditkit gaps cheques.csv --text-col cheque_no
```

## Limits (please read)

- Matching is a **tracing aid**. Review every match and every exception; the tool does not replace judgement or evidence.
- A Benford deviation or a duplicate flag is a reason to look closer, not a finding.
- MUS here selects items; it does not compute evaluation of misstatements.

## Development

```
pip install -e . pytest
pytest
```

Contributions welcome; see issues for ideas (XLSX input, multi-currency, many-to-one matching of batched payments).

## License

MIT
