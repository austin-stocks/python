
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
log_dir = "\\..\\" + "Logs"
# ---------------------------------------------------------------------------
# Set Logging
# critical, error, warning, info, debug
# set up logging to file - see previous section for more details
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename=dir_path + log_dir + "\\" + 'SC_compare_Tracklists_debug.txt',
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
# Set the various dirs and read both the Tracklists
# -----------------------------------------------------------------------------
master_tracklist_file = "Master_Tracklist.xlsx"
tracklist_file_ann = "Tracklist_from_Ann.xlsm"

logging.info ("Reading Master Tracklist and Ann Tracklist files")
start = time.process_time()
master_tracklist_df = pd.read_excel(dir_path + user_dir + "\\" + master_tracklist_file, sheet_name="Main")
tracklist_ann_df = pd.read_excel(dir_path + user_dir + "\\" + tracklist_file_ann, sheet_name="alphabetical")
# Takes around 23 seconds
logging.info ("The reading of Tracklist files took around " + str(time.process_time() - start) + " seconds")

logging.debug("Master Tracklist \n\n" + master_tracklist_df.to_string())
logging.debug("Ann Tracklist \n\n" + tracklist_ann_df.to_string())

# Rename to columns in Ann df and remove the NaN from Ticker and Quality_of_stock columns
tracklist_ann_df.rename({'Unnamed: 1': 'Ticker', 'm =': 'Quality_of_Stock','Unnamed: 5': 'Owned_By' }, axis=1, inplace=True)
# Now drop the rows in Ann DF that have NaN in 'Ticker' or 'Quality_of_Stock' columns
tracklist_ann_df.dropna(subset=['Ticker'], inplace=True)
tracklist_ann_df.dropna(subset=['Quality_of_Stock','Owned_By'], how='all', inplace=True)
logging.debug("============================================================================")
logging.debug("The tracklist from Ann after renaming and removing NaN from the the columns\n\n" + tracklist_ann_df.to_string())
# -----------------------------------------------------------------------------


# =============================================================================
# Now iterate through both the dataframes and create two lists:
# 1. List that contains the tickers that are ONLY found in Master Tracklist
# 2. List the contains  the tickers that are ONLY found in Ann Tracklist
# =============================================================================
master_ticker_list = master_tracklist_df['Tickers'].tolist()
ann_ticker_list     = tracklist_ann_df['Ticker'].tolist()
logging.debug("Total Number of Tickers extracted from Master Tracklist " + str(len(master_ticker_list)))
logging.debug("Total Number of Tickers extracted from Ann Tracklist " + str(len(ann_ticker_list)))
logging.debug("The List of tickers extracted from Master Tacklist " + str(master_ticker_list))
logging.debug("The List of tickers extracted from Ann Tacklist " + str(ann_ticker_list))

only_in_master_list = []
only_in_ann_list = []

logging.info("\n")
logging.info("Looping through Master Tracklist Tickers to see if they are found in Ann Tracklist")
for ticker_raw in master_ticker_list:
  ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase
  # logging.debug("Looking for " + str(ticker) + " from Master Trackist in Ann Tracklist")
  if ticker not in ann_ticker_list:
    logging.debug ("Did not find " + str(ticker) + " in Ann List")
    only_in_master_list.append(ticker)

logging.info("Looping through Ann Tracklist Tickers to see if they are found in Master Tracklist")
for ticker_raw in ann_ticker_list:
  ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase
  # logging.debug("Looking for " + str(ticker) + " from Ann Trackist in Master Tracklist")
  if ticker in ["QQQ", "WIZ"]:
    continue
  if ticker not in master_ticker_list:
    logging.debug ("Did not find " + str(ticker) + " in Master Tracklist List")
    only_in_ann_list.append(ticker)

logging.debug("Found these tickers only in Master Tracklist" + str(only_in_master_list))
logging.debug("Found these tickers only in Ann Tracklist" + str(only_in_ann_list))

# Till this point we should have two list
# =============================================================================

# =============================================================================
# Now that we have gotten the Tickers in the "ONLY" lists Reindex the original dataframes
master_tracklist_df.set_index('Tickers', inplace=True)
tracklist_ann_df.set_index('Ticker', inplace=True)

# Declare the dataframes that we will use to store the exclusive Tickers along
# with their respective Quality_of_Stock
only_in_master_df = pd.DataFrame(columns=['Ticker','Quality_of_Stock'])
only_in_ann_df = pd.DataFrame(columns=['Ticker','Quality_of_Stock', 'Owned_By'])
only_in_master_df.set_index('Ticker', inplace=True)
only_in_ann_df.set_index('Ticker', inplace=True)

# Start Populating the "only" dataframes
# Populate the dataframe that has tickers that were ONLY found in Master Tracklist along with their respective Quality_of_Stock
logging.info("\n")
logging.info("Finding the quality of tickers that were found only in Master Tracklist")
for ticker_raw in only_in_master_list:
  ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase
  quality_of_stock = master_tracklist_df.loc[ticker, 'Quality_of_Stock']
  logging.debug ("The " + str(ticker)  + " is of Quality " + str(quality_of_stock))
  only_in_master_df.loc[ticker] = quality_of_stock

# Populate the dataframe that has tickers that were ONLY found in Ann Tracklist  along with their respective Quality_of_Stock
logging.info("Finding the quality of tickers that were found only in Ann Tracklist")
for ticker_raw in only_in_ann_list:
  ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase
  quality_of_stock = tracklist_ann_df.loc[ticker, 'Quality_of_Stock']
  owned_by = tracklist_ann_df.loc[ticker, 'Owned_By']
  logging.debug ("The " + str(ticker)  + " is of Quality " + str(quality_of_stock))
  only_in_ann_df.loc[ticker,'Quality_of_Stock'] = quality_of_stock
  only_in_ann_df.loc[ticker,'Owned_By'] = owned_by

# print those dateframes in a file
logging.info("\n")
logging.info("Printing all the info in log directory")
only_in_master_tracklist_logfile = "Tickers_only_in_Master_Trackelist.txt"
only_in_ann_tracklist_logfile = "Tickers_only_in_Ann_Trackelist.txt"
only_in_master_df.sort_values(by=['Ticker'], ascending=[True]).to_csv(dir_path + log_dir + "\\" + only_in_master_tracklist_logfile,sep=' ', index=True, header=False)
only_in_ann_df.sort_values(by=['Ticker'], ascending=[True]).to_csv(dir_path + log_dir + "\\" + only_in_ann_tracklist_logfile,sep=' ', index=True, header=False)
# =============================================================================

logging.info("All Done")
