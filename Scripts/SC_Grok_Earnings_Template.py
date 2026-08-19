# ##############################################################################
# Build a Grok earnings template from the SEC diluted-EPS file and the CNBC
# quarterly file for each ticker in Tracklist.csv (Tickers column).
# First cut: columns A-E only.
#
#   A  CNBC_Matches_Reported_EPS   left empty
#   B  Q_Report_Date               CNBC AnnouncedDate (reported rows only)
#   C  Q_Date                      month-end of the quarter (never the raw SEC
#                                  period-end Saturday, e.g. 6/27/2026 -> 6/30/2026)
#   D  Q_EPS_Diluted               SEC EPS_GAAP
#   E  Q_EPS_Adjusted              CNBC actual (reported) or estimate (projected)
#   F  Q_EPS_Projections_Date_0    today, first data row only
#   G  Q_EPS_Projections_1         same values as E (Q_EPS_Adjusted)
#   H  Q_EPS_Projections_Date_1    yesterday, first data row only
#
# Output: Grok_Work/Grok_Earnings_Templates/<Ticker>_earnings_grok.csv
#
# Year/Quarter labels do not always match. CNBC 2026 Q3 for Apple is the June
# quarter; SEC labels that same stretch 2026 Q2. Rows are paired by period-end
# month. Each ticker's CNBC Q1-Q4 -> Mar/Jun/Sep/Dec map is inferred from
# reported announce dates vs SEC filed dates (falls back to calendar quarters).
# ##############################################################################

import calendar
import csv
import logging
import os
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
log_dir = "\\..\\" + "Logs"
tracklist_file = "Tracklist.csv"
tracklist_file_full_path = dir_path + user_dir + "\\" + tracklist_file

sec_dir = Path(dir_path) / ".." / "SEC_Earnings"
cnbc_dir = Path(dir_path) / ".." / "CNBC_Earnings"
out_dir = Path(dir_path) / ".." / "Grok_Work" / "Grok_Earnings_Templates"

os.makedirs(dir_path + log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(dir_path + log_dir + "\\SC_Grok_Earnings_Template_debug.txt", mode="w"),
        logging.StreamHandler(),
    ],
)

HEADERS = [
    "CNBC_Matches_Reported_EPS",
    "Q_Report_Date",
    "Q_Date",
    "Q_EPS_Diluted",
    "Q_EPS_Adjusted",
    "Q_EPS_Projections_Date_0",
    "Q_EPS_Projections_1",
    "Q_EPS_Projections_Date_1",
]


def parse_iso(value):
    if not value:
        return None
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()


def fmt_date(d):
    if d is None:
        return ""
    return f"{d.month}/{d.day}/{d.year}"


def fmt_num(value):
    if value is None or value == "":
        return ""
    return value


def period_bucket(d):
    """Map a period-end date to (year, month) of Mar/Jun/Sep/Dec."""
    y, m, day = d.year, d.month, d.day
    if day <= 7 and m in (1, 4, 7, 10):
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    if m <= 3:
        return (y, 3)
    if m <= 6:
        return (y, 6)
    if m <= 9:
        return (y, 9)
    return (y, 12)


def quarter_end(year, month):
    return date(year, month, calendar.monthrange(year, month)[1])


def load_sec_rows(ticker):
    path = sec_dir / f"{ticker}_sec_eps_quarterly.csv"
    if not path.exists():
        return None
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_cnbc_rows(ticker):
    path = cnbc_dir / f"{ticker}_cnbc_earnings_quarterly.csv"
    if not path.exists():
        return None
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def sec_by_bucket(sec_rows):
    by_bucket = {}
    for r in sec_rows:
        end = parse_iso(r.get("PeriodEnd"))
        if end is None:
            continue
        bucket = period_bucket(end)
        existing = by_bucket.get(bucket)
        prefer_new = False
        if existing is None:
            prefer_new = True
        else:
            old_computed = str(existing.get("Source", "")).startswith("Computed")
            new_computed = str(r.get("Source", "")).startswith("Computed")
            if old_computed and not new_computed:
                prefer_new = True
            elif old_computed == new_computed and end > parse_iso(existing["PeriodEnd"]):
                prefer_new = True
        if prefer_new:
            by_bucket[bucket] = r
    return by_bucket


def infer_cnbc_quarter_months(sec_rows, cnbc_rows):
    """Return {1:12, 2:3, 3:6, 4:9} style map from CNBC qtr -> period-end month.

    Built by pairing CNBC announced dates with nearby SEC filed dates.
    Falls back to calendar quarters (Q1=Mar ... Q4=Dec) if inference is thin.
    """
    sec_filed = []
    for r in sec_rows:
        filed = parse_iso(r.get("Filed"))
        end = parse_iso(r.get("PeriodEnd"))
        if filed and end:
            sec_filed.append((filed, period_bucket(end)[1]))

    votes = {1: Counter(), 2: Counter(), 3: Counter(), 4: Counter()}
    for r in cnbc_rows:
        if r.get("Type") != "Reported" or not r.get("AnnouncedDate") or not r.get("Quarter"):
            continue
        announced = parse_iso(r["AnnouncedDate"])
        try:
            q = int(r["Quarter"])
        except (TypeError, ValueError):
            continue
        if announced is None or q not in votes:
            continue
        best = None
        best_days = 21
        for filed, month in sec_filed:
            days = abs((announced - filed).days)
            if days < best_days:
                best_days = days
                best = month
        if best is not None:
            votes[q][best] += 1

    inferred = {}
    for q, counter in votes.items():
        if counter:
            inferred[q] = counter.most_common(1)[0][0]
    calendar_map = {1: 3, 2: 6, 3: 9, 4: 12}
    if len(inferred) < 3:
        logging.info("  CNBC quarter map: calendar fallback %s", calendar_map)
        return calendar_map
    for q, month in calendar_map.items():
        inferred.setdefault(q, month)
    logging.info("  CNBC quarter map: %s", inferred)
    return inferred


def cnbc_bucket(fiscal_year, quarter, q_to_month):
    fy = int(fiscal_year)
    q = int(quarter)
    month = q_to_month[q]
    year = fy
    # If this fiscal quarter's period ends in a calendar month after the
    # fiscal year-end month would wrap... For Sep-FY, Q1 ends Dec of fy-1.
    # Detect wrap: if Q1's month is 12, year is fy-1. More generally, if
    # the month is later in the calendar than the FY-end month implied by Q4.
    fy_end_month = q_to_month.get(4, 12)
    if month > fy_end_month:
        year = fy - 1
    return (year, month)


def cnbc_by_bucket(cnbc_rows, q_to_month):
    by_bucket = {}
    for r in cnbc_rows:
        if not r.get("FiscalYear") or not r.get("Quarter"):
            continue
        try:
            bucket = cnbc_bucket(r["FiscalYear"], r["Quarter"], q_to_month)
        except (TypeError, ValueError, KeyError):
            continue
        by_bucket[bucket] = r
    return by_bucket


def build_rows(ticker, sec_rows, cnbc_rows):
    q_to_month = infer_cnbc_quarter_months(sec_rows, cnbc_rows)
    sec = sec_by_bucket(sec_rows)
    cnbc = cnbc_by_bucket(cnbc_rows, q_to_month)
    buckets = sorted(set(sec) | set(cnbc), reverse=True)
    today = fmt_date(date.today())
    yesterday = fmt_date(date.today() - timedelta(days=1))
    out = []
    for i, bucket in enumerate(buckets):
        s = sec.get(bucket)
        c = cnbc.get(bucket)
        report_date = ""
        q_date = quarter_end(*bucket)
        diluted = ""
        adjusted = ""
        if s:
            diluted = s.get("EPS_GAAP", "")
        if c:
            if c.get("Type") == "Reported" and c.get("AnnouncedDate"):
                report_date = fmt_date(parse_iso(c["AnnouncedDate"]))
            if c.get("Type") == "Reported" and c.get("EPS_Actual") not in (None, ""):
                adjusted = c.get("EPS_Actual")
            elif c.get("EPS_Estimate") not in (None, ""):
                adjusted = c.get("EPS_Estimate")
        first_row = i == 0
        out.append({
            "CNBC_Matches_Reported_EPS": "",
            "Q_Report_Date": report_date,
            "Q_Date": fmt_date(q_date),
            "Q_EPS_Diluted": fmt_num(diluted),
            "Q_EPS_Adjusted": fmt_num(adjusted),
            "Q_EPS_Projections_Date_0": today if first_row else "",
            "Q_EPS_Projections_1": fmt_num(adjusted),
            "Q_EPS_Projections_Date_1": yesterday if first_row else "",
        })
    return out


def write_template(ticker, rows):
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{ticker}_earnings_grok.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)
    return out_path


def load_tickers():
    if not os.path.exists(tracklist_file_full_path):
        logging.error("Tracklist not found: %s", tracklist_file_full_path)
        sys.exit(1)
    tracklist_df = pd.read_csv(tracklist_file_full_path)
    if "Tickers" not in tracklist_df.columns:
        logging.error("Tracklist.csv does not have a Tickers column")
        sys.exit(1)
    tickers = []
    for ticker_raw in tracklist_df["Tickers"].tolist():
        if str(ticker_raw) == "nan":
            continue
        ticker = str(ticker_raw).replace(" ", "").upper()
        if ticker:
            tickers.append(ticker)
    return tickers


def main():
    tickers = load_tickers()
    if not tickers:
        logging.error(
            "The Tickers column in Tracklist.csv is empty. "
            "Put the tickers you want (one per row) in that column and rerun."
        )
        sys.exit(1)

    logging.info("Loaded %s ticker(s) from Tracklist.csv: %s", len(tickers), ", ".join(tickers))
    failures = []
    for ticker in tickers:
        logging.info("Processing %s", ticker)
        sec_rows = load_sec_rows(ticker)
        cnbc_rows = load_cnbc_rows(ticker)
        if sec_rows is None:
            logging.error("  missing %s", sec_dir / f"{ticker}_sec_eps_quarterly.csv")
            failures.append(ticker)
            continue
        if cnbc_rows is None:
            logging.error("  missing %s", cnbc_dir / f"{ticker}_cnbc_earnings_quarterly.csv")
            failures.append(ticker)
            continue
        rows = build_rows(ticker, sec_rows, cnbc_rows)
        out_path = write_template(ticker, rows)
        logging.info("  wrote %s rows -> %s", len(rows), out_path)

    if failures:
        logging.error("Finished with failures: %s", ", ".join(failures))
        sys.exit(1)
    logging.info("All requested earnings templates written")


if __name__ == "__main__":
    main()
