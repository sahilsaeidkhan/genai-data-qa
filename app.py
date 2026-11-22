"""Data QA Demo: upload a CSV, get every data problem explained in plain
English, with the exact rows to fix.

Run:  streamlit run app.py
"""

from pathlib import Path

import pandas as pd
import streamlit as st

from checks import flagged_rows, load_csv, run_all_checks
from explain import get_explainer
from report import build_html_report, build_markdown_report

HERE = Path(__file__).parent
SAMPLES = {
    "Messy sample (defects planted on purpose)": HERE / "sample_messy.csv",
    "Clean sample (should pass everything)": HERE / "sample_clean.csv",
}

st.set_page_config(page_title="Data QA Demo", page_icon="🧹", layout="wide")

st.title("🧹 Data QA Demo")
st.write(
    "Upload a CSV and this tool runs the checks that data teams usually "
    "do by hand: missing values, duplicates, outliers, numbers stored as "
    "text, mixed date formats, dead columns and repeated IDs. Every "
    "problem is explained in plain English with the exact rows to look "
    "at. The idea is the one behind every good QA summarizer: turn hours "
    "of eyeballing spreadsheets into a short list of things to fix."
)

with st.sidebar:
    st.header("Your file")
    uploaded = st.file_uploader("Upload a CSV", type=["csv"])
    st.write("...or try a sample:")
    sample_choice = st.radio("Sample data", list(SAMPLES),
                             label_visibility="collapsed")
    st.caption(
        "Row numbers in the results are 1-based data rows: row 1 is the "
        "first row under the header."
    )

if uploaded is not None:
    source_name = uploaded.name
    df = load_csv(uploaded)
else:
    source_name = SAMPLES[sample_choice].name
    df = load_csv(SAMPLES[sample_choice])

results, elapsed = run_all_checks(df)
explainer = get_explainer()
n_passed = sum(1 for r in results if r.passed)
bad_rows = flagged_rows(results)

st.subheader(f"Results for {source_name}")
st.success(
    f"✅ Checked {len(df):,} rows × {len(df.columns)} columns "
    f"in {elapsed:.2f} seconds."
)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Rows", f"{len(df):,}")
col2.metric("Columns", len(df.columns))
col3.metric("Checks passed", f"{n_passed} / {len(results)}")
col4.metric("Checks failed", len(results) - n_passed)
col5.metric("Rows flagged", len(bad_rows))

st.divider()

for result in results:
    if result.passed:
        st.markdown(f"### ✅ {result.title}")
        st.write("No problems found.")
        continue
    st.markdown(f"### ❌ {result.title}")
    for finding in result.findings:
        st.markdown(f"- {explainer.explain(finding)}")
        if finding.rows:
            with st.expander(f"See the flagged rows ({len(finding.rows)})"):
                st.dataframe(df.iloc[[r - 1 for r in finding.rows]])

st.divider()
st.subheader("Take the report with you")
md_report = build_markdown_report(results, source_name, len(df),
                                  len(df.columns), elapsed)
html_report = build_html_report(results, source_name, len(df),
                                len(df.columns), elapsed)
dl1, dl2 = st.columns(2)
dl1.download_button("⬇️ Download QA report (Markdown)", md_report,
                    file_name="qa_summary.md", mime="text/markdown")
dl2.download_button("⬇️ Download QA report (HTML)", html_report,
                    file_name="qa_summary.html", mime="text/html")

if bad_rows:
    st.caption(
        "Rows flagged for review: " + ", ".join(str(r) for r in bad_rows))

st.caption(
    "Explanations are written by rule-based templates, so the tool needs "
    "no API key. An LLM explainer can be plugged in later; see "
    "explain.py and the README."
)
