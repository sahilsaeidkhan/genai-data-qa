"""Generate the two sample CSVs shipped with the demo.

sample_messy.csv has defects planted on purpose (see PLANTED below and
EVALUATION.md). sample_clean.csv is the same kind of orders data with
nothing wrong with it. Run: python make_samples.py
"""

import csv
from pathlib import Path

HERE = Path(__file__).parent
HEADER = ["order_id", "customer_name", "email", "age", "signup_date",
          "city", "country", "amount", "status", "coupon_code"]

# Row numbers in the comments are 1-based data rows.
MESSY = [
    [1001, "Aarav Mehta", "aarav.mehta@gmail.com", 34, "2026-01-05", "Delhi", "India", "1250.50", "delivered", ""],
    [1002, "Sara Khan", "sara.khan@yahoo.in", 28, "2026-01-07", "Mumbai", "India", "899.00", "shipped", ""],
    [1003, "Priya Sharma", "priya.sharma@gmail.com", 41, "2026-01-09", "Pune", "India", "2340.00", "delivered", ""],   # row 3: near-dupe source
    [1004, "Rohan Verma", "rohan.verma@outlook.com", "", "2026-01-10", "Jaipur", "India", "640.75", "pending", ""],     # row 4: age missing
    [1005, "Neha Gupta", "neha.gupta@gmail.com", 37, "2026-01-12", "Bengaluru", "India", "1780.00", "delivered", ""],  # row 5: exact-dupe source
    [1006, "Vikram Singh", "vikram.singh@gmail.com", 45, "14/01/2026", "Chennai", "India", "520.00", "shipped", ""],   # row 6: DD/MM/YYYY date
    [1007, "Ananya Iyer", "ananya.iyer@gmail.com", 29, "2026-01-15", "Hyderabad", "India", "1,200", "delivered", ""], # row 7: amount as formatted text
    [1008, "Kabir Malhotra", "kabir.m@gmail.com", 52, "2026-01-16", "Delhi", "India", "3100.00", "delivered", ""],    # row 8: exact-dupe source
    [1009, "Meera Nair", "", 33, "2026-01-18", "Kochi", "India", "760.25", "pending", ""],                             # row 9: email missing
    [1010, "Arjun Patel", "arjun.patel@gmail.com", 26, "2026-01-19", "Ahmedabad", "India", "1499.99", "shipped", ""],
    [1011, "Divya Reddy", "divya.reddy@gmail.com", "twenty", "2026-01-21", "Bengaluru", "India", "980.00", "delivered", ""],  # row 11: age as a word
    [1005, "Neha Gupta", "neha.gupta@gmail.com", 37, "2026-01-12", "Bengaluru", "India", "1780.00", "delivered", ""],  # row 12: exact copy of row 5
    [1012, "Farhan Ali", "farhan.ali@gmail.com", 39, "2026-01-23", "Lucknow", "India", "2210.00", "delivered", ""],
    [1013, "Ishita Bose", "ishita.bose@gmail.com", 31, "24 Jan 2026", "Kolkata", "India", "1345.50", "shipped", ""],   # row 14: '24 Jan 2026' date
    [1003, "  priya sharma ", "priya.sharma@gmail.com", 41, "2026-01-09", "pune", "India", "2340.00", "delivered", ""],  # row 15: near copy of row 3
    [1014, "Aditya Rao", "aditya.rao@gmail.com", 48, "2026-01-26", "Mumbai", "India", "665.00", "delivered", ""],
    [1015, "Sneha Kulkarni", "sneha.k@gmail.com", "", "2026-01-27", "Nagpur", "India", "1930.00", "pending", ""],     # row 17: age missing
    [1016, "Manish Tiwari", "manish.tiwari@gmail.com", 44, "2026-01-28", "Indore", "India", "99999.00", "delivered", ""],  # row 18: amount outlier
    [1017, "Ritu Malhotra", "ritu.m@gmail.com", 36, "2026-01-29", "Delhi", "India", "₹850", "shipped", ""],            # row 19: amount with currency symbol
    [1008, "Kabir Malhotra", "kabir.m@gmail.com", 52, "2026-01-16", "Delhi", "India", "3100.00", "delivered", ""],    # row 20: exact copy of row 8
    [1018, "Nikhil Shah", "nikhil.shah@gmail.com", 30, "02/02/2026", "Surat", "India", "1120.00", "delivered", ""],    # row 21: DD/MM/YYYY date
    [1019, "Pooja Desai", "pooja.desai@gmail.com", 27, "2026-02-03", "Vadodara", "India", "", "pending", ""],          # row 22: amount missing
    [1020, "Rahul Yadav", "rahul.yadav@gmail.com", 42, "2026-02-04", "Patna", "India", "1580.00", "delivered", ""],
    [1021, "Kavya Menon", "kavya.menon@gmail.com", 35, "2026-02-05", "Chennai", "India", "2475.00", "shipped", ""],
    [1022, "Sameer Khan", "sameer.khan@gmail.com", 49, "2026-02-06", "Mumbai", "India", "730.00", "delivered", ""],
    [1023, "Anjali Gupta", "anjali.gupta@gmail.com", 24, "2026-02-07", "Delhi", "India", "1690.00", "delivered", ""],
    [1024, "Varun Chopra", "varun.chopra@gmail.com", 150, "2026-02-08", "Amritsar", "India", "540.00", "delivered", ""],  # row 27: age outlier
    [1025, "Shreya Pillai", "shreya.pillai@gmail.com", 32, "2026-02-09", "Bengaluru", "India", "2050.00", "shipped", ""],
    [1026, "Karan Mehta", "karan.mehta@gmail.com", 38, "2026-02-10", "Pune", "India", "910.00", "delivered", ""],
    [1027, "Naina Kapoor", "naina.kapoor@gmail.com", 29, "2026-02-11", "Jaipur", "India", "1330.00", "delivered", ""],
]
# Also planted across the whole messy file: country is "India" in every row
# (constant column) and coupon_code is empty in every row (empty column).

CLEAN = [
    [2001, "Aarav Mehta", "aarav.mehta@gmail.com", 34, "2026-01-05", "Delhi", "India", "1250.50", "delivered", "DIWALI10"],
    [2002, "Sara Khan", "sara.khan@yahoo.in", 28, "2026-01-07", "Mumbai", "India", "899.00", "shipped", "NONE"],
    [2003, "John Mathew", "john.mathew@gmail.com", 45, "2026-01-09", "Dubai", "UAE", "2340.00", "delivered", "FEST20"],
    [2004, "Rohan Verma", "rohan.verma@outlook.com", 31, "2026-01-10", "Jaipur", "India", "640.75", "pending", "NONE"],
    [2005, "Neha Gupta", "neha.gupta@gmail.com", 37, "2026-01-12", "Bengaluru", "India", "1780.00", "delivered", "NEWUSER"],
    [2006, "Vikram Singh", "vikram.singh@gmail.com", 45, "2026-01-14", "Chennai", "India", "520.00", "shipped", "NONE"],
    [2007, "Ananya Iyer", "ananya.iyer@gmail.com", 29, "2026-01-15", "Hyderabad", "India", "1200.00", "delivered", "DIWALI10"],
    [2008, "Kabir Malhotra", "kabir.m@gmail.com", 52, "2026-01-16", "Delhi", "India", "3100.00", "delivered", "NONE"],
    [2009, "Meera Nair", "meera.nair@gmail.com", 33, "2026-01-18", "Kochi", "India", "760.25", "pending", "FEST20"],
    [2010, "Arjun Patel", "arjun.patel@gmail.com", 26, "2026-01-19", "Ahmedabad", "India", "1499.99", "shipped", "NONE"],
    [2011, "Divya Reddy", "divya.reddy@gmail.com", 30, "2026-01-21", "Bengaluru", "India", "980.00", "delivered", "NONE"],
    [2012, "Farhan Ali", "farhan.ali@gmail.com", 39, "2026-01-23", "Lucknow", "India", "2210.00", "delivered", "NEWUSER"],
    [2013, "Ishita Bose", "ishita.bose@gmail.com", 31, "2026-01-24", "Kolkata", "India", "1345.50", "shipped", "NONE"],
    [2014, "Aditya Rao", "aditya.rao@gmail.com", 48, "2026-01-26", "Mumbai", "India", "665.00", "delivered", "NONE"],
    [2015, "Sneha Kulkarni", "sneha.k@gmail.com", 27, "2026-01-27", "Nagpur", "India", "1930.00", "pending", "DIWALI10"],
    [2016, "Manish Tiwari", "manish.tiwari@gmail.com", 44, "2026-01-28", "Indore", "India", "2100.00", "delivered", "NONE"],
    [2017, "Ritu Malhotra", "ritu.m@gmail.com", 36, "2026-01-29", "Delhi", "India", "850.00", "shipped", "NONE"],
    [2018, "Nikhil Shah", "nikhil.shah@gmail.com", 30, "2026-02-02", "Surat", "India", "1120.00", "delivered", "FEST20"],
    [2019, "Pooja Desai", "pooja.desai@gmail.com", 27, "2026-02-03", "Vadodara", "India", "1470.00", "pending", "NONE"],
    [2020, "Rahul Yadav", "rahul.yadav@gmail.com", 42, "2026-02-04", "Patna", "India", "1580.00", "delivered", "NONE"],
]


def _write(name, rows):
    path = HERE / name
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(HEADER)
        writer.writerows(rows)
    print(f"wrote {path} ({len(rows)} rows)")


if __name__ == "__main__":
    _write("sample_messy.csv", MESSY)
    _write("sample_clean.csv", CLEAN)
