import pandas as pd
import os
import sys
import time
import datetime as dt
import numpy as np
import re
import shutil
import glob

# Todo : Put the logger in
# Todo : Maybe handle liner short/ linear long/ Log charts
# # -----------------------------------------------------------------------------
# # Read the master tracklist file into a dataframe
# # -----------------------------------------------------------------------------
dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
charts_dir = "\\..\\" + "Charts"
charts_latest_dir = "\\..\\" + "Latest_Charts"

master_tracklist_file = "Master_Tracklist.xlsx"
master_tracklist_df = pd.read_excel(dir_path + user_dir + "\\" + master_tracklist_file, sheet_name="Main")
master_tracklist_df.sort_values('Ticker', inplace=True)
ticker_list_unclean = master_tracklist_df['Ticker'].tolist()
ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']
master_tracklist_df.set_index('Ticker', inplace=True)
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Get the files from the chart directory in a list
# and remove all the files from the Charts Latest directory
# -----------------------------------------------------------------------------
all_chart_files_list=os.listdir(dir_path + charts_dir + "\\")
print ("The files in the chart direcotry are", all_chart_files_list)

# This works - but it removes all the files in the directory - and that we don't want now
# as it will delete (or try to delete) git stuff from the directory too.
# list( map( os.unlink, (os.path.join(dir_path + charts_latest_dir + "\\" ,f) for f in os.listdir(dir_path + charts_latest_dir + "\\")) ) )
# So now then get the jpg file in a list and then recurse over the list to
# remove the files from the chart_latest_dir
# jpg_file_list = [filename for filename in all_chart_files_list if 'jpg' in filename]
jpg_file_list = glob.glob(dir_path + charts_latest_dir + "\\*.jpg" )
print ("The Chart file list in the ", charts_latest_dir, " direcotory are :\n", jpg_file_list)
for filePath in jpg_file_list:
  try:
    os.remove(filePath)
  except:
    print("Error while deleting file : ", filePath)
time.sleep(3)

# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Loop through all the wheat tickers in the master Tracklist file
# -----------------------------------------------------------------------------
for ticker_raw in ticker_list:
  ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase
  print("\nProcessing : ", ticker)
  # if ticker in ["CCI", , "CY", "EXPE", "FLS", "GCBC","GOOG","HURC","KMI","KMX","PNFP","QQQ","RCMT","TMO","TMUS","TTWO",,"WLTW"]:
  if ticker in ["QQQ"]:
    print ("File for ", ticker, "does not exist in earnings directory. Skipping...")
    continue
  ticker_is_wheat = master_tracklist_df.loc[ticker, 'Quality_of_Stock']
  if (ticker_is_wheat != 'Wheat') and (ticker_is_wheat != 'Essential') and (ticker_is_wheat != 'Wheat_Chaff'):
    print (ticker , " is not Wheat or Essential...skipping")
    continue

  # Find the corresponding jpg files from the charts directory list
  # todo : Get the regular expression so that it matches the numbers...so that we don't get
  # any spurious (like AMZN_2019_12_01_thislooksgood.jpg or AMZN_thislooksbac.jpg)
  my_regex = re.compile(re.escape(ticker) + re.escape("_")  + ".*jpg")
  ticker_chart_files_list = list(filter(my_regex.match, all_chart_files_list)) # Read Note
  print(ticker_chart_files_list)

  # For each file split the file name to get the date string.
  # Then covert the date string to datetime and append it to the list
  ticker_chart_date_list = []
  for ticker_chart_filename in ticker_chart_files_list:
    # Check the length of the filename - it should be number of characters in the ticker and 16
    if len(ticker_chart_filename) > (len(ticker) + 16):
      print ("Error : The filename", ticker_chart_filename, "has more characters than allowed")
      continue

    # Remove the .jpg at the end and then get the last 10 characters of the filename
    ticker_chart_date_str = (ticker_chart_filename[:-4])[-10:]
    ticker_chart_date_dt = dt.datetime.strptime(ticker_chart_date_str, "%Y_%m_%d")
    print ("The date string for ", ticker_chart_filename , "is ", ticker_chart_date_str, "and the datetime is ", ticker_chart_date_dt)
    ticker_chart_date_list.append(ticker_chart_date_dt)

  print ("The datetime list for ", ticker, " is ", ticker_chart_date_list)
  # Sort the list to the get the latest (youngest) datetime
  # and create a string for the ticker filename from the string
  ticker_chart_date_list.sort(reverse=True)
  print ("The datetime SORTED list for ", ticker, " is ", ticker_chart_date_list)
  if (len(ticker_chart_date_list) > 0):
    ticker_latest_chart = ticker_chart_date_list[0].strftime('%Y_%m_%d')
    ticker_latest_chart_filename = ticker + "_" + ticker_latest_chart + ".jpg"
    print ("The latest file for ", ticker, "is", ticker_latest_chart_filename)

  # Copy the chart file - that was the youngest - to the desitnation directory as ticker_Latest.jpg
  shutil.copy2(dir_path + charts_dir + "\\" + ticker_latest_chart_filename, dir_path + charts_latest_dir + "\\" + ticker + "_Latest.jpg")

