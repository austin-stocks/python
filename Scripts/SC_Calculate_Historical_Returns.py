import pandas as pd
import os
import sys
import time
import datetime as dt
import numpy as np
import logging
import math
import re

# #############################################
# User should only change this
# #############################################
start_date = "12/31/2019"
stop_date = "3/17/2020"
# #############################################

# -----------------------------------------------------------------------------
# Read the master tracklist file into a dataframe
# -----------------------------------------------------------------------------
dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
log_dir = "\\..\\" + "Logs"
historical_dir = "\\..\\" + "Historical"
tracklist_file = "Tracklist.csv"
tracklist_file_full_path = dir_path + user_dir + "\\" + tracklist_file
tracklist_df = pd.read_csv(tracklist_file_full_path)
# -----------------------------------------------------------------------------

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
                    filename=dir_path + log_dir + "\\" + 'SC_Calcuate_Hitorical_Returns_debug.txt',
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

start_date_dt = dt.datetime.strptime(start_date, '%m/%d/%Y').date()
stop_date_dt = dt.datetime.strptime(stop_date, '%m/%d/%Y').date()

logging.debug("The start date : " + str(start_date)  + ", Stop Date : " + str(stop_date))
if (start_date_dt >= stop_date_dt):
  logging.error("The Start Date : " + str(start_date_dt) + " is later (newer) than the Stop Date : " + str(stop_date_dt))
  logging.error("Retruns cannot be calcuated when the start date is greater than the stop date. Please correct and rerun...")
  sys.exit(1)

# -----------------------------------------------------------------------------
# Declare all the dataframes that we are going to need to write into txt file
# and set their columns
# -----------------------------------------------------------------------------
historical_last_updated_df = pd.DataFrame(columns=['Ticker','Price_Change', 'Start_Date_Price','Stop_Date_Price','Start_Date', 'Stop_Date'])
historical_last_updated_df.set_index('Ticker', inplace=True)
# -----------------------------------------------------------------------------

ticker_list_unclean = tracklist_df['Tickers'].tolist()
ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']
# #############################################################################
#                   MAIN LOOP FOR TICKERS
# #############################################################################
# ticker_list = ['AAPL', 'AUDC','MED']
for ticker_raw in ticker_list:
  ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase
  logging.debug("================================")
  logging.info("Processing : " + str(ticker))

  if ticker in ['HIIQ' , 'AVP' , 'BAS', 'CRR'  , 'CSS'  , 'ECA'  , 'FII'  , 'HOS'  , 'IDSA'  , 'LGCYQ'  , 'MDCO'  , 'PESX'  , 'PIR'  , 'SRCI'  , 'SSW'  , 'WLH'  , 'WTR'  , 'XON']:
    continue

  # ---------------------------------------------------------------------------
  # Read the Historical data file and get the last date for which prices are available
  # If it is more than a month then put it in gt_1_month old
  # ---------------------------------------------------------------------------
  historical_df = pd.read_csv(dir_path + historical_dir + "\\" + ticker + "_historical.csv")
  date_str_list = historical_df.Date.tolist()
  date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in date_str_list]
  ticker_adj_close_list = historical_df.Adj_Close.tolist()

  start_date_match = min(date_list, key=lambda d: abs(d - start_date_dt))
  start_date_match_index = date_list.index(start_date_match)
  logging.debug("Matched User specified start date : " + str(start_date_dt) + " with " + str(start_date_match) + " in Historical df at index : " + str(start_date_match_index))

  stop_date_match = min(date_list, key=lambda d: abs(d - stop_date_dt))
  stop_date_match_index = date_list.index(stop_date_match)
  logging.debug("Matched User Specified stop date : " + str(stop_date_dt) + " with " + str(stop_date_match) + " in Historical df at index : " + str(stop_date_match_index))

  start_date_adj_close = ticker_adj_close_list[start_date_match_index]
  stop_date_adj_close = ticker_adj_close_list[stop_date_match_index]
  logging.debug("Start Date Adj. Price : " + str(start_date_adj_close) + " Stop Date Adj. Price : " + str(stop_date_adj_close))

  if (math.isnan(start_date_adj_close)):
    logging.error("The Price for Matching Start Date : " + str(start_date_match) + " is nan in the Historical df")
    sys.exit(1)
  if (math.isnan(stop_date_adj_close)):
    logging.error("The Price for Matching Stop Date : " + str(stop_date_match) + " is nan in the Historical df")
    sys.exit(1)

  price_change = 100*((stop_date_adj_close-start_date_adj_close)/start_date_adj_close)
  logging.debug("The price change is : " + str(price_change))

  historical_last_updated_df.loc[ticker, 'Price_Change'] = price_change
  historical_last_updated_df.loc[ticker, 'Stop_Date'] = stop_date_match
  historical_last_updated_df.loc[ticker, 'Start_Date'] = start_date_match
  historical_last_updated_df.loc[ticker, 'Stop_Date_Price'] = stop_date_adj_close
  historical_last_updated_df.loc[ticker, 'Start_Date_Price'] = start_date_adj_close

  # sys.exit(1)
# -----------------------------------------------------------------------------
# Print all the df to their respective files
# -----------------------------------------------------------------------------
logging.info("")
logging.info("Now saving sorted data in " + str(dir_path + log_dir) + " directory")
logging.info("All the files with sorted data will be available there. Please look there when the script completes")
historical_last_updated_logfile = "historical_price_change.csv"

historical_last_updated_df.sort_values(by=['Ticker'], ascending=[True]).to_csv(dir_path + log_dir + "\\" + historical_last_updated_logfile, index=True, header=True)
logging.info("Created : " + str(historical_last_updated_logfile) + " <-- Tickers sorted alphabetically")

logging.info("")
logging.info("********************")
logging.info("***** All Done *****")
logging.info("********************")
# -----------------------------------------------------------------------------
