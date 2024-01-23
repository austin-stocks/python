import requests
import pandas as pd
import os
import math
import json
import sys
import time
import socket
import re
import datetime as dt
import numpy as np
import calendar
import logging
import yfinance as yf

from dateutil.relativedelta import relativedelta
from matplotlib.offsetbox import AnchoredText

from SC_Global_functions import aaii_analysts_projection_file
from SC_Global_functions import aaii_missing_tickers_list

from SC_logger import my_print as my_print

dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
log_dir = "\\..\\..\\..\\Automation_Not_in_Git\\" + "Logs"

# ---------------------------------------------------------------------------
# Set Logging
# critical, error, warning, info, debug
# set up logging to file - see previous section for more details
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename=dir_path + log_dir + "\\" + 'SC_YahooTargetPrice_yfinance_debug.txt',
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
tracklist_file_full_path = dir_path + user_dir + "\\" + tracklist_file
tracklist_df = pd.read_csv(tracklist_file_full_path)

# Read the already existing json file that has the price targets
price_targets_json_dict_filename = "Price_Targets.json"
with open(dir_path + user_dir + "\\" + price_targets_json_dict_filename, 'r') as json_file:
  price_targets_json_dict = json.load(json_file)

ticker_list_unclean = tracklist_df['Tickers'].tolist()
ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']

targets = []
i_idx = 1
for ticker_raw in ticker_list:
  ticker = ticker_raw.replace(" ", "").upper()  # Remove all spaces from ticker_raw and convert to uppercase
  logging.debug(str(ticker) + " : Fetching Target Price")

  ticker_yf = yf.Ticker(ticker)
  logging.debug("Iteration : " + str(i_idx) + ", Ticker : " + str(ticker) + ", Ticker info : " + str(ticker_yf.info))
  # If you want the median version, then replace 'targetMeanPrice' with 'targetMedianPrice'
  try:
    target = ticker_yf.info['targetMeanPrice']
  except (KeyError):
    logging.info("Could not find target price for " + str(ticker))
    logging.info("skipping...")
    i_idx=i_idx+1
    continue
  logging.debug ("The target price is : " + str(target) +  " and the type is : " + str(type(target)))
  target_str = str(target)
  logging.info("Iteration : " + f"{str(i_idx) : <3}" + ", Ticker : " + f"{str(ticker) : <6}" + " : Price Target : " + f"{str(target) : <10}")
  targets.append(target_str)
  # sys.exit()
  # ---------------------------------------------------------------------------

  now = dt.datetime.now()
  date_time = now.strftime("%m/%d/%Y")
  logging.debug("Today's date is : " + str(date_time))

  # Extract all the things(data structures) in a (json file) dictionary
  # for the ticker and then deal with the ticker to add / substract the
  # price target information.
  # After adding/substracting is done, replace original dictionary in the
  # json file with the newly modified dictionary
  ticker_dict = {}
  logging.debug("json dict read from the json file : " + str(price_targets_json_dict))
  if (ticker in price_targets_json_dict.keys()):
    ticker_dict = price_targets_json_dict[ticker]
    logging.debug("Dictionary corresponding to : " + str(ticker) + " : " + str(ticker_dict))
    # Remove the ticker dictionary from the big json dictionary. We will add
    # the dictionary corresponding the the ticker later
    del price_targets_json_dict[ticker]
    ticker_dict["Price_Target"].append({"Date": date_time, "Target": target_str})
  else:
    logging.info("Did not find " + str(ticker) + " in the price target json...Will create an entry for it")
    ticker_dict["Price_Target"] = [{"Date": date_time, "Target": target_str}]
    logging.debug("Here is what I have for the ticker" + str(ticker_dict))

  # Now add the ticker dictionary back into big json dictionary
  price_targets_json_dict[ticker] = ticker_dict
  price_targets_json_dict_beautify = json.dumps(price_targets_json_dict, indent=2)
  logging.debug("Here is now to original dict now looks" + str(price_targets_json_dict_beautify))

  with open(dir_path + user_dir + "\\" + price_targets_json_dict_filename, 'w') as f:
    json.dump(price_targets_json_dict, f, indent=2)

  i_idx = i_idx+1
