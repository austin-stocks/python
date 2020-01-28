import pandas as pd
import os
import sys
import time
import datetime as dt
import numpy as np
import re
import shutil

# # -----------------------------------------------------------------------------
# # Get all the files in the Earnings directory that end with _earnings.csv
# # -----------------------------------------------------------------------------
# for file in os.listdir("C:\Sundeep\Stocks_Automation\Charts"):
#   if file.endswith(".jpg"):
#     Chart_fullpath = os.path.join("C:\Sundeep\Stocks_Automation\Charts", file)
#     # print(file_fullpath)
#     # -------------------------------------------------------------------------
#     # Open the file and see if it has a column by the name of <XYN>
#     # -------------------------------------------------------------------------
# # -----------------------------------------------------------------------------

# # -----------------------------------------------------------------------------
# # Read the master tracklist file into a dataframe
# # -----------------------------------------------------------------------------
dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
master_tracklist_file = "Master_Tracklist.xlsx"
master_tracklist_df = pd.read_excel(dir_path + user_dir + "\\" + master_tracklist_file, sheet_name="Main")
master_tracklist_df.sort_values('Ticker', inplace=True)
ticker_list_unclean = master_tracklist_df['Ticker'].tolist()
ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']
master_tracklist_df.set_index('Ticker', inplace=True)
# # -----------------------------------------------------------------------------
#
# Get the Charts files in a list
all_chart_files_list=os.listdir(r"C:\\Sundeep\\Stocks_Automation\\Charts\\")
print ("The files in the chart direcotry are", all_chart_files_list)


# -----------------------------------------------------------------------------
# Loop through all the wheat tickers in the master Tracklist file
# And find the corresponding jpg files from the charts directory
# -----------------------------------------------------------------------------
for ticker_raw in ticker_list:
  ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase
  print("\nProcessing : ", ticker)
  # if ticker in ["CCI", , "CY", "EXPE", "FLS", "GCBC","GOOG","HURC","KMI","KMX","PNFP","QQQ","RCMT","TMO","TMUS","TTWO",,"WLTW"]:
  if ticker in ["QQQ"]:
    print ("File for ", ticker, "does not exist in earnings directory. Skipping...")
    continue
  ticker_is_wheat = master_tracklist_df.loc[ticker, 'Quality_of_Stock']
  if (ticker_is_wheat != 'Wheat'):
    print (ticker , " is not Wheat...skipping")
    continue

  my_regex = re.compile(re.escape(ticker) + re.escape("_")  + ".*jpg")
  ticker_chart_files_list = list(filter(my_regex.match, all_chart_files_list)) # Read Note
  print(ticker_chart_files_list)

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
  ticker_chart_date_list.sort(reverse=True)
  print ("The datetime SORTED list for ", ticker, " is ", ticker_chart_date_list)
  if (len(ticker_chart_date_list) > 0):
    ticker_latest_chart = ticker_chart_date_list[0].strftime('%Y_%m_%d')
    ticker_latest_chart_filename = ticker + "_" + ticker_latest_chart + ".jpg"
    print ("The latest file for ", ticker, "is", ticker_latest_chart_filename)

  shutil.copy2('C:\\Sundeep\\Stocks_Automation\\Charts\\' + ticker_latest_chart_filename, 'C:\\Sundeep\\Stocks_Automation\\Latest_Charts')
