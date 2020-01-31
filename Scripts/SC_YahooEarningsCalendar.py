# ##############################################################################
# Download the historical data into individual csv
# ##############################################################################

import csv
import datetime as dt
import openpyxl
import os
import xlrd
from yahoo_earnings_calendar import YahooEarningsCalendar

import pandas as pd
from yahoofinancials import YahooFinancials
# ##############################################################################


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

yec = YahooEarningsCalendar()
yahoo_earnings_calendar_df = pd.DataFrame(columns=['Ticker','Earnings_Date'])
yahoo_earnings_calendar_df.set_index('Ticker', inplace=True)

i_int = 0
for ticker_raw in ticker_list:
  ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase
  i_int += 1
  print("\nIteration :", i_int, "Processing : ", ticker)

  ticker_is_wheat = master_tracklist_df.loc[ticker, 'Quality_of_Stock']
  if (ticker_is_wheat != 'Wheat') and (ticker_is_wheat != 'Essential'):
    print (ticker , " is not Wheat or Essential...skipping")
    continue

  # Returns the next earnings date of BOX in Unix timestamp
  try:
    unixtimestamp = yec.get_next_earnings_date(ticker)
  except:
    print ("Could not download Earnings date for ", ticker)
    yahoo_earnings_calendar_df.loc[ticker] = '#NA#'
    continue

  # ticker_next_earnings_date_str = dt.datetime.fromtimestamp(unixtimestamp).strftime('%m/%d/%Y')
  # ticker_next_earnings_date_dt = dt.datetime.strptime(ticker_next_earnings_date_str, '%m/%d/%Y').date()
  ticker_next_earnings_date_dt = dt.datetime.fromtimestamp(unixtimestamp).date()
  ticker_next_earnings_date_str = dt.datetime.strftime(ticker_next_earnings_date_dt, '%m/%d/%Y')
  if (ticker_next_earnings_date_dt < dt.date.today() ):
    print ("The earnings data for ", ticker, "is ", ticker_next_earnings_date_str, "and is older than today's date...")
    yahoo_earnings_calendar_df.loc[ticker] = [ticker_next_earnings_date_str]
  else:
    print ("Next earnings date for", ticker,"is", ticker_next_earnings_date_str)
    yahoo_earnings_calendar_df.loc[ticker] = [ticker_next_earnings_date_str]

  # if (i_int == 10):
  #   break


yahoo_earnings_calendar_df.sort_values(by='Earnings_Date', ascending=[True]).to_csv('Wheat_yahoo_earnings_calendar.csv',sep=',', index=True, header=True)
print("Done")

# This works
'''
date_from = datetime.datetime.strptime(
    'Jan 31 2020  10:00AM', '%b %d %Y %I:%M%p')
date_to = datetime.datetime.strptime(
    'Feb 8 2020  1:00PM', '%b %d %Y %I:%M%p')
print(yec.earnings_between(date_from, date_to))
[
{'ticker': 'PSX', 'companyshortname': 'Phillips 66', 'startdatetime': '2020-01-31T18:30:00.000Z', 'startdatetimetype': 'BMO', 'epsestimate': 1.56, 'epsactual': None, 'epssurprisepct': None, 'gmtOffsetMilliSeconds': 0, 'quoteType': 'EQUITY'}, 
{'ticker': 'PSXP', 'companyshortname': 'Phillips 66 Partners LP', 'startdatetime': '2020-01-31T18:30:00.000Z', 'startdatetimetype': 'BMO', 'epsestimate': 0.96, 'epsactual': None, 'epssurprisepct': None, 'gmtOffsetMilliSeconds': 0, 'quoteType': 'EQUITY'}, 
]
'''

# ##############################################################################



