import pandas as pd
import os
import sys
import time
import datetime as dt
import numpy as np
import logging
import math
import re
import json
from dateutil.relativedelta import relativedelta

# -----------------------------------------------------------------------------
# Read the master tracklist file into a dataframe
# -----------------------------------------------------------------------------
dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
log_dir = "\\..\\" + "Logs"
earnings_dir = "\\..\\" + "Earnings"
chaff_earnings_dir = "\\..\\" + "Chaff_Earnings"
master_tracklist_file = "Master_Tracklist.xlsm"

master_tracklist_df = pd.read_excel(dir_path + user_dir + "\\" + master_tracklist_file, sheet_name="Already_Analyzed")
# master_tracklist_df.sort_values('Tickers', inplace=True)
master_trackist_already_analyzed_ticker_list_unclean = master_tracklist_df['Tickers'].tolist()
master_trackist_already_analyzed_ticker_list = [x for x in master_trackist_already_analyzed_ticker_list_unclean if str(x) != 'nan']

tracklist_df = pd.read_csv(dir_path + user_dir + "\\" + 'Tracklist.csv')
tracklist_df.sort_values('Tickers', inplace=True)
ticker_list_unclean = tracklist_df['Tickers'].tolist()
ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']
# The index can only be changed after the Ticker has been put to list
# In other words index cannot be read as a list
tracklist_df.set_index('Tickers', inplace=True)
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
                    filename=dir_path + log_dir + "\\" + 'SC_CheckEarningsFileExits_debug.txt',
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

# disable and enable global level logging
logging.disable(sys.maxsize)
logging.disable(logging.NOTSET)
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Declare all the dataframes that we are going to need to write into and set their columns
# -----------------------------------------------------------------------------
earnings_file_exists_df = pd.DataFrame(columns=['Ticker','Exists'])
earnings_file_exists_df.set_index('Ticker', inplace=True)

# Read all the earnings file and chaff earnings files from their respective
# directories
earnings_dir_fullpath = dir_path + earnings_dir + "\\"
chaff_earnings_dir_fullpath = dir_path + chaff_earnings_dir + "\\"
earnings_file_list_all = os.listdir(earnings_dir_fullpath)
chaff_earnings_file_list_all = os.listdir(chaff_earnings_dir_fullpath)

# -----------------------------------------------------------------------------
# Loop through all the tickers and check whether the earnings file, corresponding
# to that ticker, exits in earnings directory or chaff directory and update the
# dataframe accordingly
# -----------------------------------------------------------------------------
# ticker_list = ['PLUS','AUDC', 'MED', 'IBM']
i_int = 1
for ticker_raw in ticker_list:
  ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase
  logging.debug("================================")

  earnings_file_name = ticker + "_earnings.csv"
  if earnings_file_name in earnings_file_list_all:
    earnings_file_exists_df.loc[ticker, 'Exists'] = 'Earnings'
  elif ticker in master_trackist_already_analyzed_ticker_list:
    earnings_file_exists_df.loc[ticker, 'Exists'] = 'Found_in_Already_Analyzed_MasterTrackist'
  elif earnings_file_name in chaff_earnings_file_list_all:
    earnings_file_exists_df.loc[ticker, 'Exists'] = 'Chaff'
  else:
    earnings_file_exists_df.loc[ticker, 'Exists'] = '0_None'
  logging.info("Iteration # " + str(i_int).ljust(3) + ", Processing : " + str(ticker).ljust(8) + ", Found in " + str(earnings_file_exists_df.loc[ticker, 'Exists']))
  i_int += 1

# -----------------------------------------------------------------------------
# Print the df to the file
# -----------------------------------------------------------------------------
logging.debug("Here is the dataframe : \n" + earnings_file_exists_df.to_string())

logging.info("")
logging.info("Now saving sorted data in " + str(dir_path + log_dir) + " directory")
logging.info("All the files with sorted data will be available there. Please look there when the script completes")

earnings_file_exists_logfile = "earnings_file_exists.txt"
earnings_file_exists_df.sort_values(by=['Exists','Ticker'], ascending=[True,True]).to_csv(dir_path + log_dir + "\\" + earnings_file_exists_logfile,sep=' ', index=True, header=False)

logging.info("Created : " + str(earnings_file_exists_logfile) + " <-- Sorted by whether earnings file was found or not")

logging.debug("Now will filter out anything that matches 0_None or Chaff")
earnings_file_exists_df.sort_values(['Exists', 'Ticker'], ascending=[True, True], inplace=True)
df1 = earnings_file_exists_df.loc[earnings_file_exists_df['Exists'].isin(['0_None','Chaff', 'Found_in_Already_Analyzed_MasterTrackist'])]
# df1.sort_values(['Exists', 'Ticker'], ascending=[True, True], inplace=True)
logging.info("\n\n=======================================================================")
logging.info("Here are the tickers that were either were not found or are Chaff : \n" + df1.to_string())
logging.info("===========================================================================")


