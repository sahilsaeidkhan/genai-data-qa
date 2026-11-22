"""Data quality checks for CSV files.

The check set mirrors the checks that real validation tools run
(Great Expectations expectations, Pandera schema checks), reduced to the
subset that makes sense for a quick look at one CSV:

- missing values per column        (GE: expect_column_values_to_not_be_null,
                                     Pandera: nullable=False)
- exact duplicate rows              (GE: expect_table_values_to_be_unique style)
- near-duplicate rows               (same row modulo case / extra spaces)
- numeric outliers, IQR method      (GE: expect_column_values_to_be_between,
                                     with the range learned from the data)
- type consistency                  (Pandera: dtype checks)
    * numbers stored as text ("1,200", "Rs 850" style formatting)
    * non-numeric junk in a mostly numeric column ("twenty" in an age column)
    * mixed date formats in one column
- constant columns                  (one value everywhere, carries no signal)
- empty columns                     (nothing in them at all)
- duplicate values in id columns    (GE: expect_column_values_to_be_unique,
                                     Pandera: Column(unique=True))

Like Pandera's lazy validation, every check collects ALL of its failures
with row numbers instead of stopping at the first one.

Row numbers are 1-based data rows: row 1 is the first row under the header.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y/%m/%d",
    "%d %b %Y",
    "%d %B %Y",
    "%b %d, %Y",
    "%Y-%m-%d %H:%M:%S",
]

FORMAT_LABELS = {
    "%Y-%m-%d": "2026-01-05 (ISO)",
    "%d/%m/%Y": "05/01/2026 (day/month/year)",
    "%d-%m-%Y": "05-01-2026 (day-month-year)",
    "%Y/%m/%d": "2026/01/05",
    "%d %b %Y": "05 Jan 2026",
    "%d %B %Y": "05 January 2026",
    "%b %d, %Y": "Jan 05, 2026",
    "%Y-%m-%d %H:%M:%S": "2026-01-05 14:30:00 (ISO with time)",
}

CURRENCY_SYMBOLS = "₹$€£"


@dataclass
class Finding:
    check: str
    column: str | None
    rows: list[int] = field(default_factory=list)
    info: dict = field(default_factory=dict)


@dataclass
class CheckResult:
    key: str
    title: str
    passed: bool
    findings: list[Finding] = field(default_factory=list)


# --------------------------------------------------------------------------
# loading + small helpers
# --------------------------------------------------------------------------

def load_csv(source) -> pd.DataFrame:
    """Read a CSV as raw text so the checks see what is actually in the file.

    Everything stays a string; empty cells become NaN. Type problems are
    then found by the checks instead of being hidden by parser guessing.
    """
    df = pd.read_csv(source, dtype=str, keep_default_na=True)
    return df.reset_index(drop=True)


def _is_missing(value) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    return isinstance(value, str) and value.strip() == ""


def _row_numbers(mask: pd.Series) -> list[int]:
    """Boolean mask over a reset RangeIndex -> 1-based data row numbers."""
    return [int(i) + 1 for i in mask[mask].index]


def _plain_float(value):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _clean_float(value):
    """Float after removing thousands separators and currency symbols."""
    text = str(value).strip().strip(CURRENCY_SYMBOLS).strip()
    text = text.replace(",", "")
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _date_format_of(value):
    text = str(value).strip()
    for fmt in DATE_FORMATS:
        try:
            datetime.strptime(text, fmt)
            return fmt
        except ValueError:
            continue
    return None


def _column_profile(series: pd.Series) -> dict:
    """Classify the non-missing values of one column.

    Returns counts of values that parse as plain numbers, numbers only
    after cleanup, dates (per format), and values that parse as neither.
    """
    values = [v for v in series.tolist() if not _is_missing(v)]
    profile = {
        "n": len(values),
        "plain_num_rows": [],
        "clean_num_rows": [],
        "num_values": {},          # row -> float (cleanup parse)
        "date_rows_by_format": {},  # format -> [rows]
        "other_rows": [],
    }
    for idx, value in enumerate(series.tolist()):
        if _is_missing(value):
            continue
        row = idx + 1
        plain = _plain_float(value)
        if plain is not None:
            profile["plain_num_rows"].append(row)
            profile["num_values"][row] = plain
            continue
        cleaned = _clean_float(value)
        if cleaned is not None:
            profile["clean_num_rows"].append(row)
            profile["num_values"][row] = cleaned
            continue
        fmt = _date_format_of(value)
        if fmt is not None:
            profile["date_rows_by_format"].setdefault(fmt, []).append(row)
            continue
        profile["other_rows"].append(row)
    return profile


def _looks_numeric(profile: dict) -> bool:
    if profile["n"] < 3:
        return False
    parsed = len(profile["plain_num_rows"]) + len(profile["clean_num_rows"])
    return parsed / profile["n"] >= 0.7


def _looks_date_like(profile: dict) -> bool:
    if profile["n"] < 3:
        return False
    dated = sum(len(r) for r in profile["date_rows_by_format"].values())
    return dated / profile["n"] >= 0.7


# --------------------------------------------------------------------------
# individual checks
# --------------------------------------------------------------------------

def check_missing_values(df: pd.DataFrame) -> CheckResult:
    findings = []
    for col in df.columns:
        series = df[col]
        if series.map(_is_missing).all():
            continue  # fully empty columns are reported by their own check
        mask = series.map(_is_missing)
        rows = _row_numbers(mask)
        if rows:
            findings.append(Finding(
                check="missing_values", column=col, rows=rows,
                info={"count": len(rows), "total": len(df),
                      "pct": round(100 * len(rows) / len(df), 1)},
            ))
    return CheckResult("missing_values", "Missing values",
                       not findings, findings)


def _duplicate_groups(df: pd.DataFrame) -> list[list[int]]:
    groups = []
    grouped = df.groupby(list(df.columns), dropna=False, sort=False)
    for _, idx in grouped.groups.items():
        if len(idx) > 1:
            groups.append(sorted(int(i) + 1 for i in idx))
    return groups


def check_exact_duplicates(df: pd.DataFrame) -> CheckResult:
    findings = [Finding(check="exact_duplicates", column=None, rows=rows,
                        info={"copies": len(rows)})
                for rows in _duplicate_groups(df)]
    return CheckResult("exact_duplicates", "Exact duplicate rows",
                       not findings, findings)


def _normalized(df: pd.DataFrame) -> pd.DataFrame:
    def norm(value):
        if _is_missing(value):
            return None
        text = re.sub(r"\s+", " ", str(value).strip()).casefold()
        return text
    return df.map(norm)


def check_near_duplicates(df: pd.DataFrame) -> CheckResult:
    exact_sets = {frozenset(rows) for rows in _duplicate_groups(df)}
    findings = []
    for rows in _duplicate_groups(_normalized(df)):
        if frozenset(rows) in exact_sets:
            continue  # already reported as an exact duplicate
        findings.append(Finding(check="near_duplicates", column=None,
                                rows=rows, info={"copies": len(rows)}))
    return CheckResult("near_duplicates", "Near-duplicate rows",
                       not findings, findings)


def check_numeric_outliers(df: pd.DataFrame, profiles: dict) -> CheckResult:
    findings = []
    for col in df.columns:
        profile = profiles[col]
        if not _looks_numeric(profile):
            continue
        values = pd.Series(profile["num_values"])  # index = row number
        if len(values) < 8:
            continue
        q1, q3 = values.quantile(0.25), values.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        bad = values[(values < low) | (values > high)]
        if len(bad):
            findings.append(Finding(
                check="numeric_outliers", column=col,
                rows=sorted(int(r) for r in bad.index),
                info={"values": {int(r): float(v) for r, v in bad.items()},
                      "low": round(float(low), 2), "high": round(float(high), 2),
                      "q1": round(float(q1), 2), "q3": round(float(q3), 2)},
            ))
    return CheckResult("numeric_outliers", "Numeric outliers (IQR)",
                       not findings, findings)


def check_type_consistency(df: pd.DataFrame, profiles: dict) -> CheckResult:
    findings = []
    for col in df.columns:
        profile = profiles[col]
        if _looks_numeric(profile):
            if profile["clean_num_rows"]:
                findings.append(Finding(
                    check="numbers_as_text", column=col,
                    rows=profile["clean_num_rows"],
                    info={"examples": [str(df[col].iloc[r - 1])
                                       for r in profile["clean_num_rows"][:3]]},
                ))
            junk = profile["other_rows"] + [
                row for rows in profile["date_rows_by_format"].values()
                for row in rows
            ]
            if junk:
                findings.append(Finding(
                    check="non_numeric_in_numeric", column=col,
                    rows=sorted(junk),
                    info={"examples": [str(df[col].iloc[r - 1])
                                       for r in sorted(junk)[:3]]},
                ))
        elif _looks_date_like(profile):
            formats = profile["date_rows_by_format"]
            if len(formats) > 1:
                rows = sorted(r for rs in formats.values() for r in rs)
                findings.append(Finding(
                    check="mixed_date_formats", column=col, rows=rows,
                    info={"formats": {
                        FORMAT_LABELS.get(fmt, fmt): rs
                        for fmt, rs in formats.items()}},
                ))
            if profile["other_rows"]:
                findings.append(Finding(
                    check="non_date_in_date", column=col,
                    rows=profile["other_rows"],
                    info={"examples": [str(df[col].iloc[r - 1])
                                       for r in profile["other_rows"][:3]]},
                ))
    return CheckResult("type_consistency", "Type and format consistency",
                       not findings, findings)


def check_constant_columns(df: pd.DataFrame) -> CheckResult:
    findings = []
    for col in df.columns:
        present = [v for v in df[col].tolist() if not _is_missing(v)]
        if present and len(set(map(str, present))) == 1:
            findings.append(Finding(
                check="constant_column", column=col, rows=[],
                info={"value": str(present[0]), "count": len(present)},
            ))
    return CheckResult("constant_columns", "Constant columns",
                       not findings, findings)


def check_empty_columns(df: pd.DataFrame) -> CheckResult:
    findings = [Finding(check="empty_column", column=col, rows=[],
                        info={"total": len(df)})
                for col in df.columns if df[col].map(_is_missing).all()]
    return CheckResult("empty_columns", "Empty columns",
                       not findings, findings)


_ID_NAME = re.compile(r"(^id$|_id$|^id_|_id_)", re.IGNORECASE)


def check_id_uniqueness(df: pd.DataFrame) -> CheckResult:
    findings = []
    for col in df.columns:
        if not _ID_NAME.search(str(col)):
            continue
        present = df[col].map(lambda v: None if _is_missing(v) else str(v))
        present = present[present.notna()]
        if len(present) < 3:
            continue
        unique_ratio = present.nunique() / len(present)
        if unique_ratio < 0.9 or present.nunique() == len(present):
            continue  # either not id-like in practice, or perfectly unique
        dup_values = present[present.duplicated(keep=False)]
        rows = sorted(int(i) + 1 for i in dup_values.index)
        findings.append(Finding(
            check="id_duplicates", column=col, rows=rows,
            info={"values": sorted(dup_values.unique().tolist())},
        ))
    return CheckResult("id_uniqueness", "Duplicate values in ID columns",
                       not findings, findings)


# --------------------------------------------------------------------------
# runner
# --------------------------------------------------------------------------

ALL_CHECKS = [
    "missing_values", "exact_duplicates", "near_duplicates",
    "numeric_outliers", "type_consistency", "constant_columns",
    "empty_columns", "id_uniqueness",
]


def run_all_checks(df: pd.DataFrame) -> tuple[list[CheckResult], float]:
    """Run every check, return (results, elapsed_seconds)."""
    start = time.perf_counter()
    profiles = {col: _column_profile(df[col]) for col in df.columns}
    results = [
        check_missing_values(df),
        check_exact_duplicates(df),
        check_near_duplicates(df),
        check_numeric_outliers(df, profiles),
        check_type_consistency(df, profiles),
        check_constant_columns(df),
        check_empty_columns(df),
        check_id_uniqueness(df),
    ]
    return results, time.perf_counter() - start


def flagged_rows(results: list[CheckResult]) -> list[int]:
    rows = set()
    for result in results:
        for finding in result.findings:
            rows.update(finding.rows)
    return sorted(rows)
