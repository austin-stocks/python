# %matplotlib inline

import matplotlib.pyplot as plt
import pandas as pd
from talib import RSI, BBANDS, MACD
import logging
import sys
import os

# -----------------------------------------------------------------------------
# Read the master tracklist file into a dataframe
# -----------------------------------------------------------------------------
dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
log_dir = "\\..\\" + "Logs"
historical_dir = "\\..\\" + "Historical"
Yahoo_historical_download_dir = "\\..\\" + "Download\YahooHistorical"
Back_Testing_dir = "\\..\\" + "Back_Testing"
tracklist_file = "Tracklist.csv"
tracklist_file_full_path = dir_path + user_dir + "\\" + tracklist_file

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
                    filename=dir_path + log_dir + "\\" + 'SC_PyQuant_debug.txt',
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

# from openbb_terminal.sdk import openbb
# from openbb_terminal.sdk import TerminalStyle
# theme = TerminalStyle("light", "light", "light")


tracklist_df = pd.read_csv(tracklist_file_full_path)
# print ("The Tracklist df is", tracklist_df)
tracklist_df.sort_values('Tickers', inplace=True)
ticker_list_unclean = tracklist_df['Tickers'].tolist()
ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']

# ticker_list = ['PLUS','AUDC', 'MED', 'IBM']
ticker_list = ['AAPL']
i_int = 1
for ticker_raw in ticker_list:
  ticker = ticker_raw.replace(" ", "").upper()  # Remove all spaces from ticker_raw and convert to uppercase
  historical_df = pd.read_csv(dir_path + Yahoo_historical_download_dir + "\\" + ticker + "_yahoo_historical.csv")
  # logging.debug("The Historical Dataframe is : \n" + historical_df.to_string())

  # data = (
  #     openbb
  #     .stocks
  #     .load("AAPL", start_date="2020-01-01")
  #     .rename(columns={"Adj Close": "close"})
  # )

  historical_df_reversed = historical_df.loc[::-1].reset_index(drop=True).tail(300)
  logging.debug("The Historical Prices are : " + str(historical_df_reversed.Adj_Close))
  # Create Bollinger Bands
  up, mid, low = BBANDS(historical_df_reversed.Adj_Close, timeperiod=21, nbdevup=2, nbdevdn=2, matype=0)

  # Create RSI
  rsi = RSI(historical_df_reversed.Adj_Close, timeperiod=14)

  # Create MACD
  macd, macdsignal, macdhist = MACD(historical_df_reversed.Adj_Close,fastperiod=12,slowperiod=26,signalperiod=9)
  logging.info("The MACD Stuff is " + str(macd))

  # Depending on the indicator, the function takes different values. BBANDS takes the closing price,
  # the lookback window, and the number of standard deviations. RSI just takes the lookback window,
  # and MACD takes the fast, slow, and signal periods.
  macd = pd.DataFrame( {"MACD": macd,"MACD Signal": macdsignal,"MACD History": macdhist,} )
  data = pd.DataFrame( {"AAPL": historical_df_reversed.Adj_Close,"BB Up": up,"BB Mid": mid,"BB down": low,"RSI": rsi, }  )


  fig, axes = plt.subplots( nrows=3,figsize=(15, 10), sharex=True )

  data.drop(["RSI"], axis=1).plot( ax=axes[0], lw=1, title="BBANDS" )
  data["RSI"].plot( ax=axes[1], lw=1, title="RSI"  )
  axes[1].axhline(70, lw=1, ls="--", c="k")
  axes[1].axhline(30, lw=1, ls="--", c="k")

  macd.plot( ax=axes[2], lw=1, title="MACD", rot=0 )
  axes[2].set_xlabel("")

  fig.tight_layout()
  plt.show()