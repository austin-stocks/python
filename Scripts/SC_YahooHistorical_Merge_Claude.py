"""
SC_YahooHistorical_Merge_Claude.py

Concise, faster rewrite of SC_YahooHistorical_Merge.py. Same inputs/outputs:
reads Calendar, Configurations, Tracklist, each ticker's Yahoo historical CSV,
and earnings file; writes <ticker>_historical.csv with future calendar dates
followed by moving-averaged historical rows.

Speedups vs original:
  - Vectorized date parsing (pd.to_datetime) instead of per-row strptime
  - numpy argmin over date ordinals for nearest-date lookup
  - Bulk DataFrame.to_csv (with na_rep='NaN' to match original NaN rendering)
    instead of to_string + whitespace split + comma join
  - pd.concat instead of deprecated DataFrame.append
"""

import calendar
import datetime as dt
import logging
import os
import sys

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths (mirror original layout)
# ---------------------------------------------------------------------------
dir_path = os.getcwd()
user_dir_full            = dir_path + "\\..\\" + "User_Files"
earnings_dir_full        = dir_path + "\\..\\" + "Earnings"
yahoo_hist_in_dir        = dir_path + "\\..\\..\\..\\Automation_Not_in_Git\\YahooHistorical"
yahoo_hist_out_dir       = dir_path + "\\..\\..\\Historical"
log_dir_full             = dir_path + "\\..\\..\\..\\Automation_Not_in_Git\\" + "Logs"

tracklist_file_full_path      = user_dir_full + "\\" + "Tracklist.csv"
calendar_file_full_path       = user_dir_full + "\\" + "Calendar.csv"
configurations_file_full_path = user_dir_full + "\\" + "Configurations.csv"

# ---------------------------------------------------------------------------
# Logging (INFO to console, DEBUG to file)
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
    datefmt="%m-%d %H:%M",
    filename=log_dir_full + "\\" + "SC_YahooHistorical_merge_Claude_debug.txt",
    filemode="w",
)
_console = logging.StreamHandler()
_console.setLevel(logging.INFO)
_console.setFormatter(logging.Formatter("%(name)-12s: %(levelname)-8s %(message)s"))
logging.getLogger("").addHandler(_console)
logging.disable(sys.maxsize)
logging.disable(logging.NOTSET)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DATE_FMT = "%m/%d/%Y"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
# (out_col, source_col, window)
MA_SPECS = [
    ("MA_Price_200_day", "Adj_Close", 200),
    ("MA_Price_50_day",  "Adj_Close",  50),
    ("MA_Price_20_day",  "Adj_Close",  20),
    ("MA_Price_10_day",  "Adj_Close",  10),
    ("MA_Volume_50_day", "Volume",     50),
]
TICKER_RENAMES = {"BRK.B": "BRK-B", "BF.B": "BF-B"}
# Stitch pre-rename Yahoo history for tickers that changed names
tickers_historical_data_to_merge_dict = {
    "RGP":  {"Old_Name": "RECN", "Date_Changed": "04/02/2020"},
    "BFYT": {"Old_Name": "HIIQ", "Date_Changed": "03/05/2020"},
}

# Switch: read Tracklist.csv (0) or SPY_All_Holdings.xlsx (1)
get_sp_holdings = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _nearest_idx(ordinals: np.ndarray, target: dt.date) -> int:
    """Index of the date in `ordinals` closest to `target` (ties -> first)."""
    return int(np.abs(ordinals - target.toordinal()).argmin())


def _normalize_ticker(raw) -> str:
    t = str(raw).replace(" ", "").upper()
    return TICKER_RENAMES.get(t, t)


def _fatal(lines):
    for m in lines:
        logging.error(m)
    sys.exit(1)


def _future_anchor(q_date: dt.date) -> dt.date:
    """Q_Date + 1 quarter, pinned to day=2 (matches original branching)."""
    m, y = q_date.month, q_date.year
    if m <= 8:
        return q_date.replace(day=2, month=m + 4)
    if m <= 11:
        return q_date.replace(day=2, month=m + 4 - 12, year=y + 1)
    return q_date.replace(day=2, month=1, year=y + 1)


def _load_calendar(path):
    df = pd.read_csv(path)
    logging.debug("The years in the Calendar file are : " + str(df.columns.tolist()))
    raw = []
    for col in df.columns:
        vals = df[col].dropna().tolist()
        logging.debug("The date in col" + str(col) + " are " + str(vals))
        raw.extend(vals)
    ts = pd.to_datetime(raw, format=DATE_FMT, errors="raise")
    dates = [t.date() for t in ts]
    ordinals = np.fromiter((d.toordinal() for d in dates), dtype=np.int64, count=len(dates))
    return dates, ordinals


def _load_tickers():
    if get_sp_holdings == 1:
        df = pd.read_excel(user_dir_full + "\\" + "SPY_All_Holdings.xlsx", sheet_name="SPY")
        raw = df["Identifier"].tolist()
    else:
        df = pd.read_csv(tracklist_file_full_path)
        raw = df["Tickers"].tolist()
    return [x for x in raw if str(x) != "nan"]


def _merge_older_history(ticker, df, i_idx):
    meta = tickers_historical_data_to_merge_dict[ticker]
    old = meta["Old_Name"]
    older = pd.read_csv(yahoo_hist_out_dir + "\\" + old + "_historical.csv")

    hist_dates = pd.to_datetime(df["Date"], format=DATE_FMT, errors="raise")
    change_dt = dt.datetime.strptime(meta["Date_Changed"], DATE_FMT).date()
    logging.debug("The date when the ticker name was changed : " + str(change_dt))

    ordinals = hist_dates.dt.date.map(lambda d: d.toordinal()).to_numpy(dtype=np.int64)
    match_i = _nearest_idx(ordinals, change_dt)
    match_d = hist_dates.iloc[match_i].date()

    logging.info("Iteration no : " + str(i_idx) + ", " + str(ticker) + " needs to be merged with " + str(old))
    logging.info("Iteration no : " + str(i_idx) + ", " + "Will use " + str(ticker) + " data(new) till " + str(match_d) + " and then " + str(old) + " data(older) onwards to create the historical data")
    logging.info("Iteration no : " + str(i_idx) + ", " + "Please check the historical file or final chart to make sure that merging happened correctly")
    logging.debug("Matched date " + str(match_d) + " at index " + str(match_i))

    return pd.concat([df.iloc[: match_i + 1], older], ignore_index=True)


def _add_moving_averages(df):
    df = df.copy()
    df.loc[:, "Empty_col_H"] = "-"
    for col, src, win in MA_SPECS:
        df[col] = df.rolling(window=win)[src].mean().shift(-(win - 1))
    return df


def _write_output(out_path, df, future_dates):
    with open(out_path, "w", newline="") as fout:
        fout.write(",".join(df.columns.tolist()) + "\n")
        for d in future_dates:
            fout.write(d.strftime(DATE_FMT) + "\n")
        df.to_csv(fout, header=False, index=False, lineterminator="\n", na_rep="NaN")


# ---------------------------------------------------------------------------
# Load calendar, config, tickers
# ---------------------------------------------------------------------------
calendar_date_list, calendar_ordinals = _load_calendar(calendar_file_full_path)
config_df = pd.read_csv(configurations_file_full_path).set_index("Ticker")
ticker_list = _load_tickers()

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
for i_idx, ticker_raw in enumerate(ticker_list, start=1):
    ticker = _normalize_ticker(ticker_raw)
    logging.debug("Merging Historical Data with Calendar for : " + str(ticker))

    if ticker not in config_df.index:
        _fatal([
            "**********                                  ERROR                              **********",
            "**********     Entry for " + str(ticker).center(10) + " not found in the configurations file     **********",
            "**********     Please create one and then run the script again                 **********",
        ])
    ticker_config_series = config_df.loc[ticker]
    logging.debug("The configurations fields for " + str(ticker) + " \n" + str(ticker_config_series))

    fiscal_year_ends = ticker_config_series["Fiscal_Year"]
    if str(fiscal_year_ends) == "nan":
        fiscal_year_ends = "Dec"
    if fiscal_year_ends not in MONTHS:
        _fatal([
            "**********                                  ERROR                                                                    **********",
            "**********     Fiscal Year specified ==> (" + str(fiscal_year_ends) + ") <== for " + str(ticker).center(10) + " in the configurations file is not a valid month    **********",
            "**********     Please correct the fiscal Year in the configurations file and then run the script again               **********",
        ])

    # -----------------------------------------------------------------------
    # SECTION 1: Yahoo historical + optional name-change stitch
    # -----------------------------------------------------------------------
    historical_df = pd.read_csv(yahoo_hist_in_dir + "\\" + ticker + "_yahoo_historical.csv")
    historical_df.dropna(how="all", inplace=True)
    historical_df = historical_df[pd.notnull(historical_df["Date"])].copy()

    if ticker in tickers_historical_data_to_merge_dict:
        historical_df = _merge_older_history(ticker, historical_df, i_idx)

    historical_df.interpolate(inplace=True)
    historical_df = _add_moving_averages(historical_df)

    hist_dates = pd.to_datetime(historical_df["Date"], format=DATE_FMT, errors="raise")
    latest_hist = hist_dates.iloc[0].date()
    cal_match_date_with_historical_index = _nearest_idx(calendar_ordinals, latest_hist)
    cal_match_date_with_historical = calendar_date_list[cal_match_date_with_historical_index]
    logging.debug("The latest historical date is : " + str(latest_hist) + ". Closest Matching date in Calendar is : " + str(cal_match_date_with_historical) + " at index : " + str(cal_match_date_with_historical_index))

    # -----------------------------------------------------------------------
    # SECTION 2: Earnings file + calculate future calendar slice
    # -----------------------------------------------------------------------
    qtr_eps_df = pd.read_csv(earnings_dir_full + "\\" + ticker + "_earnings.csv")
    q_dates = pd.to_datetime(qtr_eps_df["Q_Date"].dropna(), format=DATE_FMT, errors="raise")
    q_dt = q_dates.iloc[0].date()
    logging.debug("The latest date for which earnings projections are available in the earnings file is : " + str(q_dt))
    logging.debug("The date, month and year from Q Date from earnings file " + str(q_dt.day) + ", " + str(q_dt.month) + ", " + str(q_dt.year))

    if q_dt.day < 25:
        _fatal([
            "Iteration no : " + str(i_idx) + ", " + str(ticker) + " : The day date in latest Q_Date in the earnings file is " + str(q_dt.day) + " (The complete Q_Date in the earnings file is : " + str(q_dt) + ")",
            "Iteration no : " + str(i_idx) + ", " + str(ticker) + " : It is expected that the Q_Date should be b/w 25 and 30/31 (Implying that the Quarters for reporting are aligned towards end of the month date)",
            "Iteration no : " + str(i_idx) + ", " + str(ticker) + " : Please correct in the earnings file and rerun",
        ])
    if calendar.month_abbr[q_dt.month] != fiscal_year_ends:
        _fatal([
            "Iteration no : " + str(i_idx) + ", " + str(ticker) + " : The fiscal year from Configurations file is : " + str(fiscal_year_ends),
            "Iteration no : " + str(i_idx) + ", " + str(ticker) + " : The fiscal year extracted from the Q_Date from earnings file is : " + str(calendar.month_abbr[q_dt.month]) + " (" + str(q_dt) + ")",
            "Iteration no : " + str(i_idx) + ", " + str(ticker) + " : They SHOULD not be different...Please correct and rerun",
        ])

    calendar_future_date = _future_anchor(q_dt)
    logging.debug("Iteration no : " + str(i_idx) + ", " + str(ticker) + " : The calculated future date, from earnings file Q_Date, is : " + str(calendar_future_date))

    calendar_future_date_index = _nearest_idx(calendar_ordinals, calendar_future_date)
    calendar_future_match_date = calendar_date_list[calendar_future_date_index]
    logging.debug("The nearest matching date (for user specified date : " + str(calendar_future_date) + ") in calendar date list is : " + str(calendar_future_match_date) + ", at calendar index : " + str(calendar_future_date_index))
    logging.debug("Will use the Calendar date list from index : " + str(calendar_future_date_index) + " to index : " + str(cal_match_date_with_historical_index))

    calendar_date_list_mod = calendar_date_list[calendar_future_date_index:cal_match_date_with_historical_index]

    logging.info(
        "Iteration : " + f"{str(i_idx) : <3}"
        + ", Ticker : " + f"{str(ticker) : <6}"
        + " : Fiscal Yr end : " + str(fiscal_year_ends)
        + ", Creating Historical Data from : " + f"{str(historical_df['Date'].tolist()[-1]) : <10}"
        + " -> " + f"{str(calendar_date_list_mod[-1]) : <10}"
        + " -> " + f"{str(calendar_date_list_mod[0]) : <10}"
    )
    logging.debug("The modified Calendar list has " + str(len(calendar_date_list_mod)) + " elements")

    # -----------------------------------------------------------------------
    # SECTION 3: Write output CSV
    # -----------------------------------------------------------------------
    _write_output(
        yahoo_hist_out_dir + "\\" + ticker + "_historical.csv",
        historical_df,
        calendar_date_list_mod,
    )

logging.info("All Done")
