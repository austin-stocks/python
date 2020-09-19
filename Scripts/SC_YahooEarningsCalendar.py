# ##############################################################################
# Download the historical data into individual csv
# ##############################################################################

import csv
import datetime as dt
import openpyxl
import os
import xlrd
from yahoo_earnings_calendar import YahooEarningsCalendar
import logging
import sys
import pandas as pd
# ##############################################################################


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
                    filename=dir_path + log_dir + "\\" + 'SC_YahooEarningsCalendar_debug.txt',
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
master_tracklist_file = "Master_Tracklist.xlsx"
master_tracklist_df = pd.read_excel(dir_path + user_dir + "\\" + master_tracklist_file, sheet_name="Main")
master_tracklist_df.sort_values('Tickers', inplace=True)
ticker_list_unclean = master_tracklist_df['Tickers'].tolist()
ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']
master_tracklist_df.set_index('Tickers', inplace=True)
# -----------------------------------------------------------------------------

yec = YahooEarningsCalendar()
yahoo_earnings_calendar_df = pd.DataFrame(columns=['Ticker','Earnings_Date'])
yahoo_earnings_calendar_df.set_index('Ticker', inplace=True)

i_int = 0
# ticker_list = ["AMT", "JAZZ", "PLNT", "LGIH", "STWD", "RHP", "IIPR", 'USPH', 'EME', 'CBRE']
for ticker_raw in ticker_list:
  ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase
  i_int += 1
  # logging.info("\nIteration : " + str(i_int) + " Processing : " + str(ticker))
  print("\nIteration : " + str(i_int) + " Processing : " + str(ticker))

  quality_of_stock = master_tracklist_df.loc[ticker, 'Quality_of_Stock']
  if ((quality_of_stock != 'Wheat') and (quality_of_stock != 'Wheat_Chaff') and (quality_of_stock != 'Essential') and (quality_of_stock != 'Sundeep_List')):
    # logging.info (str(ticker) +  " is not Wheat or Essential...skipping")
    print (str(ticker) +  " is not Wheat or Essential...skipping")
    continue

  # Returns the next earnings date of BOX in Unix timestamp
  try:
    unixtimestamp = yec.get_next_earnings_date(ticker)
  except:
    # logging.info ("Could not download Earnings date for " + str(ticker))
    print ("Could not download Earnings date for " + str(ticker))
    yahoo_earnings_calendar_df.loc[ticker] = '#NA#'
    continue
  # logging.info("The returned timestamp is : " + str(unixtimestamp))
  print("The returned timestamp is : " + str(unixtimestamp))

  # ticker_next_earnings_date_str = dt.datetime.fromtimestamp(unixtimestamp).strftime('%m/%d/%Y')
  # ticker_next_earnings_date_dt = dt.datetime.strptime(ticker_next_earnings_date_str, '%m/%d/%Y').date()
  ticker_next_earnings_date_dt_tmp = dt.datetime.fromtimestamp(unixtimestamp)
  print ("The converted unixtimestamp to datetime is " + str(ticker_next_earnings_date_dt_tmp))
  ticker_next_earnings_date_dt = dt.datetime.fromtimestamp(unixtimestamp).date() + dt.timedelta(days=1)
  ticker_next_earnings_date_str = dt.datetime.strftime(ticker_next_earnings_date_dt, '%m/%d/%Y')
  yahoo_earnings_calendar_df.loc[ticker] = [ticker_next_earnings_date_str]
  if (ticker_next_earnings_date_dt < dt.date.today() ):
    # logging.debug ("The earnings data for " + str(ticker) +  " is " + str(ticker_next_earnings_date_str) +  " and is older than today's date...")
    print ("The earnings data for " + str(ticker) +  " is " + str(ticker_next_earnings_date_str) +  " and is older than today's date...")
  else:
    # logging.debug ("Next earnings date for " + str(ticker) + " is " + str(ticker_next_earnings_date_str))
    print ("Next earnings date for " + str(ticker) + " is " + str(ticker_next_earnings_date_str))

  # if (i_int == 10):
  #   break

now = dt.datetime.now()
date_time = now.strftime("%Y_%m_%d")
yahoo_earnings_calendar_logfile = "yahoo_earnings_calendar_" + date_time  + ".csv"
yahoo_earnings_calendar_df.sort_values(by=['Earnings_Date','Ticker'], ascending=[True,True]).to_csv(dir_path + log_dir + "\\" + yahoo_earnings_calendar_logfile,sep=',', index=True, header=True)
# logging.debug("Done")



# -----------------------------------------------------------------------------
# This works - maybe use it later
# -----------------------------------------------------------------------------
'''
date_from = datetime.datetime.strptime(
    'Jan 31 2020  10:00AM', '%b %d %Y %I:%M%p')
date_to = datetime.datetime.strptime(
    'Feb 8 2020  1:00PM', '%b %d %Y %I:%M%p')
logging.debug(yec.earnings_between(date_from, date_to))
[
{'ticker': 'PSX', 'companyshortname': 'Phillips 66', 'startdatetime': '2020-01-31T18:30:00.000Z', 'startdatetimetype': 'BMO', 'epsestimate': 1.56, 'epsactual': None, 'epssurprisepct': None, 'gmtOffsetMilliSeconds': 0, 'quoteType': 'EQUITY'}, 
{'ticker': 'PSXP', 'companyshortname': 'Phillips 66 Partners LP', 'startdatetime': '2020-01-31T18:30:00.000Z', 'startdatetimetype': 'BMO', 'epsestimate': 0.96, 'epsactual': None, 'epssurprisepct': None, 'gmtOffsetMilliSeconds': 0, 'quoteType': 'EQUITY'}, 
]
'''

# ##############################################################################



