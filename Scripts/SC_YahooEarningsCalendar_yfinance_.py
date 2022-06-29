
import yfinance as yf
import os
import sys
import logging
import pandas as pd


dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
log_dir = "\\..\\" + "Logs"

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

# Disnable and enable global level logging
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

print(yf.__version__)
i_itr = 1
# ticker_list = ['aaon', 'asml', 'mu', 'nflx']
for ticker in ticker_list :

  ticker = ticker.replace(" ", "").upper()  # Remove all spaces from ticker_raw and convert to uppercase
  ticker_yf = yf.Ticker(ticker)
  logging.debug("Iteration : " + str(i_itr) + ", Ticker : " + str(ticker) + ", Earnings Calendar : " + str(ticker_yf.calendar))
  if ticker_yf.calendar.empty :
    logging.info("Iteration : " + str(i_itr) + ", Ticker : " + str(ticker) + ", Earnings Calendar Dataframe returned empty...Skipping this ticker")
    i_itr = i_itr + 1
    continue

  # Get the Earnings Date in a list. It may have multiple entries.
  # Get entry 0 as that is the earlier one
  earnings_date_list = ticker_yf.calendar.loc['Earnings Date']
  logging.debug("The earnnigs date list is : " + str(len(earnings_date_list)))
  earnings_date = earnings_date_list[0]
  logging.debug("The earnings date datetime is " + str(earnings_date))
  earnings_date_dt = earnings_date.date()
  logging.debug("The earnings date dt is " + str(earnings_date_dt))
  logging.info("Iteration : " + str(i_itr) + ", Ticker : " + str(ticker) + ", Earnings Date : " + str(earnings_date_dt))
  yahoo_earnings_calendar_df.loc[ticker] = [earnings_date_dt]

  i_itr = i_itr+1
  logging.debug("")
  logging.debug("")
  #  --------------------------------------------------------------------------

# Now Print it in the csv file
# now = dt.datetime.now()
# date_time = now.strftime("%Y_%m_%d")
# yahoo_earnings_calendar_logfile = "yahoo_earnings_calendar_" + date_time + ".csv"
yahoo_earnings_calendar_logfile = "yahoo_earnings_calendar_yfinance.csv"
yahoo_earnings_calendar_df.sort_values(by=['Earnings_Date','Ticker'], ascending=[True,True]).to_csv(dir_path + log_dir + "\\" + yahoo_earnings_calendar_logfile,sep=',', index=True, header=True)
