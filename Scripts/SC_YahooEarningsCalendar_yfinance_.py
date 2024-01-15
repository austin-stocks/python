
import yfinance as yf
import os
import sys
import logging
import pandas as pd


dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
log_dir = "\\..\\..\\..\\Automation_Not_in_Git\\" + "Logs"

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
# Logging Levels
# Level
# CRITICAL
# ERROR
# WARNING
# INFO
# DEBUG
# NOTSET
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename=dir_path + log_dir + "\\" + 'SC_YahooEarningsCalendar_yfinance_debug.txt',
                    filemode='w')
# define a Handler which writes INFO messages or higher to the sys.stderr
console = logging.StreamHandler()
console.setLevel(logging.INFO)
# set a format which is simpler for console use
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
# tell the handler to use this format
console.setFormatter(formatter)
# add the handler to the root logger
logging.getLogger('').addHandler(console)

# Disable and enable global level logging
logging.disable(sys.maxsize)
logging.disable(logging.NOTSET)
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Read the master tracklist file into a dataframe
# -----------------------------------------------------------------------------
master_tracklist_file = "Master_Tracklist.xlsm"
master_tracklist_df = pd.read_excel(dir_path + user_dir + "\\" + master_tracklist_file, sheet_name="Main")
master_tracklist_df.sort_values('Tickers', inplace=True)
ticker_list_unclean = master_tracklist_df['Tickers'].tolist()
ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']
master_tracklist_df.set_index('Tickers', inplace=True)
# -----------------------------------------------------------------------------

# Create a dataframe in which the earnings date will be captured and written
# out in the csv file after the earnings date is collected for all tickers.
yahoo_earnings_calendar_df = pd.DataFrame(columns=['Ticker','Earnings_Date'])
yahoo_earnings_calendar_df.set_index('Ticker', inplace=True)

skipped_ticker_df = pd.DataFrame(columns=['Ticker','Reason'])
skipped_ticker_df.set_index('Ticker', inplace=True)


print("The version of yfinance is : ", yf.__version__)

i_itr = 1
# ticker_list = ['aaon', 'asml', 'mu', 'nflx','tsm']
for ticker in ticker_list :

  ticker = ticker.replace(" ", "").upper()  # Remove all spaces from ticker_raw and convert to uppercase
  ticker_yf = yf.Ticker(ticker)
  logging.debug("Iteration : " + str(i_itr) + ", Ticker : " + str(ticker) + ", Earnings Calendar : " + str(ticker_yf.calendar))

  # ticker_attributes = (
  #   ("major_holders", pd.DataFrame),
  #   ("institutional_holders", pd.DataFrame),
  #   ("mutualfund_holders", pd.DataFrame),
  #   ("insider_transactions", pd.DataFrame),
  #   ("insider_purchases", pd.DataFrame),
  #   ("insider_roster_holders", pd.DataFrame),
  #   ("splits", pd.Series),
  #   ("actions", pd.DataFrame),
  #   ("shares", pd.DataFrame),
  #   ("info", dict),
  #   ("calendar", dict),
  #   ("recommendations", Union[pd.DataFrame, dict]),
  #   ("recommendations_summary", Union[pd.DataFrame, dict]),
  #   ("upgrades_downgrades", Union[pd.DataFrame, dict]),
  #   ("earnings", pd.DataFrame),
  #   ("quarterly_earnings", pd.DataFrame),
  #   ("quarterly_cashflow", pd.DataFrame),
  #   ("cashflow", pd.DataFrame),
  #   ("quarterly_balance_sheet", pd.DataFrame),
  #   ("balance_sheet", pd.DataFrame),
  #   ("quarterly_income_stmt", pd.DataFrame),
  #   ("income_stmt", pd.DataFrame),
  #   ("analyst_price_target", pd.DataFrame),
  #   ("revenue_forecasts", pd.DataFrame),
  #   ("sustainability", pd.DataFrame),
  #   ("options", tuple),
  #   ("news", Any),
  #   ("earnings_trend", pd.DataFrame),
  #   ("earnings_dates", pd.DataFrame),
  #   ("earnings_forecasts", pd.DataFrame),
  # )
  #

  if not ticker_yf.calendar:
    logging.info("Iteration : " + str(i_itr) + ", Ticker : " + str(ticker) + ", Earnings Calendar Dataframe returned empty...Skipping this ticker")
    i_itr = i_itr + 1
    skipped_ticker_df.loc[ticker] = "Earnings_dictionary_is_empty"
    continue

  # Get the Earnings Date in a list.
  # It may have multiple entries. Get entry 0 as that is the earlier one
  # It may not have any entries (ASML, J, STM, TSM) -
  #   In that case skip that ticker and go to the next one
  earnings_date_list = ticker_yf.calendar['Earnings Date']
  if (len(earnings_date_list) == 0):
    logging.info("Iteration : " + str(i_itr) + ", Ticker : " + str(ticker) + ", Earnings Date list is zero length...Skipping this ticker")
    i_itr = i_itr + 1
    skipped_ticker_df.loc[ticker] = "Earnings_list_len_is_zero"
    continue

  logging.debug("The earnings date list is : " + str(len(earnings_date_list)))
  earnings_date = earnings_date_list[0]
  logging.debug("The first entry in earnings date list is " + str(earnings_date) + ", and it is a : " + str(type(earnings_date)))
  # earnings_date_dt = earnings_date.date()
  earnings_date_dt = earnings_date
  logging.debug("The earnings date dt is " + str(earnings_date_dt))
  logging.info("Iteration : " + str(i_itr) + ", Ticker : " + str(ticker) + ", Earnings Date : " + str(earnings_date_dt))
  yahoo_earnings_calendar_df.loc[ticker] = [earnings_date_dt]

  i_itr = i_itr+1
  logging.debug("")
  logging.debug("")
  #  --------------------------------------------------------------------------

if (not skipped_ticker_df.empty):
  logging.info("")
  logging.info("***** NOTE ***** NOTE ***** NOTE ***** NOTE ***** NOTE ***** NOTE ***** NOTE ***** NOTE ***** ")
  logging.info("***** Earnings date for " + str(len(skipped_ticker_df.index)) + " tickers could not be found *****")
  logging.info("***** NOTE ***** NOTE ***** NOTE ***** NOTE ***** NOTE ***** NOTE ***** NOTE ***** NOTE ***** ")
  logging.info(skipped_ticker_df.to_string())

# Now Print it in the csv file
# now = dt.datetime.now()
# date_time = now.strftime("%Y_%m_%d")
# yahoo_earnings_calendar_logfile = "yahoo_earnings_calendar_" + date_time + ".csv"
yahoo_earnings_calendar_logfile = "yahoo_earnings_calendar_yfinance.csv"
yahoo_earnings_calendar_df.sort_values(by=['Earnings_Date','Ticker'], ascending=[True,True]).to_csv(dir_path + log_dir + "\\" + yahoo_earnings_calendar_logfile,sep=',', index=True, header=True)

skipped_ticker_logfile = "skipped_ticker_yahoo_earnings_calendar_yfinance.csv"
skipped_ticker_df.sort_values(by=['Ticker'], ascending=[True]).to_csv(dir_path + log_dir + "\\" + skipped_ticker_logfile,sep=',', index=True, header=True)
