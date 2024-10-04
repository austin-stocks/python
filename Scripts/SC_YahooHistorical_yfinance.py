# ##############################################################################
# Download the historical data into individual csv
# ##############################################################################

import csv
import datetime
import openpyxl
import os
import xlrd
import time
import sys
import pandas as pd
from termcolor import colored, cprint
from dateutil.relativedelta import relativedelta
import yfinance as yf
from pandas_datareader import data as pdr

# ##############################################################################

# =============================================================================
# Define the various File names and Directory Paths to be used and set the
# start and end dates
# =============================================================================
dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
earnings_dir = "\\..\\" + "Earnings"
tracklist_file = "Tracklist.csv"
tracklist_file_full_path = dir_path + user_dir + "\\" + tracklist_file
yahoo_hist_out_dir = dir_path + "\\..\\Download\\YahooHistorical"
yahoo_hist_out_dir = dir_path + "\\..\\..\\..\\Automation_Not_in_Git\\YahooHistorical"
print(yf.__file__)
print(yf.__spec__)
yf.pdr_override() # <== that's all it takes :-)
# Need to have version 0.2.40 (The latest version 0.2.44 does not work...there
# is some problem with pdr_override, so maybe the data needs to be received
# differently
# =============================================================================

# ##############################################################################
# The following block of code:
# 1. Reads the Tracklist - sheet alphabetical - Column B (2nd Colunm)
# 2. Get the 2nd column (note that the column does not have a header)
#    The 2nd column has all the tickers
# 3. Put the first row of that column in first_row list
# 4. Put the rest of the tickers in rest_list
# 5. Concatenate both the lists into ticker_list
# ##############################################################################
get_sp_holdings = 0
get_qqq_holdings = 0
get_ibd50_holdings = 0
if (get_sp_holdings == 1):
  tracklist_df = pd.read_excel(dir_path + user_dir + "\\" + 'SPY_Holdings.xlsx', sheet_name="SPY")
  ticker_list_unclean = tracklist_df['Identifier'].tolist()
  ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']
elif (get_qqq_holdings == 1):
  tracklist_df = pd.read_excel(dir_path + user_dir + "\\" + 'QQQ_Holdings.xlsx', sheet_name="QQQ")
  ticker_list_unclean = tracklist_df['HoldingsTicker'].tolist()
  ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']
elif (get_ibd50_holdings == 1):
  tracklist_df = pd.read_excel(dir_path + user_dir + "\\" + 'IBD50_Holdings.xlsx', sheet_name="IBD50")
  ticker_list_unclean = tracklist_df['Symbol'].tolist()
  ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']
else:
  tracklist_df = pd.read_csv(tracklist_file_full_path)
  # print ("The Tracklist df is", tracklist_df)
  ticker_list_unclean = tracklist_df['Tickers'].tolist()
  ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']




# =============================================================================
#  for each ticker in ticker_list
# 1. Get the historical data from Yahoo
# 2. Extract the relevant data in the format that we want
# 2. Write that data in csv
# =============================================================================
# Start date is now defined by the earliest date from the earnings file
end_date_raw = datetime.datetime.today() + datetime.timedelta(days=1)
end_date = end_date_raw.strftime('%Y-%m-%d')
print("End Date set to: ", end_date)

i = 1
for ticker_raw in ticker_list:

  # time.sleep(1)
  missing_data_found = 0
  missing_data_index = ""
  ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase

  # Remove the "." from the ticker and replace by "-" as this is what Yahoo has
  if (ticker == "BRK.B"):
    ticker = "BRK-B"
  elif (ticker == "BF.B"):
    ticker = "BF-B"

  # ---------------------------------------------------------------------------
  # Sundeep : 09/27/2022 -
  # In order to limit the size of the Historical download, only get the
  # historical date that is slightly older than the earliest earnings date
  # available in the earnings file. Otherwise, the size of the historical download
  # balloons up and this not only increase the size of the historical download
  # csv, but it takes more machine time to run this script and the historical_merge
  # script as both of them iterate through all the rows (one-by-one) of downloaded data.
  #
  # For now, I am setting the start date to be
  # 1 years before the earliest date available in the earnings file
  # I just choose 1 years mostly as random, I could have chosen 2 year or 5 years
  # The only reason that I choose two years that the Yahoo Historical merge script
  # calculates 250 day moving average and so in order for that to work probably needs
  # 1 more year of historical date, if available, beyond the last earnings date
  #
  # Now in a few years the size of the historical data will start becoming an
  # issue again - especially for tickers that are old (IBM, WMT etc). In that
  # case there can be a few choices to get the size manageable :
  # 1. Rewrite this and the historical_merge script so that they are not doing
  #    row-by-row reading and writing of the historical data. That can cut down
  #    on the machine time, but not the size of the data but maybe that is good
  #    enough
  # 2. Across the suite of scripts (historical download, historical merge
  #    and earnings chart python, limit the scripts to use only 40 years
  #    (or 35 or 20) years of earnings data and also only download 40 years
  #    (or 35 or 20) years of historical data.
  #    If a longer chart is needed (like log chart), then the scripts can
  #    have a if statement that will download the more than 40 (or 35 or 20)
  #    years of both historical data and NOT curtail the earning data at the
  #    sametime.
  # We will decide on how to solve that problem, once we get there...
  # ---------------------------------------------------------------------------
  start_date = '01/01/1900'
  try:
    earnings_df = pd.read_csv(dir_path + "\\" + earnings_dir + "\\" + ticker + "_earnings.csv", delimiter=",")
    start_date = earnings_df['Q_Date'].tolist()[-1]
  except FileNotFoundError:
    print("")
    print("WARNING ***** WARNING ***** WARNING ***** WARNING *****")
    print("The earnings file for ticker : ", ticker, ", could not be located")
    print("However please check why earnings file could not be located, unless you are doing")
    print("this on purpose (like trying to download all SPY holdings etc")
    print("For now, I will use the default start date : ", start_date)
    print("WARNING ***** WARNING ***** WARNING ***** WARNING *****")
    print("")
    i=i+1

  # print ("The earnings file is ", earnings_df.to_string())
  # print("The Earliest date found in Earnings file " , start_date)
  # Convert the string to datetime, subtract 1 year
  start_date_dt = datetime.datetime.strptime(start_date, "%m/%d/%Y") - relativedelta(years=1)
  # and then convert datetime to string.
  # There should be a simpler way to convert from str to datetime to str but anyway...
  start_date = start_date_dt.strftime('%Y-%m-%d')
  # ---------------------------------------------------------------------------

  # left justify / left align
  print("Iteration no : ", f"{i : <3}", " : ", f"{ticker : <6}", " : Start Date ", f"{start_date : <10}")
  # yahoo_financials=YahooFinancials(ticker)
  try:
    historical_data = pdr.get_data_yahoo(ticker, start=start_date, end=end_date)
    # print("The data returned is : ", historical_data, "and the type is : ", type(historical_data))
    # # The type of data that is returned by the package is <dict>
    # historical_data=yahoo_financials.get_historical_price_data(start_date, end_date, 'daily')
    # print ("Historical Data retuned from package is ", historical_data)
    # # print ("Historical Data Type returned from the package is ", type(historical_data))
  except (ValueError):
    print ("Ticker ", ticker , "could not download data from Yahoo Financials")
    continue
  i=i+1


  # Reverse the dataframe
  historical_data_reversed = historical_data.reindex(index=historical_data.index[::-1])
  # print("The reversed dataframe is : ", historical_data_reversed)
  # Change the date format of the column date
  historical_data_reversed.reset_index(inplace=True)
  historical_data_reversed["Date"] = pd.to_datetime(historical_data_reversed["Date"]).dt.strftime('%m/%d/%Y')
  # print("The reversed dataframe with date format change : ", historical_data_reversed)
  # Change the mane of the column Adj Close to Adj_Close
  historical_data_reversed.rename({'Adj Close': 'Adj_Close'}, axis=1, inplace=True)
  historical_data_reversed.set_index('Date',inplace=True)
  # print("The reversed dataframe with date format change and column rename : ", historical_data_reversed)
  # Then write it to the file
  csvFile=yahoo_hist_out_dir + "\\" + ticker + "_yahoo_historical.csv"
  # print ("Now writing to ", csvFile)
  historical_data_reversed.to_csv(csvFile)

print("All  Done...")
# ##############################################################################



