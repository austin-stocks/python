import pandas as pd
import os
import sys
import time
import datetime as dt
import numpy as np
import re
import shutil
import glob
import logging

# -----------------------------------------------------------------------------
# Read the master tracklist file into a dataframe
# -----------------------------------------------------------------------------
dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
charts_dir = "\\..\\" + "Charts"
charts_latest_dir = "\\..\\" + "Latest_Charts"
log_dir = "\\..\\" + "Logs"

master_tracklist_file = "Master_Tracklist.xlsx"
master_tracklist_df = pd.read_excel(dir_path + user_dir + "\\" + master_tracklist_file, sheet_name="Main")
master_tracklist_df.sort_values('Ticker', inplace=True)
ticker_list_unclean = master_tracklist_df['Ticker'].tolist()
ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']
master_tracklist_df.set_index('Ticker', inplace=True)
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
                    filename=dir_path + log_dir + "\\" + 'SC_CopyLastest_Charts_debug.txt',
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
# Get the files from the chart directory in a list
# and remove all the files from the Charts Latest directory
# -----------------------------------------------------------------------------
all_chart_files_list=os.listdir(dir_path + charts_dir + "\\")
logging.debug("The files in the chart directory are" + str(all_chart_files_list))

# This works - but it removes all the files in the directory - and that we don't
# want now as it will delete (or try to delete) git stuff from the directory too.
# list( map( os.unlink, (os.path.join(dir_path + charts_latest_dir + "\\" ,f) for f in os.listdir(dir_path + charts_latest_dir + "\\")) ) )
# So instead get the jpg file in a list and then recurse over the list to
# remove the files from the chart_latest_dir
# jpg_file_list = [filename for filename in all_chart_files_list if 'jpg' in filename]
jpg_file_list = glob.glob(dir_path + charts_latest_dir + "\\*.jpg" )
logging.info("The Chart file list in the " + str(charts_latest_dir) + " direcotory are :\n" + str(jpg_file_list))
for filePath in jpg_file_list:
  try:
    os.remove(filePath)
  except:
    logging.error("================================================================================")
    logging.error("Error while trying to deleting file : " + str(filePath))
    logging.error("All the existing chart files from " + str(charts_latest_dir) + " need to be removed before the script can proceed")
    logging.error( "Please resolve this issue before proceeding...Exiting now")
    logging.error("================================================================================")
    sys.exit(1)
time.sleep(3)
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Loop through all the wheat tickers in the master Tracklist file
# -----------------------------------------------------------------------------
for ticker_raw in ticker_list:
  ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase
  logging.debug("")
  logging.info("Processing : " + str(ticker))
  # if ticker in ["CCI", , "CY", "EXPE", "FLS", "GCBC","GOOG","HURC","KMI","KMX","PNFP","QQQ","RCMT","TMO","TMUS","TTWO",,"WLTW"]:
  if ticker in ["QQQ"]:
    logging.debug("File for " + str(ticker) + " does not exist in earnings directory. Skipping...")
    continue
  ticker_is_wheat = master_tracklist_df.loc[ticker, 'Quality_of_Stock']
  if (ticker_is_wheat != 'Wheat') and (ticker_is_wheat != 'Essential') and (ticker_is_wheat != 'Wheat_Chaff'):
    logging.info(str(ticker) +  " is not Wheat or Essential...skipping")
    continue

  # Find the corresponding jpg files from the charts directory list
  # todo : Get the regular expression so that it matches the numbers...so that we don't get
  # any spurious (like AMZN_2019_12_01_thislooksgood.jpg or AMZN_thislooksbac.jpg)
  my_regex = re.compile(re.escape(ticker) + re.escape("_")  + ".*jpg")
  ticker_chart_files_list = list(filter(my_regex.match, all_chart_files_list)) # Read Note
  logging.debug("ALL the chart files for " + str(ticker) + " are " + str(ticker_chart_files_list))

  # For each file split the file name to get the date string.
  # Then convert the date string to datetime and append it to the list
  ticker_chart_date_list = []
  for ticker_chart_filename in ticker_chart_files_list:
    # Check the length of the filename - it should be number of characters in the ticker and 16
    if len(ticker_chart_filename) > (len(ticker) + 16):
      logging.info("Error : The filename " + str(ticker_chart_filename) + " has more characters than allowed")
      logging.info("Will skip this filename and go on to next one...You should investigate why this is...the chart directory should have jpg file that adhere to the filename convention")
      continue

    # Remove the .jpg at the end and then get the last 10 characters of the filename
    ticker_chart_date_str = (ticker_chart_filename[:-4])[-10:]
    ticker_chart_date_dt = dt.datetime.strptime(ticker_chart_date_str, "%Y_%m_%d")
    logging.debug("The date string for " + str(ticker_chart_filename) + " is " + str(ticker_chart_date_str) + " and the datetime is " + str(ticker_chart_date_dt))
    ticker_chart_date_list.append(ticker_chart_date_dt)

  logging.debug("The datetime list for all jpg files for " + str(ticker) + " is " + str(ticker_chart_date_list))
  # Sort the list to the get the latest (youngest) datetime
  # and create a string for the ticker filename from the string
  ticker_chart_date_list.sort(reverse=True)
  logging.debug("The datetime SORTED list for all jpg files for " + str(ticker) + " is " + str(ticker_chart_date_list))
  if (len(ticker_chart_date_list) > 0):
    ticker_latest_chart = ticker_chart_date_list[0].strftime('%Y_%m_%d')
    ticker_latest_chart_filename = ticker + "_" + ticker_latest_chart + ".jpg"
    logging.info("The lastest file for " + str(ticker) + " is : " + str(ticker_latest_chart_filename) + " Copying it over to Latest Charts directory...")

  # Copy the chart file - that was the youngest - to the desitnation directory as ticker_Latest.jpg
  shutil.copy2(dir_path + charts_dir + "\\" + ticker_latest_chart_filename, dir_path + charts_latest_dir + "\\" + ticker + "_Latest.jpg")

logging.info("")
logging.info(".....ALL DONE.....")