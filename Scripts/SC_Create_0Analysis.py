import csv
import openpyxl
from openpyxl.styles import PatternFill
import os
import xlrd
import sys
import time
import pandas as pd
import datetime as dt
from yahoofinancials import YahooFinancials
import time
import logging
import xlsxwriter

#
# Define the directories and the paths
dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
historical_dir = "\\..\\" + "Historical"
earnings_dir = "\\..\\" + "Earnings"
dividend_dir = "\\..\\" + "Dividend"
log_dir = "\\..\\" + "Logs"
analysis_dir = "\\..\\" + "Analysis"
# ---------------------------------------------------------------------------
# Set Logging
# critical, error, warning, info, debug
# set up logging to file - see previous section for more details
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename=dir_path + log_dir + "\\" + 'SC_Create_0Analysis_debug.txt',
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
# ---------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Set the various dirs and read the AAII file
# -----------------------------------------------------------------------------
qtr_str_list = ['Q1', 'Q2', 'Q3', 'Q4', 'Q5', 'Q6', 'Q7', 'Q8']
yr_str_list = ['Y1', 'Y2', 'Y3', 'Y4', 'Y5', 'Y6', 'Y7']

tracklist_file = "Tracklist.csv"
tracklist_file_full_path = dir_path + user_dir + "\\" + tracklist_file
configuration_file = "Configurations.csv"
configurations_file_full_path = dir_path + user_dir + "\\" + configuration_file
tracklist_df = pd.read_csv(tracklist_file_full_path)


ticker_list_unclean = tracklist_df['Tickers'].tolist()
ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']
# #############################################################################
#                   MAIN LOOP FOR TICKERS
# #############################################################################
ticker_list = ['NATI']
for ticker_raw in ticker_list:

  ticker = ticker_raw.replace(" ", "").upper()  # Remove all spaces from ticker_raw and convert to uppercase
  logging.info("========================================================")
  logging.info("Processing for " + ticker)
  logging.info("========================================================")
  if (ticker in ["QQQ"]):
    logging.debug(str(ticker) + " is NOT in AAII df or is QQQ (etf). Will skip inserting EPS Projections..")
    continue

  # Read the ticker AAII data yr and qtr file to start
  ticker_datain_yr_file = ticker +  "_yr_data.csv"
  ticker_datain_yr_df = pd.read_csv(dir_path + analysis_dir + "\\" + "Yearly" + "\\" + ticker_datain_yr_file)
  logging.debug("The YR datain df \n" + ticker_datain_yr_df.to_string())


  logging.info("Done " + str(ticker))

logging.debug("All Done")
