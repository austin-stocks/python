# ##############################################################################
# Download the CNBC "Earnings Trends" quarterly data for each ticker in
# Tracklist.csv. For each ticker, writes a separate CSV containing:
#   - dark-blue bars (already-reported quarters with announced date + actual EPS)
#   - light-blue bars (projected quarters with consensus EPS estimate)
#
# Data source: CNBC quotes page (Earnings tab) is powered by a GraphQL call
#   host:        webql-redesign.cnbcfm.com/graphql
#   operation:   earningsForPastAndFuture
#   variables:   {symbol, period: "Quarter", pastYears, futureYears}
# The chart itself only asks for pastYears=4, but the endpoint honors much
# larger values and returns as much history as CNBC has for the ticker
# (typically back to somewhere near the IPO). This script hits the endpoint
# directly with PAST_YEARS below to pull FULL history in a single request per
# ticker - no per-ticker page load required.
#
# If the hardcoded persisted-query hash below ever stops working (CNBC rotated
# the query definition), the script auto-discovers the current hash by opening
# one ticker's earnings page and capturing the outgoing request URL.
# ##############################################################################

import csv
import json
import logging
import os
from pathlib import Path
from urllib.parse import urlparse, parse_qs, quote, unquote

import pandas as pd
from playwright.sync_api import sync_playwright

# =============================================================================
# SETTINGS
# =============================================================================
HEADLESS = True
PAST_YEARS = 40
FUTURE_YEARS = 1

PERSISTED_HASH = "22a58e8ec143cc38b7727ff02fe865fa96f035cef0adb6bcff701c6bf69cd0f0"

dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
tracklist_file = "Tracklist.csv"
tracklist_file_full_path = dir_path + user_dir + "\\" + tracklist_file

cnbc_out_dir = dir_path + "\\..\\CNBC_Earnings"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


# =============================================================================
# LOAD TRACKLIST (same pattern as SC_YahooHistorical_yfinance.py)
# =============================================================================
tracklist_df = pd.read_csv(tracklist_file_full_path)
ticker_list_unclean = tracklist_df["Tickers"].tolist()
ticker_list = [x for x in ticker_list_unclean if str(x) != "nan"]

logging.info(f"Loaded {len(ticker_list)} tickers from {tracklist_file_full_path}")

Path(cnbc_out_dir).mkdir(parents=True, exist_ok=True)


# =============================================================================
# GRAPHQL URL BUILDER
# =============================================================================
def build_graphql_url(ticker, persisted_hash, past_years=PAST_YEARS,
                     future_years=FUTURE_YEARS):
    variables = quote(json.dumps({
        "futureYears": future_years,
        "pastYears": past_years,
        "period": "Quarter",
        "symbol": ticker,
    }))
    extensions = quote(json.dumps({
        "persistedQuery": {"version": 1, "sha256Hash": persisted_hash}
    }))
    return (
        "https://webql-redesign.cnbcfm.com/graphql"
        f"?operationName=earningsForPastAndFuture"
        f"&variables={variables}"
        f"&extensions={extensions}"
    )


# =============================================================================
# AUTO-DISCOVER PERSISTED-QUERY HASH (fallback if hardcoded one goes stale)
# =============================================================================
def discover_persisted_hash(page, ticker):
    logging.info(f"Auto-discovering persisted-query hash via {ticker} page")
    captured = {"hash": None}

    def handle_response(response):
        if captured["hash"] is not None:
            return
        url = response.url
        if "earningsForPastAndFuture" not in url:
            return
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        ext_raw = qs.get("extensions", [""])[0]
        try:
            ext = json.loads(unquote(ext_raw))
            h = ext.get("persistedQuery", {}).get("sha256Hash")
            if h:
                captured["hash"] = h
                logging.info(f"Discovered hash: {h}")
        except Exception:
            pass

    page.on("response", handle_response)
    page.goto(f"https://www.cnbc.com/quotes/{ticker}?tab=earnings",
              wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(8000)
    page.mouse.wheel(0, 1800)
    page.wait_for_timeout(4000)
    page.remove_listener("response", handle_response)
    return captured["hash"]


# =============================================================================
# FETCH ONE TICKER
# =============================================================================
def fetch_ticker(page, ticker, persisted_hash):
    url = build_graphql_url(ticker, persisted_hash)
    resp = page.request.get(url)
    if resp.status != 200:
        raise RuntimeError(f"HTTP {resp.status} for {ticker}")
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(f"GraphQL error for {ticker}: {data['errors']}")
    beans = (
        data.get("data", {})
            .get("getEarningsForPastAndFuture", {})
            .get("earnings", {})
            .get("lstEarningsBean")
    )
    if not beans:
        raise RuntimeError(f"No lstEarningsBean returned for {ticker}")
    return data


# =============================================================================
# TRANSFORM + WRITE CSV
# =============================================================================
def flatten(payload, ticker):
    beans = (
        payload["data"]["getEarningsForPastAndFuture"]["earnings"]
        ["lstEarningsBean"]
    )
    rows = []
    for b in beans:
        announced = b.get("announcedDate")
        actual = b.get("epsAdjActualValue")
        is_reported = actual is not None
        rows.append({
            "Ticker": ticker,
            "FiscalYear": b.get("fiscalYear"),
            "Quarter": b.get("qtrId"),
            "Type": "Reported" if is_reported else "Projected",
            "AnnouncedDate": announced,
            "EPS_Actual": actual,
            "EPS_Estimate": b.get("epsEstimatedValue"),
            "EPS_Estimate_Low": b.get("epsEstimatedLowerValue"),
            "EPS_Estimate_High": b.get("epsEstimatedUpperValue"),
            "Surprise": b.get("surprise"),
            "PerChgEps": b.get("perChgEps"),
            "NetChgEps": b.get("netChgEps"),
        })
    rows.sort(
        key=lambda r: (r["FiscalYear"] or 0, r["Quarter"] or 0),
        reverse=True,
    )
    return rows


def write_csv(rows, ticker):
    out_path = Path(cnbc_out_dir) / f"{ticker}_cnbc_earnings_quarterly.csv"
    fieldnames = [
        "FiscalYear", "Quarter", "EPS_Actual", "Type", "AnnouncedDate",
        "EPS_Estimate", "EPS_Estimate_Low", "EPS_Estimate_High",
        "Surprise", "PerChgEps", "NetChgEps",
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
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context(
            viewport={"width": 1600, "height": 1200},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        logging.info("Warming up CNBC session (single homepage visit)")
        page.goto("https://www.cnbc.com/", wait_until="domcontentloaded",
                  timeout=60000)
        page.wait_for_timeout(2000)

        persisted_hash = PERSISTED_HASH
        i = 1
        for ticker_raw in ticker_list:
            ticker = str(ticker_raw).replace(" ", "").upper()
            if not ticker:
                continue

            logging.info(f"Iteration {i:<3} : {ticker}")
            i += 1

            try:
                payload = fetch_ticker(page, ticker, persisted_hash)
            except Exception as e:
                logging.warning(f"[{ticker}] direct fetch failed: {e}")
                if persisted_hash == PERSISTED_HASH:
                    new_hash = discover_persisted_hash(page, ticker)
                    if new_hash and new_hash != persisted_hash:
                        persisted_hash = new_hash
                        logging.info(f"Retrying {ticker} with discovered hash")
                        try:
                            payload = fetch_ticker(page, ticker, persisted_hash)
                        except Exception as e2:
                            logging.error(f"[{ticker}] retry failed: {e2}")
                            continue
                    else:
                        logging.error(f"[{ticker}] no fresh hash discoverable, skipping")
                        continue
                else:
                    logging.error(f"[{ticker}] skipping")
                    continue

            rows = flatten(payload, ticker)
            reported = sum(1 for r in rows if r["Type"] == "Reported")
            projected = sum(1 for r in rows if r["Type"] == "Projected")

            oldest = next((r["AnnouncedDate"] for r in rows
                           if r["Type"] == "Reported" and r["AnnouncedDate"]),
                          None)
            logging.info(f"[{ticker}] Reported={reported} "
                         f"Projected={projected} Oldest={oldest}")

            write_csv(rows, ticker)

        browser.close()

    logging.info("All Done...")


if __name__ == "__main__":
    main()
