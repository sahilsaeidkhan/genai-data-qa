"""Plain-English explanations for check findings.

Every finding gets a short explanation that names the column, says how
much data is affected, and quotes the exact row numbers. The explanations
are written by the RuleBasedExplainer below using templates, so the tool
works with no API key and no network.

To use an LLM instead, implement the Explainer interface (one method,
explain(finding) -> str) and pass your class to get_explainer(). The
checks do not care which explainer produced the text. LLMExplainer is a
stub showing where a model call would go; it falls back to the rule-based
text until someone wires a real client into it.
"""

from __future__ import annotations

from checks import Finding


def _row_list(rows: list[int], limit: int = 12) -> str:
    shown = rows[:limit]
    text = ", ".join(str(r) for r in shown)
    if len(rows) > limit:
        text += f", and {len(rows) - limit} more"
    return text


def _rows_word(n: int) -> str:
    return "row" if n == 1 else "rows"


class RuleBasedExplainer:
    """Template explanations. Deterministic, free, works offline."""

    def explain(self, finding: Finding) -> str:
        handler = getattr(self, f"_explain_{finding.check}", None)
        if handler is None:
            return self._explain_generic(finding)
        return handler(finding)

    # one template per check type -------------------------------------

    def _explain_missing_values(self, f: Finding) -> str:
        return (
            f"Column '{f.column}' is blank in {f.info['count']} "
            f"{_rows_word(f.info['count'])} ({f.info['pct']}% of the file): "
            f"rows {_row_list(f.rows)}. Any average, total or group-by on "
            f"'{f.column}' will quietly skip these rows, so the numbers "
            f"downstream will be based on less data than expected."
        )

    def _explain_exact_duplicates(self, f: Finding) -> str:
        return (
            f"Rows {_row_list(f.rows)} are exact copies of each other, "
            f"every column identical. This usually means a record was "
            f"exported or submitted more than once. Counting or summing "
            f"this file as-is will count the same record "
            f"{f.info['copies']} times."
        )

    def _explain_near_duplicates(self, f: Finding) -> str:
        return (
            f"Rows {_row_list(f.rows)} look like the same record typed "
            f"twice with small differences in capitalisation or spacing. "
            f"Exact-duplicate checks miss these, but a person reading the "
            f"file would treat them as one record, so totals can still be "
            f"double-counted."
        )

    def _explain_numeric_outliers(self, f: Finding) -> str:
        values = ", ".join(
            f"row {row} has {value:g}" for row, value in
            sorted(f.info["values"].items())
        )
        return (
            f"Column '{f.column}' mostly sits between {f.info['q1']:g} and "
            f"{f.info['q3']:g}. Using the IQR rule, anything below "
            f"{f.info['low']:g} or above {f.info['high']:g} counts as an "
            f"outlier, and {values}. These are worth a human look: they "
            f"are often a typing slip (an extra zero) or a value recorded "
            f"in the wrong unit, and one value like this can drag an "
            f"average far off."
        )

    def _explain_numbers_as_text(self, f: Finding) -> str:
        examples = ", ".join(f"'{e}'" for e in f.info["examples"])
        return (
            f"In column '{f.column}', the values in rows "
            f"{_row_list(f.rows)} are numbers stored as text ({examples}). "
            f"They carry formatting such as a thousands comma or a "
            f"currency symbol, so software reads them as words, not "
            f"numbers: they will be dropped from sums and averages, or "
            f"break a numeric column when the file is loaded elsewhere."
        )

    def _explain_non_numeric_in_numeric(self, f: Finding) -> str:
        examples = ", ".join(f"'{e}'" for e in f.info["examples"])
        return (
            f"Column '{f.column}' is numeric almost everywhere, but rows "
            f"{_row_list(f.rows)} hold text instead ({examples}). One "
            f"value like this turns the whole column into text when the "
            f"file is loaded, and any calculation on '{f.column}' will "
            f"either fail or silently ignore data."
        )

    def _explain_mixed_date_formats(self, f: Finding) -> str:
        parts = "; ".join(
            f"{label} in rows {_row_list(rows)}"
            for label, rows in f.info["formats"].items()
        )
        return (
            f"Column '{f.column}' mixes date formats: {parts}. Mixed "
            f"formats are risky because day-first and month-first dates "
            f"look alike, so some of these dates can be read as the wrong "
            f"day when the file is parsed. Pick one format and rewrite "
            f"the column in it."
        )

    def _explain_non_date_in_date(self, f: Finding) -> str:
        examples = ", ".join(f"'{e}'" for e in f.info["examples"])
        return (
            f"Column '{f.column}' holds dates almost everywhere, but "
            f"rows {_row_list(f.rows)} hold values that are not dates "
            f"({examples}). These will become blanks or errors when the "
            f"column is parsed as dates."
        )

    def _explain_constant_column(self, f: Finding) -> str:
        return (
            f"Column '{f.column}' has the same value, '{f.info['value']}', "
            f"in all {f.info['count']} rows. A column that never changes "
            f"carries no information for analysis or modelling, and it "
            f"often means a filter was applied at export time that nobody "
            f"documented."
        )

    def _explain_empty_column(self, f: Finding) -> str:
        return (
            f"Column '{f.column}' is empty in every one of the "
            f"{f.info['total']} rows. Either the source system never "
            f"filled it in, or the export dropped its values. It should "
            f"be removed or traced back to the source before the file is "
            f"used."
        )

    def _explain_id_duplicates(self, f: Finding) -> str:
        values = ", ".join(f"'{v}'" for v in f.info["values"])
        return (
            f"Column '{f.column}' looks like an ID column, so each value "
            f"should appear once, but {values} repeat in rows "
            f"{_row_list(f.rows)}. Joins on this column will multiply "
            f"rows, and lookups will return more than one record."
        )

    def _explain_generic(self, f: Finding) -> str:
        where = f" in column '{f.column}'" if f.column else ""
        rows = f" Rows affected: {_row_list(f.rows)}." if f.rows else ""
        return f"Check '{f.check}' found a problem{where}.{rows}"


class LLMExplainer:
    """Plug-in point for an LLM-backed explainer. Not wired up.

    Give it a client with a .complete(prompt) -> str method (any provider)
    and it will ask the model to rewrite the rule-based explanation. With
    no client it returns the rule-based text unchanged, so the app never
    breaks just because no API key is configured.
    """

    def __init__(self, client=None):
        self.client = client
        self._fallback = RuleBasedExplainer()

    def explain(self, finding: Finding) -> str:
        base = self._fallback.explain(finding)
        if self.client is None:
            return base
        prompt = (
            "Rewrite this data quality finding in plain English for a "
            "non-technical reader. Keep every row number and value "
            f"exactly as written.\n\n{base}"
        )
        return self.client.complete(prompt)


def get_explainer(kind: str = "rule") -> RuleBasedExplainer | LLMExplainer:
    if kind == "llm":
        return LLMExplainer()
    return RuleBasedExplainer()
