
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
chaff_earnings_dir = "\\..\\" + "Chaff_Earnings"
ls_earnings_filename = "ls_earnings_file.sh"
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
master_tracklist_file = "Master_Tracklist.xlsm"
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
ann_ticker_list    = tracklist_ann_df['Ticker'].tolist()
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
logging.info("Found : " + str(len(only_in_master_list)) + " tickers only in Master Tracklist")
logging.debug("Found these tickers only in Master Tracklist" + str(only_in_master_list))

logging.info("")
logging.info("Looping through Ann Tracklist Tickers to see if they are found in Master Tracklist")
for ticker_raw in ann_ticker_list:
  ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase
  # logging.debug("Looking for " + str(ticker) + " from Ann Trackist in Master Tracklist")
  if ticker in ["QQQ", "WIZ"]:
    continue
  if ticker not in master_ticker_list:
    logging.debug ("Did not find " + str(ticker) + " in Master Tracklist List")
    only_in_ann_list.append(ticker)
logging.info("Found : " + str(len(only_in_ann_list)) + " tickers only in Ann Tracklist")
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

logging.info("\n")
logging.info("Printing all tickers found ONLY in Ann Tracklist to, " + str(ls_earnings_filename) + ", in chaff_earnings dir")
logging.info("You can just execute that script")
logging.info(" cd /c/Sundeep/Stocks_Automation/chaff_earnings")
logging.info("./ls_earnings_file.sh")
logging.info("to find which tickers Sundeep had tracked in the past...")
logging.info("Those earnings file are available in chaff earnings directory to decide whether ")
logging.info("to move those earnings file to earnings directory and update and use them or")
logging.info("extract earnings from Ann stock xlsm file...")
logging.info("Note : There would be many earnings file that would not be found in chaff earnings")
logging.info("     : directory. Those would be brand new stocks that Sundeep has not tracked before")
logging.info("     : For them, Sundeep would need to extract earnings from Ann stock xlsm")
with open(dir_path + chaff_earnings_dir + "\\" + ls_earnings_filename, 'w') as f:
  f.write("## -------------------------------------------------------------------------------\n")
  f.write("## This script is used to find out if the earnings file exist in this directory   \n")
  f.write("##                                                                                \n")
  f.write("## The script is automatically created by SC_compare_Tracklists.py script         \n")
  f.write("## and contains the list of files that were found in Ann Trackist but not in      \n")
  f.write("## Sundeep Master Tracklist. So, this script can be use to see if those tickers   \n")
  f.write("## that Ann is tracking but Sundeep is not, are in the chaff earnings directory.  \n")
  f.write("## (which means that Sundeep had tracked them sometime in the past)               \n")
  f.write("##                                                                                \n")
  f.write("## If Sundeep desires then the chaff earnings file can be moved, relatively       \n")
  f.write("## easily, to earnings directory to start tracking them.                          \n")
  f.write("##                                                                                \n")
  f.write("## That decision Sundeep can make after looking at Ann chart for the ticker and   \n")
  f.write("## then looking at the state of chaff earnings file.                              \n")
  f.write("##                                                                                \n")
  f.write("## Sometimes it would be more practical to just take Ann xlsm file for that       \n")
  f.write("## ticker and extract the earning data out of it instead.                         \n")
  f.write("## This can happen b/c the chaff earnings file might have gotten too old          \n")
  f.write("## and / or Sundeep might have changed to formatting of earnings file so much     \n")
  f.write("## that it would be less work instead to just extract earnings from Ann xlsm file \n")
  f.write("## and use that as earnings file moving forward.                                  \n")
  f.write("## -------------------------------------------------------------------------------\n")
  for line in list(only_in_ann_df.index.values):
    f.write("ls " + line + "_earnings.csv\n")

# print those dateframes in a file
logging.info("")
logging.info("Now Printing the info in log directory")
only_in_master_tracklist_logfile = "Tickers_only_in_Master_Trackelist.txt"
only_in_ann_tracklist_logfile = "Tickers_only_in_Ann_Trackelist.txt"
only_in_master_df.sort_values(by=['Ticker'], ascending=[True]).to_csv(dir_path + log_dir
                                                                      + "\\" + only_in_master_tracklist_logfile,sep=' ', index=True, header=False)
only_in_ann_df.sort_values(by=['Ticker'], ascending=[True]).to_csv(dir_path + log_dir + "\\" + only_in_ann_tracklist_logfile,sep=' ', index=True, header=False)
logging.info("Put tickers that were found only in Master Tracklist in : " + str(only_in_master_tracklist_logfile))
logging.info("Put tickers that were found only in Ann's  Tracklist in : " + str(only_in_ann_tracklist_logfile))
# =============================================================================

logging.info("All Done")
