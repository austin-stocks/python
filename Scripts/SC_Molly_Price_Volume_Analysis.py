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
import xlsxwriter

def human_format(num, precision=2, suffixes=['', 'K', 'M', 'B', 'T', 'P']):
  m = sum([abs(num / 1000.0 ** x) >= 1 for x in range(1, len(suffixes))])
  return f'{num / 1000.0 ** m:.{precision}f}{suffixes[m]}'

# -----------------------------------------------------------------------------
# Read the master tracklist file into a dataframe
# -----------------------------------------------------------------------------
dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
log_dir = "\\..\\..\\..\\Automation_Not_in_Git\\" + "Logs"
price_vol_dir = "\\..\\..\\..\\Automation_Not_in_Git\\" + "Misc" + "\\" + "Molly_Price_Volume"
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
                    filename=dir_path + log_dir + "\\" + 'SC_Molly_Price_Volume_Analysis_debug.txt',
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
# Read the Price Volume file
# This file is created by downloading the Google Finance file from Google Drive
# every weekend.
# -----------------------------------------------------------------------------
# logging.info("")
file_date_str = input("Please input the date for which you want to run Price-Volume : ")
# file_date_str = "2023-08-11"
logging.info("")
price_vol_file = file_date_str + "-GoogleFinance-Price-Volume.xlsx"
logging.info("Reading the price volume file : " + str(price_vol_file) + ", and preparing for calculating Volume Averages and Price Change later...")
price_vol_xls = pd.ExcelFile(dir_path + price_vol_dir + "\\" + price_vol_file)
raw_price_df = pd.read_excel(price_vol_xls, 'Price')
raw_vol_df = pd.read_excel(price_vol_xls, 'Vol')
# logging.debug("The Raw Price DF \n" + raw_price_df.to_string())
# logging.debug("The Raw Vol DF \n" + raw_vol_df.to_string())

# ---------------------------------------------------------
# Drop the 'Date' column from the df as it is just something
# that is populated by GoogleFinance and just contains the
# string 'Price' or 'Volume' and is not needed by Sundeep
# ---------------------------------------------------------
raw_price_df.drop('Date', inplace=True, axis=1)
raw_price_df.reset_index
# logging.debug("The Price DF \n" + raw_price_df.to_string())
raw_price_df.set_index('SYMBOL', inplace=True)
raw_price_df.sort_index(ascending=True,inplace=True)
logging.info("It seems to have :: rows : " + str(len(raw_price_df.index.tolist())+1) + ", columns : " + str(len(raw_price_df.columns.tolist())))
raw_vol_df.drop('Date', inplace=True, axis=1)
raw_vol_df.reset_index
raw_vol_df.set_index('SYMBOL', inplace=True)
raw_vol_df.sort_index(ascending=True,inplace=True)

# ---------------------------------------------------------
# Do some sanity check to make sure that both the sheets have
# same number of rows and columns
# ---------------------------------------------------------
number_of_rows_in_price_sheet = len(raw_price_df.index.tolist())
number_of_cols_in_price_sheet = len(raw_price_df.columns.tolist())
number_of_rows_in_vol_sheet = len(raw_vol_df.index.tolist())
number_of_cols_in_vol_sheet = len(raw_vol_df.columns.tolist())
if (number_of_rows_in_price_sheet != number_of_rows_in_vol_sheet):
  logging.error ("")
  logging.error ("The number of rows on \"Price\" and \"Vol\" sheets DO NOT match")
  logging.error ("Price Sheet has   : " + str(number_of_rows_in_price_sheet) + " rows")
  logging.error ("Volume  Sheet has : " + str(number_of_rows_in_vol_sheet) + " rows")
  logging.error ("They need to match...did you forget to delete the last few rows in one of the sheet")
  logging.error ("Please fix and rerun")
  sys.exit(1)

if (number_of_cols_in_price_sheet != number_of_cols_in_vol_sheet):
  logging.error ("")
  logging.error ("The number of columns on \"Price\" and \"Vol\" sheets DO NOT match")
  logging.error ("Price Sheet has   : " + str(number_of_cols_in_price_sheet) + " columns")
  logging.error ("Volume  Sheet has : " + str(number_of_cols_in_vol_sheet) + " columns")
  logging.error ("They need to match...Maybe you just need to delete empty columns in both the sheets")
  logging.error ("OR maybe there is something wrong with downloaded data, please check the google sheets")
  logging.error ("Please fix and rerun")
  sys.exit(1)
# ---------------------------------------------------------


# logging.debug("The Price  DF after dropping the columne \'Date\' and setting the index to SYMBOL\n" + raw_price_df.to_string())
# logging.debug("The Volume DF after dropping the columne \'Date\' and setting the index to SYMBOL\n" + raw_vol_df.to_string())
# ---------------------------------------------------------

# ---------------------------------------------------------
# Get the columns in a list, they are datetime, and change
# them just to a convenient date str. Then set the columns
# in the dataframes to that date str
# ---------------------------------------------------------
col_date_list_dt = raw_price_df.columns.tolist()
logging.debug("Columns : " + str(col_date_list_dt) + ", and their # " + str(len(col_date_list_dt)))
# Get everything to the right of 1st column, which is "COUNT".
# Everything to the right of the "COUNT" col. should be dates
del col_date_list_dt[:1]
logging.debug("Columns with just dates (after removing the first entry (COUNT) : " + str(col_date_list_dt) + ", and their # " + str(len(col_date_list_dt)))
col_date_list_str = [d.strftime('%m/%d/%Y') for d in col_date_list_dt]
logging.debug("Date ONLY Columns (in str format) : " + str(col_date_list_str) + ", and their # " + str(len(col_date_list_str)))
# Set the columns back to "COUNT" and the date strings (NOT the date_dt)
raw_price_df.columns = ["COUNT"] +  col_date_list_str
raw_vol_df.columns = ["COUNT"] + col_date_list_str
logging.debug("The Raw Price DF after dates converted to strings : \n" + raw_price_df.to_string())
logging.debug("The Raw Vol DF after dates converted to strings : \n" + raw_vol_df.to_string())

# Set a range to check b/c the number of days for which the data
# is availabe changes from week to week (Google finance sheet is
# setup to download last 200 calendar days, which can be anywhere
# in the range below
if ((len(col_date_list_str) <= 131) or (len(col_date_list_str) >= 142)):
  logging.error("")
  logging.error("=====> There are : " + str(len(col_date_list_str)) + " Dates (Columns), in the Google Finance File <=====")
  logging.error("=====> That number is not b/w 131 and 140 <=====")
  logging.error("")
  logging.error("Sundeep has, by design, made Google Finance sheet to download 200 calendar days")
  logging.error("Those calendar days translate somewhere b/w 131 and 140 stock market days")
  logging.error("Sundeep reached that number through trial and error over many weeks of running that script (heuristic)")
  logging.error("")
  logging.error("However, depending upon stock market holidays, the number of columns can be slightly off")
  logging.error("So if the number of actual columns is slightly off, then that just means")
  logging.error("that there were fewer or more stock market holidays. In that case please adjust")
  logging.error("the acceptable range in the IF statement above in the python code")
  logging.error("")
  logging.error("However, if the number is a lot off...say it is 125 or 145, then need to check")
  logging.error("Google Finance sheet to make sure that the data over there is downloading property")
  logging.error("Please check and correct and run again. Exiting...")
  logging.error("")
  sys.exit(1)
# ---------------------------------------------------------


# ---------------------------------------------------------
# Create new dataframes that are needed to be populated by
# the code later and will be written to the logfile for
# further processing by the VBA script later
# ---------------------------------------------------------
vol_dma_5d_df = raw_vol_df.copy()
vol_dma_21d_df = raw_vol_df.copy()
vol_dma_50d_df = raw_vol_df.copy()
price_change_1d_df = raw_price_df.copy()

# -----------------------------------------------------------------------------
# Iterate through the vol df and calcuate the 5 dma, 21 dma and 50 dma and
# populate the respective dfs
# Also, since the column name are the same for both price and vol dfs, update
# the price change df as well (otherwise need to write similar loop again)
# -----------------------------------------------------------------------------
logging.info("Starting to calculate Volume Averages and Price Change...")
ticker_list_unclean = raw_vol_df.index.tolist()
ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']
i_idx_outer = 1
for i_ticker, row in raw_vol_df.iterrows():
  logging.debug("Creating Volume Averages for ticker : " + str(i_ticker))
  raw_vol_list = row.tolist()
  logging.debug(str(i_ticker) + " : Volume List : " + str(raw_vol_list))

  if (i_idx_outer%100 == 0 ):
    logging.info("Processing Row : " + str(i_idx_outer))
  # ---------------------------------------------------------
  # Pretty cool way of getting rolling mean over a list
  # The first entry in the row for each ticker is "COUNT" column
  # So skip the first entry in the list and calculate the
  # SMA staring from the next entry (entry #1)
  # ---------------------------------------------------------
  numbers_series = pd.Series(raw_vol_list[1:])
  tmp_vol_dma_5d_list = numbers_series.rolling(5).mean().tolist()[5 - 1:]
  tmp_vol_dma_21d_list = numbers_series.rolling(21).mean().tolist()[21 - 1:]
  tmp_vol_dma_50d_list = numbers_series.rolling(50).mean().tolist()[50 - 1:]

  # These can be uncommented to debug to look at the numbers per ticker
  # as they are getting processed
  # logging.debug("The 5 day dma of the volume is " + str(tmp_vol_dma_5d_list))
  # logging.debug("Length of 5 day dma of the volume is : " + str(len(tmp_vol_dma_5d_list)))
  # logging.debug("The 21day dma of the volume is " + str(tmp_vol_dma_21d_list))
  # logging.debug("Length of 21 day dma of the volume is : " + str(len(tmp_vol_dma_21d_list)))
  # logging.debug("The 50 day dma of the volume is " + str(tmp_vol_dma_50d_list))
  # logging.debug("Length of 50 day dma of the volume is : " + str(len(tmp_vol_dma_50d_list)))

  # ---------------------------------------------------------
  # Populate the various DF for the ticker row
  # ---------------------------------------------------------
  for i_idx in range(len(col_date_list_str)-1):
    col_date_str = col_date_list_str[i_idx]
    col_date_str_next = col_date_list_str[i_idx+1]
    if i_idx < (len(col_date_list_str)-5):
      vol_dma_5d_df.at[i_ticker, col_date_str] = tmp_vol_dma_5d_list[i_idx]
    if i_idx < (len(col_date_list_str)-21):
      vol_dma_21d_df.at[i_ticker, col_date_str] = tmp_vol_dma_21d_list[i_idx]
    if i_idx < (len(col_date_list_str)-50):
      vol_dma_50d_df.at[i_ticker, col_date_str] = tmp_vol_dma_50d_list[i_idx]
    if i_idx < (len(col_date_list_str)-1):
      price_change_1d_df.at[i_ticker, col_date_str] = (raw_price_df.at[i_ticker,col_date_str]/raw_price_df.at[i_ticker,col_date_str_next])-1

  i_idx_outer = i_idx_outer+1
# -----------------------------------------------------------------------------
# logging.debug("The 5dma Vol DF \n" + vol_dma_5d_df.to_string())
# logging.debug("The 21dma Vol DF \n" + vol_dma_21d_df.to_string())
# logging.debug("The 50dma Vol DF \n" + vol_dma_50d_df.to_string())
# logging.debug("The Price Change DF \n" + price_change_1d_df.to_string())
logging.info("Done...")
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Finally Write the output in xlsx file
# TODO : I am writing the same data in two files (they are copies of each other)
# I am remove the copy when I get more confidence in getting the VBA to do
# what I want to do
# -----------------------------------------------------------------------------
now = dt.datetime.now()
date_time = now.strftime("%Y-%m-%d")
file_date_str

# mollyverse_price_vol_xlsx = date_time + "-Molly-Price-Volume.xlsx"
# mollyverse_price_vol_xlsx_copy = date_time + "-Molly-Price-Volume_copy.xlsx"
mollyverse_price_vol_xlsx = file_date_str + "-Molly-Price-Volume.xlsx"
mollyverse_price_vol_xlsx_copy = file_date_str + "-Molly-Price-Volume_copy.xlsx"
logging.info("Now writing Volume Averages and Price Change into :")
logging.info(str(dir_path + price_vol_dir) + "\\" + str(mollyverse_price_vol_xlsx))

# with pd.ExcelWriter(dir_path + log_dir + "\\" + mollyverse_price_vol_xlsx) as writer:
with pd.ExcelWriter(dir_path + price_vol_dir + "\\" + mollyverse_price_vol_xlsx) as writer:
  price_change_1d_df.to_excel(writer, sheet_name='Price-Chg', header=True)
  raw_price_df.to_excel(writer, sheet_name='Price', header=True)
  raw_vol_df.to_excel(writer, sheet_name='Vol', header=True)
  vol_dma_5d_df.to_excel(writer, sheet_name='Vol-5dma', header=True)
  vol_dma_21d_df.to_excel(writer, sheet_name='Vol-21dma', header=True)
  vol_dma_50d_df.to_excel(writer, sheet_name='Vol-50dma', header=True)

# with pd.ExcelWriter(dir_path + log_dir + "\\" + mollyverse_price_vol_xlsx_copy) as writer_copy:
with pd.ExcelWriter(dir_path + price_vol_dir + "\\" + mollyverse_price_vol_xlsx_copy) as writer_copy:
  price_change_1d_df.to_excel(writer_copy, sheet_name='Price-Chg', header=True)
  raw_price_df.to_excel(writer_copy, sheet_name='Price', header=True)
  raw_vol_df.to_excel(writer_copy, sheet_name='Vol', header=True)
  vol_dma_5d_df.to_excel(writer_copy, sheet_name='Vol-5dma', header=True)
  vol_dma_21d_df.to_excel(writer_copy, sheet_name='Vol-21dma', header=True)
  vol_dma_50d_df.to_excel(writer_copy, sheet_name='Vol-50dma', header=True)

logging.info("")
logging.info("ALL DONE...")
# -----------------------------------------------------------------------------

