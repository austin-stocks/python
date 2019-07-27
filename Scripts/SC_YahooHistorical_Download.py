# ##############################################################################
# Download the historical data into individual csv
# ##############################################################################

import csv
import datetime
import openpyxl
import os
import xlrd

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
yahoo_hist_out_dir = dir_path + "\\..\\Download\\YahooHistorical"

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

'''
# This works. I am removing this so that we can use a csv version of Tracklist file
df = pd.DataFrame()
df = pd.read_excel(tracklist_file_full_path, sheet_name="alphabetical", usecols="B")
print ("Read the Tracklist")
# print (df)

# The first row is the colunmn head in Dataframe
first_row = df.columns.values.tolist()
print ("First row is ", first_row)

rest_list = [item for sublist in df[first_row].values for item in sublist]
print ("Flat list is ",rest_list)

# Now push that name into ticker_list
ticker_list = []
ticker_list = first_row+rest_list
print ("Ticker List is ", ticker_list)
print ('The number of ticker in the list are ', len(ticker_list))
'''

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
  for x in reversed(range(1, len(historical_data[ticker]['prices']))):

    # Check and warn if the number of columns in date do not match in adjusted close
    # data_list = historical_data['Tickers'].tolist()

    # Create the List to be written into csv file row
    price_list = []

    # Get the date in the format that we need
    # the function returns in the order yyyy-mm-dd and we need in dd/mm/yyyy
    if (type(historical_data[ticker]['prices'][x]['formatted_date']) == type(None)) :
      print ("The data at index ",x ," is missing for ", ticker)
      # Need to think about if we need to continue here.
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
      missing_data_index = x
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
    text = colored('Warning: Missing data found in Yahoo Download - Either in Price or Volume for ' + ticker + ' at index ' + str(missing_data_index), 'red',attrs=['reverse', 'blink'])
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

print("Done")
# ##############################################################################



