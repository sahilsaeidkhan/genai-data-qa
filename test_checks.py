"""Tests: every defect planted in sample_messy.csv must be caught with the
correct row numbers, and sample_clean.csv must pass everything.

Run:  .venv/bin/python -m pytest test_checks.py -v
"""

from pathlib import Path

import pytest

from checks import flagged_rows, load_csv, run_all_checks
from explain import RuleBasedExplainer
from report import build_html_report, build_markdown_report

HERE = Path(__file__).parent


@pytest.fixture(scope="module")
def messy():
    df = load_csv(HERE / "sample_messy.csv")
    results, elapsed = run_all_checks(df)
    return df, results, elapsed


@pytest.fixture(scope="module")
def clean():
    df = load_csv(HERE / "sample_clean.csv")
    results, elapsed = run_all_checks(df)
    return df, results, elapsed


def findings_by_check(results, check_key):
    out = []
    for result in results:
        out.extend(f for f in result.findings if f.check == check_key)
    return out


def one_finding(results, check_key, column=None):
    matches = [f for f in findings_by_check(results, check_key)
               if column is None or f.column == column]
    assert len(matches) == 1, f"expected 1 {check_key} finding for {column}"
    return matches[0]


# ---------------------------------------------------------------- messy --

def test_messy_shape(messy):
    df, _, _ = messy
    assert len(df) == 30 and len(df.columns) == 10


def test_missing_values(messy):
    _, results, _ = messy
    assert set(one_finding(results, "missing_values", "age").rows) == {4, 17}
    assert set(one_finding(results, "missing_values", "email").rows) == {9}
    assert set(one_finding(results, "missing_values", "amount").rows) == {22}
    # coupon_code is fully empty: reported as an empty column, not here
    assert findings_by_check(results, "missing_values") == [
        f for f in findings_by_check(results, "missing_values")
        if f.column != "coupon_code"]


def test_exact_duplicates(messy):
    _, results, _ = messy
    groups = sorted(tuple(f.rows)
                    for f in findings_by_check(results, "exact_duplicates"))
    assert groups == [(5, 12), (8, 20)]


def test_near_duplicates(messy):
    _, results, _ = messy
    groups = [tuple(f.rows)
              for f in findings_by_check(results, "near_duplicates")]
    assert groups == [(3, 15)]


def test_outliers(messy):
    _, results, _ = messy
    amount = one_finding(results, "numeric_outliers", "amount")
    assert amount.rows == [18] and amount.info["values"][18] == 99999.0
    age = one_finding(results, "numeric_outliers", "age")
    assert age.rows == [27] and age.info["values"][27] == 150.0


def test_numbers_as_text(messy):
    _, results, _ = messy
    f = one_finding(results, "numbers_as_text", "amount")
    assert set(f.rows) == {7, 19}


def test_non_numeric_in_numeric(messy):
    _, results, _ = messy
    f = one_finding(results, "non_numeric_in_numeric", "age")
    assert f.rows == [11] and f.info["examples"] == ["twenty"]


def test_mixed_date_formats(messy):
    _, results, _ = messy
    f = one_finding(results, "mixed_date_formats", "signup_date")
    formats = f.info["formats"]
    assert len(formats) == 3
    assert set(formats["05/01/2026 (day/month/year)"]) == {6, 21}
    assert set(formats["05 Jan 2026"]) == {14}
    assert len(formats["2026-01-05 (ISO)"]) == 27


def test_constant_and_empty_columns(messy):
    _, results, _ = messy
    const = one_finding(results, "constant_column", "country")
    assert const.info["value"] == "India"
    one_finding(results, "empty_column", "coupon_code")


def test_id_duplicates(messy):
    _, results, _ = messy
    f = one_finding(results, "id_duplicates", "order_id")
    assert set(f.rows) == {3, 5, 8, 12, 15, 20}
    assert set(f.info["values"]) == {"1003", "1005", "1008"}


def test_messy_fails_most_checks(messy):
    _, results, _ = messy
    failed = [r for r in results if not r.passed]
    assert len(failed) == len(results)  # all 8 check groups fire
    assert len(flagged_rows(results)) >= 15


def test_explanations_cite_rows(messy):
    _, results, _ = messy
    explainer = RuleBasedExplainer()
    outlier_text = explainer.explain(
        one_finding(results, "numeric_outliers", "amount"))
    assert "row 18 has 99999" in outlier_text
    missing_text = explainer.explain(
        one_finding(results, "missing_values", "age"))
    assert "rows 4, 17" in missing_text
    for result in results:
        for finding in result.findings:
            text = explainer.explain(finding)
            assert len(text) > 40  # a real sentence, not a stub


def test_reports_render(messy):
    df, results, elapsed = messy
    md = build_markdown_report(results, "sample_messy.csv", len(df),
                               len(df.columns), elapsed)
    assert "99999" in md and "Missing values" in md
    html = build_html_report(results, "sample_messy.csv", len(df),
                             len(df.columns), elapsed)
    assert "<html" in html and "FAIL" in html


# ---------------------------------------------------------------- clean --

def test_clean_passes_everything(clean):
    df, results, elapsed = clean
    assert len(df) == 20
    failed = [r.title for r in results if not r.passed]
    assert failed == [], f"clean file failed checks: {failed}"
    assert flagged_rows(results) == []
    assert elapsed >= 0
