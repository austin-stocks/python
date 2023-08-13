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
from   datetime import date
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import calendar
import logging

from collections import Counter
from dateutil.relativedelta import relativedelta
from matplotlib.offsetbox import AnchoredText

import SC_Global_functions as sc_funcs

from SC_logger import my_print as my_print
from yahoofinancials import YahooFinancials
from mpl_finance import candlestick_ohlc
from pandas.plotting import register_matplotlib_converters

register_matplotlib_converters()



dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
log_dir = "\\..\\" + "Logs"
# ---------------------------------------------------------------------------
# Set Logging
# critical, error, warning, info, debug
# set up logging to file - see previous section for more details
logging.basicConfig(# This decides what level of messages get printed in the debug file
                    # level=logging.DEBUG,
                    level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename=dir_path + log_dir + "\\" + 'SC_Create_Links_And_More_debug.txt',
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
# ---------------------------------------------------------------------------


tracklist_file = "Tracklist.csv"
master_tracklist_file = "Master_Tracklist.xlsm"
tracklist_file_full_path = dir_path + user_dir + "\\" + tracklist_file
tracklist_df = pd.read_csv(tracklist_file_full_path)
master_tracklist_df = pd.read_excel(dir_path + user_dir + "\\" + master_tracklist_file, sheet_name="Main")
master_tracklist_df = pd.read_excel(dir_path + user_dir + "\\" + master_tracklist_file, sheet_name="Main")
master_tracklist_ticker_list = master_tracklist_df['Tickers'].tolist()

# print ("The Tracklist df is", tracklist_df)
ticker_list_unclean = tracklist_df['Tickers'].tolist()
ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']

links_and_more_df = pd.DataFrame(columns=['Tickers'])

# links_and_more_df.set_index('Tickers', inplace=True)
# links_and_more_df.insert(1, "SChart", " ")  # Stockcharts
# links_and_more_df.insert(1, "TD", " ")  # TD Ameritrade
# links_and_more_df.insert(1, "CNBC", " ")  # CNBC
# links_and_more_df.insert(1, "Y-Profile", " ")  # Yahoo Finance Profile
# links_and_more_df.insert(1, "Y-BS", " ")  # Yahoo Finance Balance Sheet
# links_and_more_df.insert(1, "SPI", " ")  # Profitspy
# links_and_more_df.insert(1, "AAII", " ")  # AAII

# #############################################################################
#                   MAIN LOOP FOR TICKERS
# #############################################################################
# ticker_list = ['IBM']
i_itr = 1
for ticker_raw in ticker_list:
  master_tracklist_ticker_list
  ticker = ticker_raw.replace(" ", "").upper()  # Remove all spaces from ticker_raw and convert to uppercase
  # logging.info("========================================================")
  logging.info("Iteration : " + str(i_itr) + ", Ticker : " + ticker)
  # logging.info("========================================================")

  i_itr = i_itr+1

  links_and_more_df.loc[ticker, 'Tickers'] = ticker
  if (ticker in master_tracklist_ticker_list):
    links_and_more_df.loc[ticker, 'In Master'] = 1
  else:
    links_and_more_df.loc[ticker, 'In Master'] = 0

  links_and_more_df.loc[ticker, 'SChart'] = 'https://stockcharts.com/h-sc/ui?s='+str(ticker)
  links_and_more_df.loc[ticker, 'TD'] = 'https://research.tdameritrade.com/grid/public/research/stocks/earnings?period=qtr&section=0&symbol=' + str(ticker)
  links_and_more_df.loc[ticker, 'CNBC'] = 'https://www.cnbc.com/quotes/' + str(ticker) +'?tab=earnings'
  links_and_more_df.loc[ticker, 'Y-Profile'] = 'https://finance.yahoo.com/quote/' + str(ticker)
  links_and_more_df.loc[ticker, 'Y-BS'] = 'https://finance.yahoo.com/quote/' + str(ticker) + "/balance-sheet"
  links_and_more_df.loc[ticker, 'SPI'] = 'https://www.profitspi.com/stock/view.aspx?v=stock-chart&uv=269665&p=' + str(ticker)
  links_and_more_df.loc[ticker, 'AAII'] = 'https://www.aaii.com/stock/ticker/' + str(ticker)

links_and_more_df.reset_index()
links_and_more_df.set_index('Tickers', inplace=True)


now = dt.datetime.now()
date_time = now.strftime("%Y-%m-%d")
Create_Links_And_More_logfile= date_time + "-Tickers_With_Links_And_More.xlsx"
writer = pd.ExcelWriter(dir_path + log_dir + "\\" + Create_Links_And_More_logfile, engine='xlsxwriter')
# links_and_more_df.sort_values(by=['RS Rating','# of Funds - last reported qrtr','Price*Volume'], ascending=[False,False,False]).to_excel(writer)
links_and_more_df.to_excel(writer)
logging.info("")
logging.info("Created : " + str(dir_path + log_dir + "\\" + Create_Links_And_More_logfile) + " <-- Tickers with various Links")
writer.save()


