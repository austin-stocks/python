# ##############################################################################
# Download the historical data into individual csv
# ##############################################################################

import csv
import datetime
import openpyxl
import os
import xlrd
import datetime as dt
import time
import pandas as pd
from yahoofinancials import YahooFinancials
from termcolor import colored, cprint
# ##############################################################################

# =============================================================================
# Define the various File names and Directory Paths to be used and set the
# start and end dates
# =============================================================================
dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
tracklist_file = "Tracklist.csv"
tracklist_file_full_path = dir_path + user_dir + "\\" + tracklist_file
dividend_out_dir = dir_path + "\\..\\Dividend"

start_date = '1900-01-01'
# end_date_raw = str(datetime.datetime.now().year) + \
#        "-" + str(datetime.datetime.now().month) + \
#        "-" + str(datetime.datetime.now().day)
end_date_raw = datetime.datetime.today() + datetime.timedelta(days=1)
end_date = end_date_raw.strftime('%Y-%m-%d')
# end_date = '2015-08-15'
print ("Start Date set to: ", start_date, ", End Date set to: ", end_date)
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
  # Read the trracklist and convert the read tickers into a list
  tracklist_df = pd.read_csv(tracklist_file_full_path)
  # print ("The Tracklist df is", tracklist_df)
  ticker_list_unclean = tracklist_df['Tickers'].tolist()
  ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']

# =============================================================================


# =============================================================================
#  for each ticker in ticker_list
# 1. Get the historical data from Yahoo
# 2. Extract the relevant data in the format that we want
# 2. Write that data in csv
# =============================================================================
i = 1
for ticker_raw in ticker_list:
  # time.sleep(7)
  missing_data_found = 0
  missing_data_index = ""
  ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase

  # Remove the "." from the ticker and replace by "-" as this is what Yahoo has
  if (ticker == "BRK.B"):
    ticker = "BRK-B"
  elif (ticker == "BF.B"):
    ticker = "BF-B"

  print("Iteration no : ", i , " ", ticker)
  yahoo_financials=YahooFinancials(ticker)
  try:
    # The type of data that is returned by the package is <dict>
    # which is a list of dictionaries
    dividend_data = yahoo_financials.get_daily_dividend_data(start_date, end_date)
    # print("Dividend Data : ",dividend_data)
    # print("Dividend Data : ",type(dividend_data))
  except (ValueError):
    print ("Ticker ", ticker , "could not download data from Yahoo Dividend...you may have wrong ticker")
    continue


  # print("Length of the dictionary is : ", len(dividend_data))
  # print("Length of the dictionary is : ", dividend_data[ticker])
  i = i+1
  if ((dividend_data[ticker]) is None):
    print ("Ticker ", ticker , "returned empty dictionary for dividends...skipping")
    continue
  # ===========================================================================
  # # This works when you have to iterated over a list of dictionaries.
  # for index in range(len(dividend_data[ticker])):
  #   for key in dividend_data[ticker][index]:
  #     print("Key : ", key, " Data : ", dividend_data[ticker][index][key])
  # ===========================================================================
  csv_2write_dividend_df = pd.DataFrame()
  date_list = list()
  dividend_amount_list = list()
  for index in reversed(range(len(dividend_data[ticker]))):
    # print("Index : ", index, " Date : ", dividend_data[ticker][index]['formatted_date'], " Dividend Amount ", dividend_data[ticker][index]['amount'])
    # Very useful function
    # datetime.datetime.strptime(date_string, format1).strftime(format2)
    date_new_format = dt.datetime.strptime( dividend_data[ticker][index]['formatted_date'], '%Y-%m-%d').strftime('%m/%d/%Y')
    date_list.append(date_new_format)
    dividend_amount_list.append(dividend_data[ticker][index]['amount'])

  # This works too - but th next line is simpler to understand to make columns with lists
  # csv_2write_dividend_df=pd.DataFrame(list(zip(date_list,dividend_amount_list)),columns=['Date', 'Amount'])
  csv_2write_dividend_df=pd.DataFrame({'Date': date_list, 'Amount': dividend_amount_list})
  csv_2write_dividend_df.set_index('Date', inplace=True)

  # print ("The dataframe is : ", csv_2write_dividend_df.head())
  csv_2write_dividend_df.to_csv(dividend_out_dir + "\\" + ticker + "_dividend.csv")

