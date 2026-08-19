# ##############################################################################
# Download SEC XBRL GAAP diluted EPS (quarterly) for each ticker in
# Tracklist.csv. For each ticker, writes a separate CSV.
#
# NOTE: Adjusted / non-GAAP EPS is NOT a standard XBRL concept and is not
# reliably available as structured SEC data. For adjusted EPS use the CNBC
# scraper output (epsAdjActualValue) - see SC_CNBC_Earnings_Quarterly.py.
#
# Data source: SEC EDGAR XBRL company-concept API
#   ticker->CIK map:  https://www.sec.gov/files/company_tickers.json
#   EPS facts:        https://data.sec.gov/api/xbrl/companyconcept/CIK{cik:010d}
#                       /us-gaap/EarningsPerShareDiluted.json
#
# SEC Fair Access requires a User-Agent identifying the requester. Rate limit
# is 10 req/s; we sleep briefly between requests.
# ##############################################################################

import csv
import json
import logging
import os
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

# =============================================================================
# SETTINGS
# =============================================================================
USER_AGENT = "Sundeep Chadha sundeep.chadha@gmail.com"
REQUEST_SLEEP_SEC = 0.15
REQUEST_TIMEOUT_SEC = 30

dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
tracklist_file = "Tracklist.csv"
tracklist_file_full_path = dir_path + user_dir + "\\" + tracklist_file

sec_out_dir = dir_path + "\\..\\SEC_Earnings"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": USER_AGENT,
    "Accept-Encoding": "gzip, deflate",
    "Host": None,
})

# =============================================================================
# LOAD TRACKLIST
# =============================================================================
tracklist_df = pd.read_csv(tracklist_file_full_path)
ticker_list_unclean = tracklist_df["Tickers"].tolist()
ticker_list = [x for x in ticker_list_unclean if str(x) != "nan"]

logging.info(f"Loaded {len(ticker_list)} tickers from {tracklist_file_full_path}")

Path(sec_out_dir).mkdir(parents=True, exist_ok=True)


# =============================================================================
# TICKER -> CIK MAP (fetch once, cache in memory)
# =============================================================================
def load_ticker_cik_map():
    url = "https://www.sec.gov/files/company_tickers.json"
    logging.info(f"Fetching ticker->CIK map from {url}")
    resp = SESSION.get(url, timeout=REQUEST_TIMEOUT_SEC)
    resp.raise_for_status()
    raw = resp.json()
    mapping = {}
    for entry in raw.values():
        ticker = str(entry["ticker"]).upper()
        cik = int(entry["cik_str"])
        mapping[ticker] = cik
    logging.info(f"Loaded CIK for {len(mapping)} tickers")
    return mapping


# =============================================================================
# FETCH EPS FACTS FOR ONE CIK
# =============================================================================
EPS_CONCEPTS = [
    ("EarningsPerShareDiluted", "Diluted"),
    ("EarningsPerShareBasic", "Basic"),
]


def fetch_eps_facts(cik):
    """Try Diluted first, then Basic. Returns (facts_json, concept_label)
    for the first available concept, or (None, None) if neither is tagged.

    Some companies (e.g. FOUR - Shift4 - with multi-class share structure)
    only tag Basic in XBRL, not Diluted.
    """
    for concept, label in EPS_CONCEPTS:
        url = (
            f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik:010d}"
            f"/us-gaap/{concept}.json"
        )
        resp = SESSION.get(url, timeout=REQUEST_TIMEOUT_SEC)
        if resp.status_code == 404:
            time.sleep(REQUEST_SLEEP_SEC)
            continue
        resp.raise_for_status()
        return resp.json(), label
    return None, None


# =============================================================================
# FILTER + DEDUPE QUARTERLY FACTS
# =============================================================================
def parse_iso(s):
    return date.fromisoformat(s)


def duration_days(start, end):
    return (parse_iso(end) - parse_iso(start)).days + 1


def is_quarterly_duration(days):
    return 80 <= days <= 100


def is_annual_duration(days):
    return 350 <= days <= 380


def _sort_key(r):
    """Prefer earliest-filed; among ties, prefer non-amendment forms."""
    form = r["Form"] or ""
    is_amendment = form.endswith("/A")
    return (r["_filed_dt"] or date.max, 1 if is_amendment else 0)


def _make_row(ticker, unit_key, e, source, concept_label):
    end_dt = parse_iso(e["end"])
    return {
        "Ticker": ticker,
        "Year": end_dt.year,
        "Quarter": (end_dt.month - 1) // 3 + 1,
        "PeriodStart": e["start"],
        "PeriodEnd": e["end"],
        "EPS_GAAP": e.get("val"),
        "EPS_Concept": concept_label,
        "Source": source,
        "Form": e.get("form"),
        "Filed": e.get("filed"),
        "AccessionNumber": e.get("accn"),
        "Unit": unit_key,
        "_filed_dt": parse_iso(e["filed"]) if e.get("filed") else None,
    }


def _dedupe_by_period_end(rows):
    grouped = {}
    for r in rows:
        key = r["PeriodEnd"]
        existing = grouped.get(key)
        if existing is None or _sort_key(r) < _sort_key(existing):
            grouped[key] = r
    return list(grouped.values())


def extract_quarterly_rows(facts_json, ticker, concept_label):
    """Return quarterly EPS rows with Q4 computed from FY when necessary.

    Many companies don't tag a standalone 3-month Q4 EPS - Q4 is only
    reported inside the annual 10-K's full-year figure. When that's the
    case, we compute Q4 as FY - (Q1 + Q2 + Q3). EPS isn't strictly additive
    across quarters (weighted-average share counts drift), so this is an
    approximation - typically within a cent or two. Rows carry a Source
    column: "XBRL" for directly-tagged facts, "Computed(FY-Q1-Q2-Q3)" for
    derived Q4s.
    """
    if not facts_json:
        return []

    units = facts_json.get("units", {})

    quarterly_raw = []
    annual_raw = []
    for unit_key, entries in units.items():
        for e in entries:
            if not (e.get("start") and e.get("end")):
                continue
            try:
                days = duration_days(e["start"], e["end"])
            except Exception:
                continue
            if is_quarterly_duration(days):
                quarterly_raw.append(
                    _make_row(ticker, unit_key, e, "XBRL", concept_label)
                )
            elif is_annual_duration(days):
                annual_raw.append(
                    _make_row(ticker, unit_key, e, "XBRL", concept_label)
                )

    quarterly = _dedupe_by_period_end(quarterly_raw)
    annual = _dedupe_by_period_end(annual_raw)

    q_by_end = {r["PeriodEnd"]: r for r in quarterly}

    for fy in annual:
        fy_start = parse_iso(fy["PeriodStart"])
        fy_end = parse_iso(fy["PeriodEnd"])
        if fy["EPS_GAAP"] is None:
            continue

        qs_in_fy = [
            r for r in quarterly
            if fy_start <= parse_iso(r["PeriodStart"])
            and parse_iso(r["PeriodEnd"]) <= fy_end
            and r["EPS_GAAP"] is not None
        ]
        if len(qs_in_fy) != 3:
            continue

        qs_in_fy.sort(key=lambda r: r["PeriodEnd"])
        q4_start = parse_iso(qs_in_fy[-1]["PeriodEnd"]) + timedelta(days=1)
        q4_end_iso = fy_end.isoformat()
        if q4_end_iso in q_by_end:
            continue

        q4_val = round(
            fy["EPS_GAAP"] - sum(r["EPS_GAAP"] for r in qs_in_fy),
            4,
        )
        q4_row = {
            "Ticker": ticker,
            "Year": fy_end.year,
            "Quarter": (fy_end.month - 1) // 3 + 1,
            "PeriodStart": q4_start.isoformat(),
            "PeriodEnd": q4_end_iso,
            "EPS_GAAP": q4_val,
            "EPS_Concept": concept_label,
            "Source": "Computed(FY-Q1-Q2-Q3)",
            "Form": fy["Form"],
            "Filed": fy["Filed"],
            "AccessionNumber": fy["AccessionNumber"],
            "Unit": fy["Unit"],
            "_filed_dt": fy["_filed_dt"],
        }
        quarterly.append(q4_row)
        q_by_end[q4_end_iso] = q4_row

    for r in quarterly:
        r.pop("_filed_dt", None)

    quarterly.sort(key=lambda r: r["PeriodEnd"], reverse=True)
    return quarterly


# =============================================================================
# WRITE CSV
# =============================================================================
def write_csv(rows, ticker):
    out_path = Path(sec_out_dir) / f"{ticker}_sec_eps_quarterly.csv"
    fieldnames = [
        "PeriodStart", "PeriodEnd", "EPS_GAAP", "Year", "Quarter",
        "EPS_Concept", "Source", "Form", "Filed",
        "AccessionNumber", "Unit",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    logging.info(f"[{ticker}] wrote {len(rows)} rows -> {out_path}")


# =============================================================================
# MAIN
# =============================================================================
def main():
    ticker_cik = load_ticker_cik_map()

    i = 1
    for ticker_raw in ticker_list:
        ticker = str(ticker_raw).replace(" ", "").upper()
        if not ticker:
            continue

        logging.info(f"Iteration {i:<3} : {ticker}")
        i += 1

        cik = ticker_cik.get(ticker)
        if cik is None:
            logging.warning(f"[{ticker}] not found in SEC ticker->CIK map, skipping")
            continue

        time.sleep(REQUEST_SLEEP_SEC)
        try:
            facts, concept_label = fetch_eps_facts(cik)
        except Exception as e:
            logging.error(f"[{ticker}] fetch failed: {e}")
            continue

        if facts is None:
            logging.warning(f"[{ticker}] CIK{cik:010d} has neither EarningsPerShareDiluted nor EarningsPerShareBasic, skipping")
            continue

        rows = extract_quarterly_rows(facts, ticker, concept_label)
        if not rows:
            logging.warning(f"[{ticker}] no quarterly EPS rows after filtering")
            continue

        earliest = min(r["PeriodEnd"] for r in rows)
        latest = max(r["PeriodEnd"] for r in rows)
        logging.info(f"[{ticker}] CIK={cik:010d} concept={concept_label} rows={len(rows)} span={earliest}..{latest}")

        write_csv(rows, ticker)

    logging.info("All Done...")


if __name__ == "__main__":
    main()
