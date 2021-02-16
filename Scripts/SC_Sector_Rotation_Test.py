
import yfinance as yf
import pandas as pd
import matplotlib
import os
import math
import json
import sys
import time
import socket
import re
import datetime as dt
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import calendar
import logging

from dateutil.relativedelta import relativedelta
from matplotlib.offsetbox import AnchoredText

from SC_Global_functions import aaii_analysts_projection_file
from SC_Global_functions import aaii_missing_tickers_list

from SC_logger import my_print as my_print
from yahoofinancials import YahooFinancials
from mpl_finance import candlestick_ohlc
from pandas.plotting import register_matplotlib_converters

register_matplotlib_converters()

def human_format(num, precision=2, suffixes=['', 'K', 'M', 'B', 'T', 'P']):
  m = sum([abs(num / 1000.0 ** x) >= 1 for x in range(1, len(suffixes))])
  return f'{num / 1000.0 ** m:.{precision}f} {suffixes[m]}'


dir_path = os.getcwd()
log_dir = "\\..\\" + "Logs"
user_dir = "\\..\\" + "User_Files"

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
                    filename=dir_path + log_dir + "\\" + 'SC_Sector_Rotation_Test_debug.txt',
                    filemode='w')
# define a Handler which writes INFO messages or higher to the sys.stderr
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
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

all_sectors_input_data_file = "Sector_Rotation_Tracking.xlsm"


ticker_list = ['XLB','XLC','XLE','XLF','XLI','XLK', 'XLP','XLRE','XLU','XLV','XLY']

# https://www.cnbc.com/sector-etfs/
# https://etfdb.com/etfs/


test_start_date = "06/15/2020"
test_stop_date = "01/15/2021"
no_of_days_to_look_back = 30
rebalance_interval = 15
no_of_holdings = 2
initial_to_invest = 10000

test_start_date_dt = dt.datetime.strptime(test_start_date, '%m/%d/%Y').date()
test_stop_date_dt = dt.datetime.strptime(test_stop_date, '%m/%d/%Y').date()




# -----------------------------------------------------------------------------
# Read the input file and create historical dataframe that has dates and
# columns corresponding to the adj close price for each ticker 
# -----------------------------------------------------------------------------
start = time.process_time()
historical_df = pd.DataFrame(columns=['Date'])
for ticker in ticker_list :
  logging.debug("Reading the historical data for : " + ticker)
  all_sectors_input_df = pd.read_excel(dir_path + user_dir + "\\" + all_sectors_input_data_file, sheet_name=ticker)
  # Get the date column
  date_timestamp_list = all_sectors_input_df['Date'].dropna().tolist()
  date_str_list = [d.strftime('%m-%d-%Y') for d in date_timestamp_list]
  date_list = [dt.datetime.strptime(date, '%m-%d-%Y').date() for date in date_str_list]
  # Get the adj_close column
  adj_close_list = all_sectors_input_df['Adj_Close'].dropna().tolist()
  # logging.debug("The date list is " + str(date_str_list))
  historical_df['Date'] = date_list
  historical_df[ticker] = adj_close_list

historical_df.set_index('Date', inplace=True)
logging.debug("The historical dataframe with Adj Close price \n" + historical_df.to_string())
logging.info ("The reading of Tracklist files took around " + str(time.process_time() - start) + " seconds")
# -----------------------------------------------------------------------------



# -----------------------------------------------------------------------------
# Now get the start and stop dates for each iteration and find out the 
# -----------------------------------------------------------------------------

# Calculate the number of interations that need to be done based on start,
# stop dates and the rebalance interval
no_of_iterations = int((test_stop_date_dt - test_start_date_dt).days/rebalance_interval)
logging.debug("Test Start Date : " + str(test_start_date_dt) + ", Test Stop Date : " + str(test_stop_date_dt) + ", Rebalance Interval : " + str(rebalance_interval))
logging.debug("Number of Days between Test Start and Test Stop dates : " + str((test_stop_date_dt - test_start_date_dt).days))
logging.debug("The number of iterations that will be done are : " + str(no_of_iterations))

date_list_dt = historical_df.index.values
start_date_dt = test_start_date_dt
curr_holdings_df = pd.DataFrame(columns=['Date','Ticker', 'no_of_shares', 'Price_purchased'])
curr_holdings_df.set_index('Ticker', inplace=True)

for i_idx in range(no_of_iterations):
  logging.debug("===============================================================")
  logging.debug("Iteration : " + str(i_idx))
  logging.debug("===============================================================")
  ticker_returns_df = pd.DataFrame(columns=['Ticker','look_back_date','start_date','look_back_price','start_price','Returns'])
  ticker_returns_df.set_index('Ticker', inplace=True)
  ticker_dict = {}
  for ticker in ticker_list :
    start_date_match_historical_dt = min(date_list_dt, key=lambda d: abs(d - start_date_dt))
    look_back_date_dt = start_date_match_historical_dt - dt.timedelta(days=no_of_days_to_look_back)
    look_back_date_match_historical_dt = min(date_list_dt, key=lambda d: abs(d - look_back_date_dt))

    start_price = historical_df.loc[start_date_match_historical_dt,ticker]
    look_back_price = historical_df.loc[look_back_date_match_historical_dt,ticker]
    price_change = (start_price/look_back_price)-1
    logging.debug("Ticker : " + str(ticker) \
                  + ", Look Back Date : " + str(look_back_date_match_historical_dt) \
                  + ", Start Date : " + str(start_date_match_historical_dt) \
                  + ", Look Back Price : " + str(look_back_price)
                  + ", Start Price : " + str(start_price)
                  + ", Price Change(%) : " + str(round((price_change*100),2)))
    ticker_dict[ticker] = {}
    ticker_dict[ticker]['start_date'] = start_date_match_historical_dt
    ticker_dict[ticker]['look_back_date'] = look_back_date_match_historical_dt
    ticker_dict[ticker]['start_price'] = start_price
    ticker_dict[ticker]['look_back_price'] = look_back_price
    ticker_dict[ticker]['price_change'] = price_change

    ticker_returns_df.loc[ticker,'look_back_date'] = look_back_date_match_historical_dt
    ticker_returns_df.loc[ticker,'start_date'] = start_date_match_historical_dt
    ticker_returns_df.loc[ticker,'look_back_price'] = look_back_price
    ticker_returns_df.loc[ticker,'start_price'] = start_price
    ticker_returns_df.loc[ticker,'Returns'] = price_change*100

  # Sort the returns DF by Returns
  ticker_returns_df.sort_values(by=['Returns'], ascending=[False],inplace=True)
  ticker_to_buy_curtailed_df = ticker_returns_df.iloc[:no_of_holdings]
  logging.debug("----------------------------------------")
  logging.debug("Based on " + str(no_of_days_to_look_back) + " days returns, the tickers that qualified to be bought are : ")
  logging.debug("----------------------------------------")
  # logging.debug("The curtailed df is \n" + ticker_to_buy_curtailed_df.to_string())
  for i_index, row in ticker_to_buy_curtailed_df.iterrows():
    # logging.debug("Index : " + str(i_index) + ", Row : " + str(row['Returns']))
    logging.debug("Ticker : " + str(i_index) \
                + ", Look Back Date : " + str(row['look_back_date']) \
                + ", Start Date " + str(row['start_date']) \
                + ", Returns " + str(round(row['Returns'],2)))
  logging.debug("----------------------------------------")

  # -------------------------------------------------------
  # First sell all the holdings and get the total dollars out
  # to be able to buy in the next step
  # -------------------------------------------------------
  if (i_idx == 0):
    curr_value = initial_to_invest
  else:
    curr_value=0
    logging.debug("----------------------------------------")
    logging.debug("Selling the current holdings before buying")
    for i_index, row in curr_holdings_df.iterrows():
      curr_value=curr_value + ticker_returns_df.loc[i_index,'start_price']*curr_holdings_df.loc[i_index,'no_of_shares']
      logging.debug("Selling : " + str(i_index) \
                    + ", No of Shares : " + str( round(curr_holdings_df.loc[i_index,'no_of_shares'],2)) \
                    + ", Purchase price : " + str(curr_holdings_df.loc[i_index,'Price_purchased']) \
                    + ", Selling price : " + str(ticker_returns_df.loc[i_index,'start_price']) \
                    + ", Gain/Loss for this period : " + str(round((((ticker_returns_df.loc[i_index,'start_price']/curr_holdings_df.loc[i_index,'Price_purchased'])-1)*100),2)) + " %" \
                    + ", Getting net proceeds : " + str(ticker_returns_df.loc[i_index,'start_price']*curr_holdings_df.loc[i_index,'no_of_shares']))
    logging.debug("The curr. value after selling the holdings : " + str(curr_value))
    logging.debug("Total Returns till  : " + str(start_date_match_historical_dt) + ", : " + str(((curr_value/initial_to_invest) - 1)*100) + " %")
    logging.debug("----------------------------------------")
  # -------------------------------------------------------

  # -------------------------------------------------------
  # Now make fresh buys
  # -------------------------------------------------------
  curr_holdings_df = pd.DataFrame(columns=['Date', 'Ticker', 'no_of_shares', 'Price_purchased'])
  curr_holdings_df.set_index('Ticker', inplace=True)
  logging.debug("----------------------------------------")
  logging.debug("Now buying the new tickers that qualified")
  for i_index, row in ticker_to_buy_curtailed_df.iterrows():
    curr_holdings_df.loc[i_index,'Date'] = row['start_date']
    curr_holdings_df.loc[i_index,'no_of_shares'] = (curr_value*.5)/row['start_price']
    curr_holdings_df.loc[i_index, 'Price_purchased'] = row['start_price']
    logging.debug("Bought : " + str(i_index) + ", Purchase Price : " + str(row['start_price']) + ", No of Shares : " + str(round((curr_value*.5/row['start_price']),2)))
  logging.debug("----------------------------------------")
  # logging.debug("The Current holdings df : \n" + curr_holdings_df.to_string())
  # -------------------------------------------------------

  start_date_dt = start_date_dt + dt.timedelta(days=rebalance_interval)
# -----------------------------------------------------------------------------


