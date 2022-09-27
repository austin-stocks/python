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
from yahoofinancials import YahooFinancials
from termcolor import colored, cprint
from dateutil.relativedelta import relativedelta

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
  # In order to limit the size of the Historical download only get the
  # historical date that is slightly older than the earliest earnings date
  # available in the earnings file. Othewise, the size of the historical download
  # balloon up and this not only increase the size of the historical download
  # csv but it take more machine time to run this script and the historical_merge
  # script as both of them iterate through all the rows of downloaded data.
  #
  # For now I am setting the start date to be
  # 1 years before the earliest date availabe in the earnings file
  # I just choose 1 years mostly as random, I could have choosen 2 year or 5 years
  # The only reason that I choose two years that the Yahoo Historical merge script
  # calculates 250 day moving average and so in order for that to work probably needs
  # 1 more year of historical date, if available, beyond the last earnings date
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

  # print("The Earliest date found in Earnings file " , start_date)
  # Convert the string to datetime, substract 1 year
  start_date_dt = datetime.datetime.strptime(start_date, "%m/%d/%Y") - relativedelta(years=1)
  # and then convert datetime to string.
  # There should be a simpler way to convert from str to datetime to str but anyway...
  start_date = start_date_dt.strftime('%Y-%m-%d')
  # ---------------------------------------------------------------------------

  # left justify / left align
  print("Iteration no : ", f"{i : <3}", " :  ", f"{ticker : <6}", " : Start Date ", f"{start_date : <10}")
  yahoo_financials=YahooFinancials(ticker)
  try:
    # The type of data that is returned by the package is <dict>
    historical_data=yahoo_financials.get_historical_price_data(start_date, end_date, 'daily')
    # print ("Historical Data retuned from package is ", historical_data)
    # print ("Historical Data Type returned from the package is ", type(historical_data))
  except (ValueError):
    print ("Ticker ", ticker , "could not download data from Yahoo Financials")
    continue


  csvFile=open(yahoo_hist_out_dir + "\\" + ticker + "_yahoo_historical.csv", 'w+', newline='')
  writer = csv.writer(csvFile)

  # Put the Header Row in the csv
  writer.writerow(["Date", "Open", "High", "Low", "Close", "Adj_Close", "Volume"])

  # The package function above provides the historical information in the list 'prices'
  # in the order from oldest -> lastest, so, Iterate over the list in reversed order
  total_historical_rows = len(historical_data[ticker]['prices'])
  for x in reversed(range(1, len(historical_data[ticker]['prices']))):

    # Check and warn if the number of columns in date do not match in adjusted close
    # data_list = historical_data['Tickers'].tolist()

    # Create the List to be written into csv file row
    price_list = []

    # Get the date in the format that we need
    if (type(historical_data[ticker]['prices'][x]['formatted_date']) == type(None)) :
      print("ERROR : The date at index ", x ," is missing for ", ticker)
      # Need to think about if we need to continue here. because if the
      # date is missing then what is the point in contuining
      sys.exit(1)

    # the function returns in the order yyyy-mm-dd and we need in dd/mm/yyyy
    date_str = ""
    date_str = historical_data[ticker]['prices'][x]['formatted_date'][5:7]
    date_str = date_str + "/" + historical_data[ticker]['prices'][x]['formatted_date'][8:10]
    date_str = date_str + "/" + historical_data[ticker]['prices'][x]['formatted_date'][0:4]

    # Now get the other fields from the list 'prices' and print them in the csv
    price_list.insert(0, date_str)
    price_list.insert(1, historical_data[ticker]['prices'][x]['open'])
    price_list.insert(2, historical_data[ticker]['prices'][x]['high'])
    price_list.insert(3, historical_data[ticker]['prices'][x]['low'])
    price_list.insert(4, historical_data[ticker]['prices'][x]['close'])
    price_list.insert(5, historical_data[ticker]['prices'][x]['adjclose'])
    price_list.insert(6, historical_data[ticker]['prices'][x]['volume'])
    #print(price_list)
    if (  (type(historical_data[ticker]['prices'][x]['open']) == type(None)) or \
          (type(historical_data[ticker]['prices'][x]['high']) == type(None)) or \
          (type(historical_data[ticker]['prices'][x]['low']) == type(None)) or \
          (type(historical_data[ticker]['prices'][x]['close']) == type(None)) or \
          (type(historical_data[ticker]['prices'][x]['adjclose']) == type(None)) or \
          (type(historical_data[ticker]['prices'][x]['volume']) == type(None))):
      # print ("Missing data found\n")
      missing_data_found = 1
      missing_data_index = total_historical_rows-x-1
      date_str_for_missing_data = date_str
      # text = colored('Warning: Missing data found in Yahoo Download - Either in Price or Volume for date: ' + date_str, 'red', attrs=['reverse', 'blink'])
      # print (text)

    writer.writerow(price_list)

  csvFile.close()
  # For now break after 10
  # if i == 3:
  #   break
  i = i + 1
  if (missing_data_found == 1):
    # Sundeep is here...need to find out what to report/how to report and then maybe do a missing panda data to
    # populate the entire data
    text = colored('Warning: Missing data found in Yahoo Download, for date : ' + date_str_for_missing_data +' - Either in Price or Volume for ' + ticker + ' at index ' + str(missing_data_index),
                   'red',attrs=['reverse', 'blink'])
    print (text)


  # Get the dividend data here
  # print(yahoo_financials.get_daily_dividend_data(start_date, end_date))
  # start_date = '1987-09-15'
  # end_date = '1988-09-15'
  # yahoo_financials = YahooFinancials(['AAPL', 'WFC'])
  # print(yahoo_financials.get_daily_dividend_data(start_date, end_date))
  # {
  #     "AAPL": [
  #         {
  #             "date": 564157800,
  #             "formatted_date": "1987-11-17",
  #             "amount": 0.08
  #         },
  #         {
  #             "date": 571674600,
  #             "formatted_date": "1988-02-12",
  #             "amount": 0.08
  #         },
  #         {
  #             "date": 579792600,
  #             "formatted_date": "1988-05-16",
  #             "amount": 0.08
  #         },
  #         {
  #             "date": 587655000,
  #             "formatted_date": "1988-08-15",
  #             "amount": 0.08
  #         }
  #     ],

print("All  Done...")
# ##############################################################################



