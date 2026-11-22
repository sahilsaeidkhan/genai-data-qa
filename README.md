# Data QA Demo

Upload a CSV, get back a short list of everything wrong with
it, written in plain English, with the exact rows to fix.

Data QA on a fresh file usually means opening it in a
spreadsheet and scrolling: looking for blanks, spotting the
row that got pasted twice, wondering why the totals feel off.
This tool does that first pass automatically. It runs eight
groups of checks, times itself, and turns the results into a
summary you can hand to someone.

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app opens with a messy sample file loaded, so it works
the moment it starts. There is also a clean sample to compare
against, and you can upload your own CSV from the sidebar.

## Does it actually catch things?

The messy sample (`sample_messy.csv`, 30 rows) has 14 defects
planted on purpose: blank cells, two exact duplicate rows, a
near-duplicate hiding behind different capitalisation, an
amount of 99999, an age of 150, numbers stored as text
(`1,200`, `₹850`), the word "twenty" in the age column, dates
in three different formats, a column that is "India" all the
way down, and a column that is completely empty.

All 14 are caught, with the right row numbers, and the clean
sample passes every check with no false alarms. The test
suite that proves it:

```bash
python -m pytest test_checks.py
```

14 tests, all passing as of 22 Nov 2026. The planted-vs-caught
table is in `EVALUATION.md`.

## What it checks

The check set is borrowed from the tools data teams actually
use, mainly Great Expectations and Pandera, trimmed to what
makes sense for one file at a time:

- **Missing values** per column, with row numbers (the GE
  not-null expectation, Pandera's `nullable=False`)
- **Exact duplicate rows**
- **Near-duplicate rows**: same record modulo capitalisation
  and extra spaces, which exact matching misses
- **Numeric outliers** using the IQR rule
- **Type problems**: numbers stored as text (`1,200`, `₹850`),
  words sitting in a numeric column (`twenty` in an age
  column), and columns that mix several date formats
- **Constant columns** that carry no information
- **Empty columns**
- **Repeated values in ID columns** (GE's unique expectation,
  Pandera's `unique=True`)

Like Pandera's lazy validation, the checks collect every
failure with its row numbers instead of stopping at the first
problem. Row numbers are 1-based data rows: row 1 is the
first row under the header.

The app shows a small dashboard (rows, columns, checks passed
and failed, rows flagged), prints how long the run took, and
exports the summary as Markdown or HTML.

## The explanations

Every finding gets a plain-English explanation that names the
column, says how much data is affected and quotes the rows.
These are written by rule-based templates in `explain.py`, so
the tool needs no API key and works offline.

If you want a model to write them instead, `explain.py` is
built for that: implement the one-method explainer interface
(or pass a client with a `.complete(prompt)` method to
`LLMExplainer`) and nothing else changes. The checks only
produce findings; who words them is a separate decision.

## Files

- `app.py` — the Streamlit app
- `checks.py` — the check engine (no Streamlit in it, so it is easy to test and reuse)
- `explain.py` — rule-based explanations, plus the LLM plug-in point
- `report.py` — Markdown and HTML report builders
- `sample_messy.csv` — orders data with defects planted on purpose
- `sample_clean.csv` — the same kind of data with nothing wrong
- `make_samples.py` — regenerates both samples
- `test_checks.py` — tests proving every planted defect is caught with the right rows, and the clean file passes
- `EVALUATION.md` — what was tested, the real results, and the limits

## Limitations

Honest list, also in EVALUATION.md: dates are read day-first,
so a month-first file would be misread; near-duplicates only
cover case and spacing, not typos; the outlier rule has no
domain sense and flags about 0.7% of perfectly normal data by
design; a 50,000 row file takes about 12 seconds, so this is
a tool for files a person would otherwise check by hand, not
for pipeline-scale data.
