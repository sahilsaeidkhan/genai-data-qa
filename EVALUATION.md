# Evaluation

Tested on 22 Nov 2026 with the automated suite in `test_checks.py`
(14 tests, all passing) plus a Streamlit AppTest run of the app itself
and a headless `streamlit run` boot check (health endpoint OK, HTTP 200).

## Planted defects vs caught

`sample_messy.csv` (30 rows) has 14 defects planted on purpose. All 14
were caught, with the right row numbers:

| # | Planted defect | Caught as | Rows reported |
|---|---|---|---|
| 1 | age blank, rows 4 and 17 | Missing values | 4, 17 |
| 2 | email blank, row 9 | Missing values | 9 |
| 3 | amount blank, row 22 | Missing values | 22 |
| 4 | row 12 is an exact copy of row 5 | Exact duplicates | 5, 12 |
| 5 | row 20 is an exact copy of row 8 | Exact duplicates | 8, 20 |
| 6 | row 15 repeats row 3 with different case/spaces | Near duplicates | 3, 15 |
| 7 | amount 99999, row 18 | Outlier (IQR) | 18 |
| 8 | age 150, row 27 | Outlier (IQR) | 27 |
| 9 | amount "1,200" as text, row 7 | Numbers stored as text | 7 |
| 10 | amount with a ₹ symbol, row 19 | Numbers stored as text | 19 |
| 11 | age written as "twenty", row 11 | Non-numeric in numeric column | 11 |
| 12 | dates in 3 formats (ISO, 05/01/2026, 05 Jan 2026) | Mixed date formats | rows 6, 21 in DD/MM/YYYY; row 14 in "24 Jan 2026"; 27 in ISO |
| 13 | country is "India" in all 30 rows | Constant column | country |
| 14 | coupon_code empty in all 30 rows | Empty column | coupon_code |

The repeated order_ids caused by defects 4, 5 and 6 were also reported
by the ID check (order_id values 1003, 1005, 1008; rows 3, 5, 8, 12,
15, 20).

Result on the messy file: 0 of 8 check groups passed, 14 findings,
0.04 seconds for 30 rows.

## Clean file

`sample_clean.csv` (20 rows, same schema, nothing planted) passed all
8 check groups with zero findings and zero flagged rows. No false
positives on the clean data.

## Scale check

A generated 50,000 row file: loading took 0.06 s, the checks took
11.8 s. Two findings there were correct behaviour, not bugs: the IQR
rule flagged the natural tails of a normal distribution (about 0.7% of
rows, which is what the rule does by design), and a constant
signup_date column was correctly reported. The tool is aimed at the
small-to-medium files a person would QA by hand; it is not built for
million-row data.

## Known limitations, honestly

- The mixed date format finding lists every row of the column, so the
  "rows flagged" counter counts all 30 rows of the messy file even
  though only 3 rows use a non-ISO format. The explanation text itself
  names the exact rows per format.
- Date parsing tries day-first formats (05/01/2026 = 5 January). A file
  written month-first would be misread. There is no way to tell the two
  apart from the values alone when both are plausible.
- A column counts as "numeric" or "date-like" when at least 70% of its
  values parse that way. A column that is half numbers, half words is
  reported as neither and gets no type finding.
- Near-duplicate detection only normalises case and whitespace. It will
  not catch typos ("Delhi" vs "Dehli") or reordered names.
- Outliers use the plain IQR rule with no domain sense. An age of 150
  and a genuinely large order look the same to it; a human still has to
  judge the flagged rows.
- Explanations are rule-based templates, not an LLM. They are accurate
  but they read like templates, because they are. `explain.py` has the
  plug-in point for a model-backed explainer.
- The CSV is read as raw text on purpose, so quoted fields, odd
  encodings or a broken header row can produce confusing results
  instead of a clean error.
