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
from mplfinance.original_flavor import candlestick_ohlc
from pandas.plotting import register_matplotlib_converters

register_matplotlib_converters()


# =============================================================================
# User defined functions
# =============================================================================

# -----------------------------------------------------------------------------
# Returns big numbers in K, M(illion), B(ilion) etc
# -----------------------------------------------------------------------------
def human_format(num, precision=2, suffixes=['', 'K', 'M', 'B', 'T', 'P']):
  m = sum([abs(num / 1000.0 ** x) >= 1 for x in range(1, len(suffixes))])
  return f'{num / 1000.0 ** m:.{precision}f}{suffixes[m]}'


# -----------------------------------------------------------------------------
# Returns growth between the current and previous number
# ----------|-----------|------------------------------------------|
# Previous  |  Current  |  Notes                                   |
# ----------|-----------|------------------------------------------|
#    +      |     +     | Meaningful. Can be positive or negative  |
# ----------|-----------|------------------------------------------|
#    +      |     -     | Meaningful. Will always be negative      |
# ----------|-----------|------------------------------------------|
#    -      |     +     | Earnings are improving...maybe meaningful|
# ----------|-----------|------------------------------------------|
#    -      |     -     | If current > previous - Improving        |
#           |           | If current < previous - Deteriorating    |
# ----------|-----------|------------------------------------------|
# -----------------------------------------------------------------------------
def get_growth(current, previous):
  if (previous == 0):
    return "Div#0#"
  elif current == previous:
    return 0
  elif (previous > 0):  # Covers case 1 and 2
    return round(((current - previous) / previous) * 100.0, 2)
  elif (previous < 0) and (current > 0):  # Case 3
    # This has very little meaning but still will give sone indication to
    # the user that the growth has been on positive tragectory
    return round(((current - previous) / previous) * 100.0, 2) * (-1)
  elif (previous < 0) and (current < 0):  # Case 3
    if (current > previous):  # Case 4a
      return "Improving"
    else:  # Case 4a
      return "Deteriorating"

  # return float('inf')


# -----------------------------------------------------------------------------
# This function takes in a list that has nan in between numeric values and
# replaces the nan in the middle with a step so that the 'markers' can be
#  converted to a line while plotting
# -----------------------------------------------------------------------------
def smooth_list(l):
  i_int = 0
  l_mod = l.copy()
  l_clean = []
  l_indices = []

  while (i_int < len(l) - 1):
    if (str(l_mod[i_int]) != 'nan'):
      l_clean.append(l[i_int])
      l_indices.append(i_int)

    i_int += 1

  # print("The original List is ", l)
  # print("The clean List is ", l_clean)
  # print("The indices of non non values is ", l_indices)

  i_int = 0
  while (i_int < len(l_clean) - 1):
    # print("Clean List index:", i_int, ", Clean List value:", l_clean[i_int], ", Corresponding List index:",
    #       l_indices[i_int])
    step = (l_clean[i_int] - l_clean[i_int + 1]) / (l_indices[i_int + 1] - l_indices[i_int])
    start_index = l_indices[i_int]
    stop_index = l_indices[i_int + 1]
    # print("The step is ", step, "Start and Stop Indices are ", start_index, stop_index)
    j_int = start_index + 1
    while (j_int < stop_index):
      l_mod[j_int] = float(l_mod[j_int - 1]) - step
      # print("Updating index", j_int, "to ", l_mod[j_int])
      j_int += 1

    i_int += 1

  # print("Modified List is", l_mod)
  return (l_mod)
# =============================================================================

def qtr_date_and_index_matching_eps_report_date(qtr_date_list_def,eps_report_date_def):
  # find the date closest to the date of last reported earnings from the date list
  qtr_date_matching_eps_report_date_def = min(qtr_date_list_def, key=lambda d: abs(d - eps_report_date_def))
  qtr_date_matching_eps_report_date_index_def = qtr_date_list_def.index(qtr_date_matching_eps_report_date_def)
  logging.debug("The match date for Last reported Earnings date : " + str(eps_report_date_def) + " in the Earnings df is : " + str(qtr_date_matching_eps_report_date_def) + " at index " + str(qtr_date_matching_eps_report_date_index_def))
  # If the date match in the eps_date_list is a date in the future date (that can happen if
  # the eps_report_date is more than 45 days after the quarter date. In this case we need to
  # move the match date index back by a quarter (by adding 1 to it - as the index starts
  # from 0 for the future most date)
  if ((qtr_date_matching_eps_report_date_def >= dt.date.today()) or (qtr_date_matching_eps_report_date_def >= eps_report_date_def)):
    qtr_date_matching_eps_report_date_index_def += 1
    qtr_date_matching_eps_report_date_def = qtr_date_list_def[qtr_date_matching_eps_report_date_index_def]
    logging.debug("Adjusting the match date to " + str(qtr_date_matching_eps_report_date_def) + " at index " + str(qtr_date_matching_eps_report_date_index_def))

  return (qtr_date_matching_eps_report_date_def,qtr_date_matching_eps_report_date_index_def)

# =============================================================================
# Global variables
# =============================================================================
g_var_annotate_actual_qtr_earnings = 1
g_var_use_aaii_data_to_extend_eps_projections = 1

g_dict_chart_options = {
  # This defined whether the numbers for Annual EPS and Q EPS and Dividend
  # should be printed on the chart
  'print_eps_and_div_numbers': 'Yes', # Yes, No, Both - This will create chart two times - one with numbers and one without
  'Chart_type_options': ['Log', 'Linear'],
  'Linear_chart_types' : ['Linear','Long_Linear']
  # 'Linear_chart_types': ['Long_Linear']
  # 'Linear_chart_types': ['Linear']
}
# =============================================================================


# todo :
# Put the number besides the last pink dot - so that sanity check can be done
# Always do a eps projection lines from the last black diamond
# Handle Annotated text
# See how you can add comments
# What format the file should be save
# Get the code debug friendly
# How to create other subplots that have the book value etc
#   Maybe use subplots for it
# How to use earnings projections
# If possible superimpose the PE line in the chart
# -----------------------------------------------------------------------
# Todo : fixme :
# Calcuate the delta b/w the projections_0 and projections_1 and show it on the chart (maybe as a string)
#   For this need to find the white diamonds for both the lists
# Fix the analyst accuracy for the new earnings file format
# -----------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Define the various filenames and Directory Paths to be used
# ---------------------------------------------------------------------------
# Find who is running the script and then read the json file for
# that individual, if it exists
who_am_i = os.getlogin()
my_hostname = socket.gethostname()

dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
chart_dir = "..\\..\\" + "Charts"
historical_dir = "\\..\\..\\" + "Historical"
earnings_dir = "\\..\\" + "Earnings"
dividend_dir = "\\..\\" + "Dividend"
log_dir = "\\..\\..\\..\\Automation_Not_in_Git\\" + "Logs"
aaii_financial_qtr_dir = "\\..\\..\\" + "AAII" + "\\" + "AAII_Financials" + "\\" + "Quarterly"
sc_funcs.master_to_aaii_ticker_xlate.set_index('Ticker', inplace=True)
# ---------------------------------------------------------------------------
# Set Logging
# critical, error, warning, info, debug
# set up logging to file - see previous section for more details
logging.basicConfig(# This decides what level of messages get printed in the debug file
                    # level=logging.DEBUG,
                    level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename=dir_path + log_dir + "\\" + 'SC_EarningsChart_debug.txt',
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
schiller_pe_monthly_file = "Schiller_PE_by_Month.csv"
master_tracklist_file = "Master_Tracklist.xlsm"
tracklist_file_full_path = dir_path + user_dir + "\\" + tracklist_file
configuration_file = "Configurations.csv"
configuration_json_file = "Configurations.json"
price_target_json_file = "Price_Targets.json"

calendar_file = "Calendar.csv"
configurations_file_full_path = dir_path + user_dir + "\\" + configuration_file


logging.debug("I am " + str(who_am_i) + " and I am running on " + str(my_hostname))
# if (re.search('ann', who_am_i, re.IGNORECASE)):
#   logging.debug("Looks like Ann is running the script")
#   user_name = "ann"
#   buy_sell_color = "red"
#   personal_json_file = "Ann.json"
# elif re.search('alan', who_am_i, re.IGNORECASE):
#   logging.debug("Looks like Alan is running the script")
#   buy_sell_color = "teal"
#   user_name = "alan"
#   personal_json_file = "Alan.json"
# elif (re.search('sundeep', who_am_i, re.IGNORECASE)) or \
#   re.search('DesktopNew-Optiplex', my_hostname, re.IGNORECASE) or \
#   re.search('LaptopOffice-T480', my_hostname, re.IGNORECASE) or \
#   re.search('LaptopNew-Inspiron-5570', my_hostname, re.IGNORECASE):
#   logging.debug("Looks like Sundeep is running the script")
#   user_name = "sundeep"
#   buy_sell_color = "magenta"
#   personal_json_file = "Sundeep.json"

logging.debug("Looks like Sundeep is running the script")
user_name = "sundeep"
buy_sell_color = "magenta"
personal_json_file = "Sundeep.json"
logging.debug("Setting the personal json file to " + str(personal_json_file))

tracklist_df = pd.read_csv(tracklist_file_full_path)
config_df = pd.read_csv(dir_path + user_dir + "\\" + configuration_file)
config_df.set_index('Ticker', inplace=True)
schiller_pe_df = pd.read_csv(dir_path + user_dir + "\\" + schiller_pe_monthly_file)
master_tracklist_df = pd.read_excel(dir_path + user_dir + "\\" + master_tracklist_file, sheet_name="Main")
master_tracklist_df.set_index('Tickers', inplace=True)

with open(dir_path + user_dir + "\\" + configuration_json_file) as json_file:
  config_json = json.load(json_file)

with open(dir_path + user_dir + "\\" + price_target_json_file) as json_file:
  price_target_json = json.load(json_file)


if (os.path.exists(dir_path + user_dir + "\\" + personal_json_file) is True):
  with open(dir_path + user_dir + "\\" + personal_json_file) as json_file:
    personal_json = json.load(json_file)

# print("The configuration df", config_df)
schiller_pe_date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in schiller_pe_df.Date.tolist()]
schiller_pe_value_list = schiller_pe_df.Value.tolist()
logging.debug("The schiller PE df is\n" + schiller_pe_df.to_string())
logging.debug("The Schiller PE Date list is\n" + str(schiller_pe_date_list))
logging.debug("The Schiller PE Value list is\n" + str(schiller_pe_value_list))
# =============================================================================

# =============================================================================
# Todo : Reading and plotting the index should be inside a if statement and should
# be in some global file
# Read the spy or dji or ixic file for comparison
plot_spy = 0
plot_dji = 1
plot_nasdaq = 1
if (plot_spy):
  spy_df = pd.read_csv(dir_path + "\\" + historical_dir + "\\" + "^GSPC_historical.csv")
if (plot_dji):
  dji_df = pd.read_csv(dir_path + "\\" + historical_dir + "\\" + "^DJI_historical.csv")
if (plot_nasdaq):
  nasdaq_df = pd.read_csv(dir_path + "\\" + historical_dir + "\\" + "^IXIC_historical.csv")
# =============================================================================


# -----------------------------------------------------------------------------
if (g_var_use_aaii_data_to_extend_eps_projections == 1):
  aaii_analysts_projection_df = pd.read_csv(dir_path + user_dir + "\\" + sc_funcs.aaii_analysts_projection_file)
  aaii_analysts_projection_df.set_index('Ticker', inplace=True)
  # logging.debug("The AAII Analysts Projection df is " + aaii_analysts_projection_df.to_string())

calendar_df = pd.read_csv(dir_path + user_dir + "\\" + calendar_file)
# logging.debug("The Calendar df read from Calendar file : \n" + calendar_df.to_string())
col_list = calendar_df.columns.tolist()
calendar_date_list_raw = []
for col in col_list:
  tmp_list = calendar_df[col].dropna().tolist()
  calendar_date_list_raw.extend(tmp_list)

calendar_date_list = [dt.datetime.strptime(str(date), '%m/%d/%Y').date() for date in calendar_date_list_raw]
# -----------------------------------------------------------------------------


# print ("The Tracklist df is", tracklist_df)
ticker_list_unclean = tracklist_df['Tickers'].tolist()
ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']

# #############################################################################
# #############################################################################
# #############################################################################
#                   MAIN LOOP FOR TICKERS
# #############################################################################
# #############################################################################
# #############################################################################
# ticker_list = ['IBM']
for ticker_raw in ticker_list:

  ticker = ticker_raw.replace(" ", "").upper()  # Remove all spaces from ticker_raw and convert to uppercase
  logging.info("========================================================")
  logging.info("Preparing chart for " + ticker)
  logging.info("========================================================")
  if ticker in ["QQQ"]:
    logging.info("File for " + str(ticker) + "does not exist in earnings directory. Skipping...")
    continue
  try:
    quality_of_stock = master_tracklist_df.loc[ticker, 'Quality_of_Stock']
  except (KeyError):
    logging.error("")
    logging.error("********** ERROR ERROR ERROR **********")
    logging.error(str(ticker) + " NOT found in Master Tracklist file")
    logging.error("This happens when Sundeep adds a ticker but then forgetfully :-)")
    logging.error("forgets to update the Master Tracklist file with that ticker....")
    logging.error("Please update the Master Tracklist file and then rerun the script again")
    logging.error("Exiting...")
    sys.exit()
  if ((quality_of_stock != 'Wheat') and (quality_of_stock != 'Wheat_Chaff') and (quality_of_stock != 'Essential') and (quality_of_stock != 'Sundeep_List')):
    logging.info(str(ticker) + " is not Wheat...skipping")
    continue

  # ---------------------------------------------------------------------------
  # From the Master Tracklist :
  # Get the last earning report date
  # and the last date when EPS Projections were updated.
  # The last earnings report date is used to :
  # Decide while vs black diamonds and Calculate the Analysts Adjustment factor
  # Both of them are dispalyed in the chart
  # ---------------------------------------------------------------------------
  try:
    ticker_master_tracklist_series = master_tracklist_df.loc[ticker]
    logging.debug("The Master Tracklist configurations for " + ticker + " is\n" + str(ticker_master_tracklist_series))
  except KeyError:
    # Todo : Create a default series with all nan so that it can be cleaned up in the next step
    logging.error("**********                                  ERROR                              **********")
    logging.error("**********     Entry for " + str(ticker).center(10) + " not found in the Master Tracklist file     **********")
    logging.error("**********     Please create one and then run the script again                 **********")
    sys.exit()
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Check if there is data in the config file corresponding to the ticker that
  # is being processed
  # ---------------------------------------------------------------------------
  try:
    ticker_config_series = config_df.loc[ticker]
    logging.debug("The configurations for " + ticker + " is\n" + str(ticker_config_series))
  except KeyError:
    # Todo : Create a default series with all nan so that it can be cleaned up in the next step
    logging.error("**********                                  ERROR                              **********")
    logging.error("**********     Entry for " + str(ticker).center(10) + " not found in the configurations file     **********")
    logging.error("**********     Please create one and then run the script again                 **********")
    sys.exit()

  if (str(ticker_config_series['Fiscal_Year']) != 'nan'):
    fiscal_yr_str = str(ticker_config_series['Fiscal_Year'])
    if not (all(x.isalpha() for x in fiscal_yr_str)):
      logging.error("**********                                           ERROR                                       **********")
      logging.error("**********     Entry for " + str(ticker).center(10) + " 'Fiscal_Year' in the configurations file  is" + str(fiscal_yr_str) + "   **********")
      logging.error("**********     It is not a 3 character month. Valid values(string) are:     **********")
      logging.error("**********     Valid values [Jan, Feb, Mar,...,Nov, Dec]                                         **********")
      logging.error("**********     Please correct and then run the script again                                      **********")
  else:
    fiscal_yr_str = "Dec"

  fiscal_qtr_str = "BQ-" + fiscal_yr_str
  fiscal_yr_str = "BA-" + fiscal_yr_str
  logging.debug("The fiscal Year is " + str(fiscal_yr_str))
  # ---------------------------------------------------------------------------

  # Get the chart type from configuration file
  if (str(ticker_config_series['Chart_Type']) != 'nan'):
    chart_type_idx = str(ticker_config_series['Chart_Type'])
  else:
    chart_type_idx = "Linear"
  if (not (all(x.isalpha() for x in chart_type_idx))) or ((chart_type_idx != 'Linear') and (chart_type_idx != 'Log')):
    logging.error("Error - The chart type field in the configuration file is : \"" + str(chart_type_idx) + "\"")
    logging.error("Only values allowed are Linear or Log. Please correct and rerun")
    sys.exit()

  # =============================================================================
  # Read the Historical file for the ticker
  # =============================================================================
  # todo : There are certain cases (MEDP) for e.g. that has recently IPO'ed that
  # have earning going back 2-3 quarters more than the historical data (in other
  # words they started trading on say 08/12/2015, but their earnings are available
  # from 03/30/2015). In such a case probably need to look at calendar file and extend
  # the date list and adj_close list so that all the prior earnings are included.
  # The back date adj_close needs to be initialized to whatever value (nan likely)
  historical_df = pd.read_csv(dir_path + "\\" + historical_dir + "\\" + ticker + "_historical.csv")
  # logging.debug("The Historical df is \n" + historical_df.to_string())
  # =============================================================================

  # =============================================================================
  # Read the Earnings file for the ticker
  # =============================================================================
  qtr_eps_df = pd.read_csv(dir_path + "\\" + earnings_dir + "\\" + ticker + "_earnings.csv", delimiter=",")
  logging.debug("The Earnings df is \n" + qtr_eps_df.to_string())

  # Read the Actual Quarterly Report Dates from the earnings file
  qtr_eps_report_date_list = []
  if ('Q_Report_Date' in qtr_eps_df.columns):
    tmp_list = qtr_eps_df.Q_Report_Date.tolist()
    for item in tmp_list:
      # logging.debug("Item : " + str(item))
      if (str(item) != 'nan'):
        tmp_first_entry_row = tmp_list.index(item) + 1
        break
    logging.debug("The first non-zero entry for Q_Report_Data before dropna is at row : " + str(tmp_first_entry_row))
    qtr_eps_report_date_list = qtr_eps_df.Q_Report_Date.dropna().tolist()
    tmp_dropped_entries = tmp_first_entry_row - len(qtr_eps_report_date_list)
    logging.debug("The Quarterly Report Date List from the earnings file after dropna is " + str(qtr_eps_report_date_list))
  else:
    logging.error("The Quarter report date column (Column Heading : Q_Report_Date) is missing in the Earnings file...")
    logging.error("Please add and populate that column - it contains the dates when the compnay has reported earnings")
    logging.error("This column is populated by looking at the dark blue bars on CNBC to find out the quarter report dates")
    sys.exit(1)
  if (len(qtr_eps_report_date_list) == 0):
    logging.error("The Quarter report date column in the Earnings file has no entries. Need atleast one entry...")
    logging.error("Please add and populate that column - it contains the dates when the company has reported earnings")
    logging.error("This column is populated by looking at the dark blue bars on CNBC to find out the quarter report dates")
    sys.exit(1)
  try:
    qtr_eps_report_date_list_dt = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in qtr_eps_report_date_list]
  except:
    logging.error("Found some error while processing Quarter Report Date List, col B (Q_Report_Date) in the earnings report file")
    logging.error("This generally happens when Sundeep is preparing a new earnings file and the date format is ")
    logging.error("Unintentially entered wrong, like 1/22/20022, instead of 1/22/2022 etc. ")
    logging.error("Please take a look at col B (Q_Report_Date) in earnings report file and see if there is some misformatted data, correct and rerun")
    sys.exit(1)
  # Check if the qtr_eps_report_date dates are in descending order
  for i_date_idx in range(len(qtr_eps_report_date_list_dt)):
    if (i_date_idx > 0) and (qtr_eps_report_date_list_dt[i_date_idx] > qtr_eps_report_date_list_dt[i_date_idx-1]):
        logging.error("The dates in \'Q_Report_Date\' col. (Col B) in the earnings file are not in descending order")
        logging.error("The offending date values are : " + str(qtr_eps_report_date_list_dt[i_date_idx-1]) + ", on row : " + str(tmp_first_entry_row+i_date_idx))
        logging.error("The offending date values are : " + str(qtr_eps_report_date_list_dt[i_date_idx])   + ", on row : " + str(tmp_first_entry_row+i_date_idx+1))
        logging.error("They should have been in descending order")
        logging.error("Sundeep probably got distracted and put the wrong year. for e.g instead of 1/22/20/25, it will put 1/22/2024")
        logging.error("and that likely got the dates in non-descending order")
        logging.error("Please take a look at col B (Q_Report_Date) in earnings file, correct and rerun")
        sys.exit(1)
  eps_report_date = qtr_eps_report_date_list_dt[0]
  for i_date in qtr_eps_report_date_list_dt:
    if (i_date > dt.date.today()):
      logging.error("The date " + str(i_date) + " in the Q_Report_Date column is later than today...")
      logging.error("Please correct and rerun...")
      sys.exit(1)

  logging.debug("The Quarterly Report Date List is " + str(qtr_eps_report_date_list_dt))
  logging.debug("The Last Earning report date is " + str(eps_report_date))

  # ---------------------------------------------------------------------------
  # Sanity check the date_list here for any duplicate dates. This is just to
  # prevent any obscure errors that give out cryptic messages later on b/c
  # AAII projections may get tacked and can lead to weird stuff
  # ---------------------------------------------------------------------------
  qtr_eps_date_list = qtr_eps_df['Q_Date'].tolist()
  logging.debug("The Q_Date list " + str(qtr_eps_date_list))
  if len(set(qtr_eps_date_list)) != len(qtr_eps_date_list):
    logging.error("Possible duplicate items found in the Q_Date list for qtr_eps. Please correct and rerun...")
    unique_vals_arr = []
    duplicate_vals_arr = []
    for i in qtr_eps_date_list:
      if (i not in unique_vals_arr):
        logging.debug("Adding " + str(i) + " to unique")
        unique_vals_arr.append(i)
      else:
        logging.debug("Adding " + str(i) + " to duplicate")
        duplicate_vals_arr.append(i)
      logging.debug("Unique Dates are " + str(unique_vals_arr))
      logging.debug("Duplicate Dates are " + str(duplicate_vals_arr) + "\n")
    logging.error("Duplicate Dates are " + str(duplicate_vals_arr))
    sys.exit(1)
  # ---------------------------------------------------------------------------

  # -------------------------------------------------------------------------
  # 10/26/2021
  # Sundeep is in the process of adding a column Q_EPS_Adjusted to all the
  # earnings file - this will contain whatever earnings are reported on CNBC
  # (rather than the diluted earnings that I collect anyway). So, in essence
  # I am going to collect two sets of earnings - one diluted (that I always
  # have, and (now) additionally adjusted earnings (one that CNBC reports
  # on their website (NOTE: It is not always called adjusted earnings in the
  # CNBC report, but the earnings file will call it adjusted earnings
  # While sundeep is in the process of collecting the adjusted earnings for
  # all the stocks, we want to make sure that the current structure of the earnings
  # file should work.
  # So - as we continue - if the Q_EPS_Adjusted column is available in the
  # earnings file, then copy over the latest "x" quarters of adjusted earnings
  # projections (CNBC projections) from the adjusted column over to the diluted eps
  # column (they are the white diamond dates)
  # Now this is not necessary to be done - but if I don't do it, the I have to
  # put the CNBC projections in both Q_EPS_Diluted and Q_EPS_Adjusted.
  # This code just copies over the white diamond (future than the current Q report date)
  # CNBC projections from the Q_EPS_Adjusted column to Q_EPS_Diluted column.
  # I am not 100% sure on how this is going to be useful, but it is
  # one of the things that may become useful later on...
  # -------------------------------------------------------------------------
  # check if Q_EPS_Adjusted column exists in the qtr_ep_df
  qtr_eps_list = qtr_eps_df.Q_EPS_Diluted.tolist()
  # qtr_eps_date_list = qtr_eps_df['Q_Date'].tolist()
  try:
    logging.debug("The Q_Date list " + str(qtr_eps_df.Q_Date.tolist()))
    qtr_eps_date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in qtr_eps_df.Q_Date.tolist()]
  except (TypeError):
    logging.error("**********                                ERROR                               **********")
    logging.error("**********  Some of the entries for Column 'Date' in the Earnings file are    **********")
    logging.error("**********  either missing (blank) or do not have proper mm/dd/yyyy format.   **********")
    logging.error("**********  Please correct the Earnings file 'Date' column and run again      **********")
    sys.exit(1)

  # ---------------------------------------------------------------------------
  # Find the Q_Date and it's index closest to the date of last reported earnings
  # and if there is no reported earnings filled corresponding to that index (no
  # earnings filled in Q_EPS_Diluted column), then flag an error...this means
  # that the Q_Report_Date had a date filled in but, likely, I forgot to fill
  # in the actual earnings corresponding the report date in the Q_EPS_Diluted
  # column (kids called me or something happened and then I forgot :-))
  # ---------------------------------------------------------------------------
  eps_date_list_eps_report_date_match, eps_date_list_eps_report_date_index = qtr_date_and_index_matching_eps_report_date(qtr_eps_date_list, eps_report_date)
  # if (math.isnan(qtr_eps_df.loc[eps_date_list_eps_report_date_index,['Q_EPS_Diluted']])):
  if (str(qtr_eps_df.iloc[eps_date_list_eps_report_date_index]['Q_EPS_Diluted']) == 'nan'):
    logging.error("Latest Diluted earnings in Q_EPS_Diluted column, corresponding to Lastest Earnings date : " + str(eps_report_date) + ", is not filled in the earning file")
    logging.error("Likely you put the earnings release date in the Q_Report_Date column but forgot (or got distracted) to enter the actual earnings in Q_EPS_Diluted column")
    logging.error("Row : " + str(eps_date_list_eps_report_date_index+2) + " (Date: " + str(eps_report_date) + ")," + " Col : Q_EPS_Diluted")
    logging.error("Please fill it out and rerun")
    sys.exit()
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Check if there is case where I forgot to update the Q_Report_Date but recorded
  # the actual earnings in Q_EPS_Diluted column that the company reported.
  # In other words, the code finds something in Q_EPS_Diluted col but nothing corresponding
  # to that in the Q_Report_Date column.
  # It generally means that either I forgot or got distracted while updating the earnings
  # file with reported earning date...It is a simple problem to solve.
  # Just go the Edgar or CNBC and find out the actual reporting date and fill in
  # NOTE : This code only (and should) check for the rows that are later than the
  # last reported earnings date found in the earning file. In other words, if the
  # code found 06/15/2022 as the last reported date in Q_Report_Date then will check
  # only Q_EPS_Diluted rows that are newer (above) that row. Otherwise, if we check
  # the whole earnings file for missing Q_Report_Date for earnings, then there
  # are MANY MANY rows for which the Q_Report_Date is not present (all the
  # older earnings for which the CBNC date is not available)
  # ---------------------------------------------------------------------------
  logging.debug("The Q_Date index that matches to last reported earning date is : " + str(eps_date_list_eps_report_date_index))
  for i_int in range(eps_date_list_eps_report_date_index):
    # logging.debug("Index : " + str(i_int) + ", : " + qtr_eps_df.loc[i_int,['Q_Date']].to_string() + ", : " + qtr_eps_df.loc[i_int,['Q_EPS_Diluted']].to_string())
    if (str(qtr_eps_df.iloc[i_int]['Q_EPS_Diluted']) == 'nan'):
      logging.debug("Index : " + str(i_int) + ", : " + qtr_eps_df.loc[i_int, ['Q_Date']].to_string() + ", : " + qtr_eps_df.loc[i_int, ['Q_EPS_Diluted']].to_string())
    else:
      logging.error("It seems that : " + qtr_eps_df.loc[i_int,['Q_EPS_Diluted']].to_string() + ", is recorded for : " + qtr_eps_df.loc[i_int,['Q_Date']].to_string() + " in row " + str(i_int+2) + " of the earnings file")
      logging.error("while there is no corresponding Q_Report_Date populated for those earnings")
      logging.error("Did you just forget/got distracted to update the earnings report date in the earnings file when you recorded company earnings for : " + qtr_eps_df.loc[i_int,['Q_Date']].to_string())
      logging.error("Please have a look at row : " + str(i_int+2) + " in the earnings file corresponding to column : Q_Report_Date and fill the actual earnings report date")
      logging.error("Please correct and rerun. Exiting...")
      sys.exit()
  # ---------------------------------------------------------------------------

  if 'Q_EPS_Adjusted' in qtr_eps_df.columns:
    qtr_eps_adjusted_list = qtr_eps_df.Q_EPS_Adjusted.tolist()
    logging.info("Found qtr_eps_adjusted column in the earnings file")
    logging.info("will copy over the (future) earnings projections from q_eps_adjusted column to q_eps_diluted column")
    logging.debug("The QTR EPS Diluted list is " + str(qtr_eps_list))
    logging.debug("The QTR EPS Adjusted list is " + str(qtr_eps_adjusted_list))

    # Copy the Q_EPS_Adjusted EPS numbers into Q_EPS_Diluted column starting at index 0
    # (which is the latest Q_Date (row 2 in the column Q_Date) till we reach the index
    # that represents the last unreported earnings quarter. So for e.g row 2 in Q_date is 12/30/2022
    # and the last earnings were reported on 06/30/2021, then copy the Q_EPS_Adjusted from
    # 12/30/2022, 09/30/2022, 06/30/2022, 03/30/2022, 12/30/2021 and 09/30/2021 rows
    # into Q_EPS_Diluted. That way the forst few 'nan' in Q_EPS_Diluted will now have the
    # same value as Q_EPS_Adjusted
    qtr_eps_df_copy = qtr_eps_df.copy()
    logging.debug("The qtr earnings df :" + qtr_eps_df.to_string())
    for i_int in range(eps_date_list_eps_report_date_index):
      qtr_eps_df.loc[i_int,['Q_EPS_Diluted']] = qtr_eps_df_copy.loc[i_int,['Q_EPS_Adjusted']].values

    qtr_eps_list = qtr_eps_df.Q_EPS_Diluted.tolist()
    logging.debug("The qtr earnings df after copying over Q_EPS_Adjusted, till the lastest earnings date,  over to Q_EPS_Diluted :" + qtr_eps_df.to_string())
    qtr_eps_df_copy = pd.DataFrame()
  # -------------------------------------------------------------------------

  # -------------------------------------------------------------------------
  # Check if the latest date in historical df is newer than or equal to the latest
  # date in the Q_Date - Otherwise the white diamonds (which are based on Q_Date)
  # will be created for (future) dates that don't exist in historical df and the
  # script will produce strange charts and/or gives out weired messages
  # -------------------------------------------------------------------------
  latest_qtr_date_in_earnings_file = qtr_eps_df['Q_Date'].tolist()[0]
  logging.debug("The latest Date in Earnings file is " + str(latest_qtr_date_in_earnings_file))
  latest_qtr_date_in_earnings_file_dt = dt.datetime.strptime(str(latest_qtr_date_in_earnings_file), '%m/%d/%Y').date()
  if (fiscal_yr_str != str("BA-" + str(latest_qtr_date_in_earnings_file_dt.strftime("%b")))):
    logging.error("The fiscal year in config file : *** " + str(fiscal_yr_str) + " *** does not match the month of the latest qtr in the earnings file *** " + str(latest_qtr_date_in_earnings_file_dt.strftime("%b")) + " ***")
    logging.error("Please correct and rerun")
    sys.exit(1)
  latest_date_in_historical_file = historical_df['Date'].tolist()[0]
  latest_date_in_historical_file_dt = dt.datetime.strptime(str(latest_date_in_historical_file), '%m/%d/%Y').date()
  logging.debug("The latest Date in Historical file is " + str(latest_date_in_historical_file))
  if (latest_qtr_date_in_earnings_file_dt > latest_date_in_historical_file_dt):
    logging.error("The latest date in the historical df : " + str(latest_date_in_historical_file) + " should be newer than the lastest date in qtr df : " + str(latest_qtr_date_in_earnings_file))
    logging.error("Historical df should always has date that is later than the latest qtr eps date")
    logging.error("Not having that will create problems in the script further as the script may not recognize any white diamonds and will fail")
    logging.error("********** Maybe you forgot to update (add a year or two) to the 'Calendar_Future_Date' Column                                              **********")
    logging.error("********** in configurations file, when you added more quarters of earnings in the earnings file                                            **********")
    logging.error("********** or you added years in the configurations file but forgot to run the merge script to reflect added year(s) in the historical file **********")
    logging.error("Please correct - by adding a year or two in the configuration file, if your forgot - and then rerun merge script either way before continuing")
    sys.exit(1)
  # -------------------------------------------------------------------------

  # -------------------------------------------------------------------------
  #       *****     Start of AAII insertion of Projected EPS Insertion    *****
  # -------------------------------------------------------------------------
  logging.info("The AAII Analysts file used is : " + str(sc_funcs.aaii_analysts_projection_file))
  # Find the fiscal years y0, y1 and y2 and their respective projections
  no_of_years_to_insert_aaii_eps_projections = 0
  continue_aaii_eps_projections_for_this_ticker = 1
  if ((str(ticker_config_series['Use_AAII_Projections']) == 'No') or (str(ticker_config_series['Use_AAII_Projections']) == 'N')):
    logging.debug("User Specifies that AAII Projections for this ticker should not be used through")
    logging.debug("the setting in Use_AAII_Projections column in the configurations file for this ticker")
    logging.debug("..........Will skip inserting AAII Projections..........")
    logging.debug("This frequently happens if the AAII Projections are so out of whack that we want to temporarily")
    logging.debug("stop AAII EPS insertion from screwing the chart while we figure out what's up AAII EPS projections")
    logging.debug("For e.g. for FNF - the projections, generally in the range of .4 - in the AAII file are in the $100s ")
    logging.debug("thus screwing the chart (scale) completely...So the course could be to :")
    logging.debug("1. Go and correct the AAII file manually - after finding out what the values should be from CNBC projections (if they are available there)")
    logging.debug("2. Download AAII file again - and hope that the discrepancy is gone")
    logging.debug("3. Wait for a few days and download file again - and hope that the discrepancy is gone")
    logging.debug("4. Temporarily disable the AAII insertion - which is what the user has done here")
    logging.debug("Once - with #1-#3 the AAII Porjections are corrected, then the user should change the configurations file")
    logging.debug("so that the AAII EPS Projections can be included in the chart")
    continue_aaii_eps_projections_for_this_ticker = 0

  # Check if the ticker is found in the analysts_projection_df and
  # If found, then read it from there
  # If not found, then skip putting the future EPS projection in the chart
  # In both cases also check if the tickers is also found in the missing ticker list, then
  # If found, then warn/inform the user appropriately and skip putting the future
  # EPS projections in the chart anyway. The assumption being that there might be a good
  # reason on why the user put the ticker in the aaii_missing_tickers_list
  # (e.g projections are way off/seem very wrong, user really does not want EPS
  # projections in the chart beyond what is in the earnings file etc)
  try:
    ticker_aaii_analysts_projection_series = aaii_analysts_projection_df.loc[ticker]
    if (ticker in sc_funcs.aaii_missing_tickers_list):
      logging.warning("")
      logging.warning(str(ticker) + " is listed in aaii_missing_tickers_list in the sc_funcs file, but")
      logging.warning("it is present in the "+ str(sc_funcs.aaii_analysts_projection_file) + " file")
      logging.warning("There better be a good reason to have it in the aaii_missing_tickers_list b/c now the script")
      logging.warning("is NOT going to pick future EPS projections and put them in the cart and, again, unless")
      logging.warning("there is a very good reason, you probably do NOT want that")
      logging.warning("=====> Recommended Action <=====")
      logging.warning("Unless you have a very good reason for why the ticker was put in the aaii_missing_tickers_list and you want it there, otherwise")
      logging.warning("Remove the ticker from aaii_missing_tickers_list and rerun the script")
      logging.warning("I WILL PAUSE THE SCRIPT FOR 5 SECONDS FOR YOU TO THINK...")
      logging.warning("AND THEN WILL CONTINUE TO PREPARE THE CHART WITHOUT USING THE EPS PROJECTIONS FROM AAII ANALYSTS FILE")
      logging.warning("")
      continue_aaii_eps_projections_for_this_ticker = 0
      time.sleep(5)
  except:
    logging.warning("")
    logging.warning(str(ticker) + " is NOT in AAII Analysts projections df. Will skip inserting future EPS Projections from AAII Analysts data...")
    logging.warning("Keep an eye out, the ticker may be added by AAII in the future, then the script will insert future EPS projections in the chart")
    logging.warning("")
    if (ticker in sc_funcs.aaii_missing_tickers_list):
      logging.info("Also found " + str(ticker) + " in the aaii_missing_tickers_list")
      logging.info("This is superflous right now as the ticker is not in the AAII analysts file anyway.")
      logging.info("You can remove the ticker from the aaii_missing_tickers_list and it will have not effect on the chart right now")
      logging.warning("However (unless there is strong reason not to) it is recommended to remove the ticker from the aaii_missing_tickers_list")
      logging.warning("because if you don't remove, then the tickers future EPS prjoections will NOt get picked by the script even after it is added by AAII")
      logging.info("")
      time.sleep(3)
    continue_aaii_eps_projections_for_this_ticker = 0

  if (g_var_use_aaii_data_to_extend_eps_projections == 1) and (continue_aaii_eps_projections_for_this_ticker == 1):
    # ticker_aaii_analysts_projection_series = aaii_analysts_projection_df.loc[ticker]
    logging.debug("The series for " + str(ticker) + " in the AAII Analysts df is " + str(ticker_aaii_analysts_projection_series))
    y_plus0_fiscal_year_end = ticker_aaii_analysts_projection_series['Date--Current fiscal year']
    if (str(y_plus0_fiscal_year_end) != 'nan'):
      y_plus0_fiscal_year_dt = dt.datetime.strptime(str(y_plus0_fiscal_year_end), '%m/%d/%Y').date()
    else:
      logging.debug("The y0 fiscal year end for " + str(ticker) + " is NaN in AAII Analysts df...will skip inserting AAII EPS Projections")
      continue_aaii_eps_projections_for_this_ticker = 0

  # Till this point we have only decided whether we want (based on user/config file variables) to or
  # we can insert AAII Projections (based on whether the ticker exists in the aaii df)
  # This piece of code decides how many years of projected EPS can be inserted
  if (g_var_use_aaii_data_to_extend_eps_projections == 1) and (continue_aaii_eps_projections_for_this_ticker == 1):
    y_plus1_fiscal_year_dt = y_plus0_fiscal_year_dt + relativedelta(years=1)
    y_plus2_fiscal_year_dt = y_plus0_fiscal_year_dt + relativedelta(years=2)
    logging.debug("Y0 Fiscal Year for  " + str(ticker) + " ends on " + str(y_plus0_fiscal_year_dt))
    logging.debug("Y1 Fiscal Year for  " + str(ticker) + " ends on " + str(y_plus1_fiscal_year_dt))
    logging.debug("Y2 Fiscal Year for  " + str(ticker) + " ends on " + str(y_plus2_fiscal_year_dt))
    y_plus0_fiscal_year_eps_projections = ticker_aaii_analysts_projection_series['EPS Est Y0']
    y_plus1_fiscal_year_eps_projections = ticker_aaii_analysts_projection_series['EPS Est Y1']
    y_plus2_fiscal_year_eps_projections = ticker_aaii_analysts_projection_series['EPS Est Y2']
    logging.debug("Y0 eps projections are " + str(y_plus0_fiscal_year_eps_projections))
    logging.debug("Y1 eps projections are " + str(y_plus1_fiscal_year_eps_projections))
    logging.debug("Y2 eps projections are " + str(y_plus2_fiscal_year_eps_projections))
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Now tht we have dates from AAII fiscal years compare it against the latest
    # date that is in the earnings file and find the number of year/quarters than
    # need to be inserted
    # -------------------------------------------------------------------------
    if (str(ticker_config_series['Use_Diluted_or_Adjusted_EPS']) == "Adjusted"):
      logging.info("Using ADJUSTED EPS to Plot the chart")
      if qtr_eps_df['Q_EPS_Adjusted'].count() != qtr_eps_df['Q_EPS_Diluted'].count():
        logging.error ("")
        logging.error ("*************************************************************************************")
        logging.error ("As per the config file (column : Use_Diluted_or_Adjusted_EPS), we are using Adjusted Earnings EPS to plot the chart")
        logging.error ("However, the # of entries in Q_EPS_Diluted are not equal to the number of entries in the Q_EPS_Adjusted")
        logging.error ("# of entries in Q_EPS_Diluted  : " + str(qtr_eps_df['Q_EPS_Diluted'].count()))
        logging.error ("# of entries in Q_EPS_Adjusted : " + str(qtr_eps_df['Q_EPS_Adjusted'].count()))
        logging.error ("That number should be equal")
        logging.error ("Generally the # of entries in Q_EPS_Adjusted is less than the # of entries in Q_EPS_Diluted")
        logging.error ("and they are missing towrads the bottom (older entries)")
        logging.error ("If that is the case then : ")
        logging.error ("  1. One quick way to fix is to copy over those entries from Q_EPS_Diluted to Q_EPS_Adjusted")
        logging.error ("     That (hopfully) should not make a lot of difference in the chart")
        logging.error ("  2. Other option would be to get the Adjusted earnings from 8-K from SEC")
        logging.error ("  3. If you really don't care, then Sundeep can modify the script so that all dates older than")
        logging.error ("     the oldest Q_EPS_Adjusted can be deleted...That is not a good option as it would shorten")
        logging.error ("     the left side of the chart (meaning the left side of the chart will now only start from")
        logging.error ("     when the Q_EPS_Adjusted values are available...It is not the best way, but can be done")
        logging.error ("     It can even be done manually by modifying the earnings.csv file, but then that would be")
        logging.error ("     permanent loss of data..so either save that somewhere in case you change your mind...but")
        logging.error ("     probably #1 and #2 would be the best options to consider")
        logging.error ("So, there is some thinking needed...Please fix and then rerun")
        logging.error ("")
        logging.error ("Exiting...")
        logging.error ("*************************************************************************************")
        sys.exit()
      qtr_eps_list = qtr_eps_df.Q_EPS_Adjusted.tolist()
      # Copy the adjusted column over the diluted column as the code further down updates
      # Q_EPS_Diluted
      qtr_eps_df['Q_EPS_Diluted'] = qtr_eps_df['Q_EPS_Adjusted']
    else:
      qtr_eps_list = qtr_eps_df.Q_EPS_Diluted.tolist()
    days_bw_y_plus0_and_latest_qtr_date_in_earnings_file = y_plus0_fiscal_year_dt - latest_qtr_date_in_earnings_file_dt
    days_bw_y_plus1_and_latest_qtr_date_in_earnings_file = y_plus1_fiscal_year_dt - latest_qtr_date_in_earnings_file_dt
    days_bw_y_plus2_and_latest_qtr_date_in_earnings_file = y_plus2_fiscal_year_dt - latest_qtr_date_in_earnings_file_dt
    logging.debug("The difference b/w Y0 fiscal year date and Latest qtr date is : " + str(days_bw_y_plus0_and_latest_qtr_date_in_earnings_file.days) + " days")
    logging.debug("The difference b/w Y1 fiscal year date and Latest qtr date is : " + str(days_bw_y_plus1_and_latest_qtr_date_in_earnings_file.days) + " days")
    logging.debug("The difference b/w Y2 fiscal year date and Latest qtr date is : " + str(days_bw_y_plus2_and_latest_qtr_date_in_earnings_file.days) + " days")
    if (-5 <= days_bw_y_plus2_and_latest_qtr_date_in_earnings_file.days <= 5):
      logging.warning(str(ticker) + " : The date for the Latest entry in the Earnings file: " + str(latest_qtr_date_in_earnings_file_dt) + " matches Y2 fiscal end date : " + str(y_plus2_fiscal_year_dt) + " ...so nothing needs to be inserted")
      logging.warning(str(ticker) + " : Hmmm...However this should very rare...make sure for " + str(ticker) + "that the latest entry qtr_eps_date and the Y2 fiscal year dates actually match...")
    elif (-5 <= days_bw_y_plus1_and_latest_qtr_date_in_earnings_file.days <= 5):
      logging.debug(str(ticker) + " : The date for the Latest entry in the Earnings file: " + str(latest_qtr_date_in_earnings_file_dt) + " matches Y1 fiscal end date : " + str(y_plus1_fiscal_year_dt) + " ...so we can possibly add Y2 fiscal year projections if they are not NaN")
      if ((str(y_plus2_fiscal_year_eps_projections) != 'nan') and
              (y_plus1_fiscal_year_eps_projections > 0) and
              (y_plus2_fiscal_year_eps_projections/y_plus1_fiscal_year_eps_projections < 10)):
        logging.debug(str(ticker) + " : Y2 fiscal year eps projections are NOT nan and Y1 fiscal year eps projections are non-negative. So, will insert one year (Y2)")
        no_of_years_to_insert_aaii_eps_projections = 1
        logging.debug("The latest qtr date in earnings file is " + str(latest_qtr_date_in_earnings_file_dt))
        logging.debug("The Fiscal Qtr string is " + str(fiscal_qtr_str))
        # Fixme : Sundeep is here There is a bug in Python, I guess, that when the fiscal_qtr ends in Feb then it starts
        # Maybe the best way to fix is fix so
        # meplace upstairs - then regress it will different fiscal qtr str to make
        # sure that it works (It currently was failing for KMX)
        if (fiscal_qtr_str == "BQ-Feb"):
          logging.debug("Here I am")
          fiscal_qtr_and_yr_dates_raw = pd.date_range(latest_qtr_date_in_earnings_file_dt, y_plus2_fiscal_year_dt + dt.timedelta(days=5),                                                      freq=fiscal_qtr_str)
        else:
          fiscal_qtr_and_yr_dates_raw = pd.date_range(latest_qtr_date_in_earnings_file_dt, y_plus2_fiscal_year_dt, freq=fiscal_qtr_str)
      else:
        logging.debug(str(ticker) + " : Hmmm...it seems like either Y2 eps projections are Nan OR "
                                    " Y1 eps projections are negative in AAII. In case the Y1 eps is negative, growth math will not work right OR "
                                    " The ratio between y_plus2_eps_projections/y_plus1_eps_projections ("
                                    + str(y_plus2_fiscal_year_eps_projections) + "\\"
                                    + str(y_plus1_fiscal_year_eps_projections) + " = " + str(y_plus2_fiscal_year_eps_projections/y_plus1_fiscal_year_eps_projections)
                                    + ") is greater than 10. Inserting Earnings projections in such a case will blow up the scale of the chart"
                                    " Because of one of the reasons above (Sundeep should look in the debug file to find out which reason), "
                                    " no AAII projections will be inserted inserted...")
    elif (-5 <= days_bw_y_plus0_and_latest_qtr_date_in_earnings_file.days <= 5):
      logging.debug(str(ticker) + " : The date for the Latest entry in the Earnings file: " + str(latest_qtr_date_in_earnings_file_dt) + " matches Y0 fiscal end date : " + str(y_plus0_fiscal_year_dt) + " ...so we can possibly add Y1 and Y2 fiscal year projections if they are not NaN")
      # Sundeep - This is a shortcut way of ONLY inserting 1 year of EPS Projections when 2 years of projections were available
      # Force y_plus2_fiscal_year_eps_projections = 'nan' here so that only one year fiscal projection can be inserted
      # To revert back to adding upto 2 years of aaii eps projections - just comment the next line
      y_plus2_fiscal_year_eps_projections = 'nan'
      if ((str(y_plus2_fiscal_year_eps_projections) != 'nan') and
          (str(y_plus1_fiscal_year_eps_projections) != 'nan') and
              (y_plus1_fiscal_year_eps_projections > 0) and
              (y_plus0_fiscal_year_eps_projections > 0) and
              (y_plus2_fiscal_year_eps_projections / y_plus1_fiscal_year_eps_projections < 10) and
              (y_plus1_fiscal_year_eps_projections / y_plus0_fiscal_year_eps_projections < 10)):
        logging.debug(str(ticker) + " : Both Y1 and Y2 fiscal year eps projections are NOT nan and Y1 and Y0 eps numbers are non-negative. So, will insert two years (Y1 and Y2)")
        no_of_years_to_insert_aaii_eps_projections = 2
        fiscal_qtr_and_yr_dates_raw = pd.date_range(latest_qtr_date_in_earnings_file_dt, y_plus2_fiscal_year_dt, freq=fiscal_qtr_str)
      elif ((str(y_plus1_fiscal_year_eps_projections) != 'nan') and
               (y_plus0_fiscal_year_eps_projections > 0) and
               (y_plus1_fiscal_year_eps_projections / y_plus0_fiscal_year_eps_projections < 10)):
        logging.debug(str(ticker) + " : Y2 fiscal year eps projections is NaN, Y1 fiscal year eps projections is NOT nan and Y0 fiscal year number is non-negative. So, will insert one year (Y1)")
        no_of_years_to_insert_aaii_eps_projections = 1
        fiscal_qtr_and_yr_dates_raw = pd.date_range(latest_qtr_date_in_earnings_file_dt, y_plus1_fiscal_year_dt, freq=fiscal_qtr_str)
      else:
        logging.debug(str(ticker) + " : Hmmm...it seems like either both Y1 and Y2 eps projections are nan in AAII or either Y0 or Y1 eps projections are negative. Nothing inserted...")
        logging.debug(str(ticker) + " : Growth math does not work when we start from negative numbers. However, if both Y2 and Y1 earnings projections are NaN, then please check Y1 and Y2 earnings projections in AAII")
        logging.debug(str(ticker) + " Either that OR one of the ratios b/w y_plus2_eps_projections/y_plus1_eps_projections OR y_plus1_eps_projections/y_plus0_eps_projections")
        logging.debug(str(ticker) + " is greater than 10. If we try to insert earnings projections when the ration is that high, it messes up the scale of the chart")
        logging.debug(str(ticker) + " It is better in these cases to NOT insert the projections...Sundeep is thinking")
    else:
      logging.error("The date corresponding to the Latest entry in the Earnings file : " + str(latest_qtr_date_in_earnings_file_dt))
      logging.error("neither matches the Y0 fiscal year end from AAII file : " + str(y_plus0_fiscal_year_dt))
      logging.error("nor matches the Y1 fiscal year end from AAII file : " + str(y_plus1_fiscal_year_dt))
      logging.error("nor matches the Y2 fiscal year end from AAII file : " + str(y_plus2_fiscal_year_dt))
      sys.exit(1)
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Now that we the number of years of EPS projections to insert,
    # calculate the projected eps per quarter for future years - and insert in the dataframe
    # At the end we will end up
    # 1. Updating the qtr_eps_df - which will be pre-pended with the dates and
    #   the qtr_eps values that we are inserting for projected EPS from AAII
    # 2. Updating the historica_df - which will be pre-pended with the calendar
    #   dates for the numbers of years for which projected qtr_eps was inserted
    # -------------------------------------------------------------------------
    if (no_of_years_to_insert_aaii_eps_projections > 0):
      fiscal_qtr_dates = []
      for x in fiscal_qtr_and_yr_dates_raw:
        fiscal_qtr_dates.append(x.date().strftime('%m/%d/%Y'))

      # This can happen if the qtr date in the earnings file also prouduces
      # the match (and so produces a spurious date) in the fiscal_qtr_and_yr_dates_raw above
      # Maybe cleanup the above calculation to ensure that the
      if (len(fiscal_qtr_dates) != 4) and (len(fiscal_qtr_dates) != 8):
        del fiscal_qtr_dates[0]
      logging.debug("The original qtr dates list is\n" + str(fiscal_qtr_and_yr_dates_raw))
      logging.debug("The modified qtr dates list is\n" + str(fiscal_qtr_dates))

      logging.debug("The qtr eps list is " + str(qtr_eps_list))
      no_of_qtr_to_insert = no_of_years_to_insert_aaii_eps_projections * 4
      tmp_eps_list = []
      for i_int in range(no_of_qtr_to_insert):
        tmp_eps_list.append(float('nan'))
      if (no_of_years_to_insert_aaii_eps_projections == 1):
        if (-5 <= days_bw_y_plus0_and_latest_qtr_date_in_earnings_file.days <= 5):
          growth_factor = y_plus1_fiscal_year_eps_projections / y_plus0_fiscal_year_eps_projections
          logging.debug(str(ticker) + " : Inserting one year of EPS projections with the growth factor for y_plus1 over y_plus0 : " + str(growth_factor) + " (" + str(y_plus1_fiscal_year_eps_projections) + "/" + str(y_plus0_fiscal_year_eps_projections) + ")")
        else:
          growth_factor = y_plus2_fiscal_year_eps_projections / y_plus1_fiscal_year_eps_projections
          logging.debug(str(ticker) + " : Inserting one year of EPS projections with the growth factor for y_plus2 over y_plus1 : " + str(growth_factor) + " (" + str(y_plus2_fiscal_year_eps_projections) + "/" + str(y_plus1_fiscal_year_eps_projections) + ")")
        for i_int in range(no_of_qtr_to_insert):
          tmp_eps_list[i_int] = qtr_eps_list[3 - i_int] * growth_factor
          logging.debug("Inserting in tmp_eps_list list at index : " + str(i_int) + " Qtr eps : " + str(qtr_eps_list[3 - i_int]) + " Projected Calcuated EPS with growth factor : " + str(tmp_eps_list[i_int]))
      else:
        growth_factor = y_plus1_fiscal_year_eps_projections / y_plus0_fiscal_year_eps_projections
        logging.debug(str(ticker) + " : Inserting two years of EPS projections. Doing First part -  with the growth factor for y_plus1 over y_plus0 : " + str(growth_factor) + " (" + str(y_plus1_fiscal_year_eps_projections) + "/" + str(y_plus0_fiscal_year_eps_projections) + ")")
        for i_int in range(0, 4):
          tmp_eps_list[i_int] = qtr_eps_list[3 - i_int] * growth_factor
          logging.debug("Inserting in tmp_eps_list list at index : " + str(i_int) + " Qtr eps : " + str(qtr_eps_list[3 - i_int]) + " Projected Calcuated EPS with growth factor : " + str(tmp_eps_list[i_int]))
        # Insert y_plus_2 after y_plus_1 has been inserted
        growth_factor = y_plus2_fiscal_year_eps_projections / y_plus1_fiscal_year_eps_projections
        logging.debug(str(ticker) + " : Inserting two years of EPS projections. Doing Second part -  with the growth factor for y_plus2 over y_plus1 : " + str(growth_factor) + " (" + str(y_plus2_fiscal_year_eps_projections) + "/" + str(y_plus1_fiscal_year_eps_projections) + ")")
        for i_int in range(4, 8):
          tmp_eps_list[i_int] = tmp_eps_list[i_int - 4] * growth_factor
          logging.debug("Inserting in tmp_eps_list list at index : " + str(i_int) + " Qtr eps : " + str(tmp_eps_list[i_int - 4]) + " Projected Calcuated EPS with growth factor : " + str(tmp_eps_list[i_int]))

      logging.debug("The tmp_eps_list list of projected eps to be inserted " + str(tmp_eps_list))
      for i_int in range(no_of_qtr_to_insert):
        logging.debug("Inserting in qtr_eps_df at index : " + str(-(i_int + 1)) + " Q_Date : " + str(fiscal_qtr_dates[i_int]) + " Q_EPS_Diluted : " + str(tmp_eps_list[i_int]))
        qtr_eps_df.loc[-(i_int + 1)] = qtr_eps_df.loc[0]
        # qtr_eps_df.loc[-(i_int+1), 'Q_Date'] =  dt.datetime.strptime(fiscal_qtr_dates[i_int], '%m/%d/%Y').date()
        qtr_eps_df.loc[-(i_int + 1), 'Q_Date'] = fiscal_qtr_dates[i_int]
        qtr_eps_df.loc[-(i_int + 1), 'Q_EPS_Diluted'] = tmp_eps_list[i_int]

      max_qtr_eps_from_insertion = max(tmp_eps_list)
      # -------------------------------------------------------------------------
      logging.debug("The qtr_eps dataframe with added projections is \n" + qtr_eps_df.to_string())
      # Now sort and reindex the q_eps_df
      # qtr_eps_df_tmp = qtr_epq_df
      # qtr_eps_df.set_index('Q_Date', inplace=True)
      # qtr_eps_df['Q_Date'] = pd.to_datetime(qtr_eps_df['Q_Date'], format="%m/%d/%Y")
      # qtr_eps_df['Q_Date'] = qtr_eps_df['Q_Date'].astype('datetime64[D]', format="%m/%d/%Y")
      qtr_eps_df['Q_Date'] = pd.to_datetime(qtr_eps_df['Q_Date'].str.strip(), format='%m/%d/%Y')

      qtr_eps_df.sort_values('Q_Date', inplace=True, ascending=False)
      qtr_eps_df.reset_index(inplace=True, drop=True)
      qtr_eps_df['Q_Date'] = pd.to_datetime(qtr_eps_df['Q_Date']).dt.strftime('%m/%d/%Y')
      logging.debug("The earnings dataframe after adding earning projection and sorting is \n" + qtr_eps_df.to_string())
      # ---------------------------------------------------------------------------
      # ---------------------------------------------------------------------------
      # See if there is anything inserted then expand out the historical df as well
      # ---------------------------------------------------------------------------
      cal_match_date_with_historical = min(calendar_date_list, key=lambda d: abs(d - latest_date_in_historical_file_dt))
      cal_match_date_with_historical_index = calendar_date_list.index(cal_match_date_with_historical)
      logging.debug(str(ticker) + " : The latest date in historical df " + str(latest_date_in_historical_file_dt) + " matched index " + str(cal_match_date_with_historical_index) + " in the calendar df")
      cal_match_date_with_insert_eps_projection = min(calendar_date_list, key=lambda d: abs(d - (latest_date_in_historical_file_dt + relativedelta(years=no_of_years_to_insert_aaii_eps_projections))))
      cal_match_date_with_insert_eps_projection_index = calendar_date_list.index(cal_match_date_with_insert_eps_projection)
      logging.debug(str(ticker) + " : The date for which EPS is inserted " + str(latest_date_in_historical_file_dt + relativedelta(years=no_of_years_to_insert_aaii_eps_projections)) + " matched index " + str(cal_match_date_with_insert_eps_projection_index) + " in the calendar df")

      for i_int in range(cal_match_date_with_insert_eps_projection_index, cal_match_date_with_historical_index):
        # logging.debug ("Inserting in historical df at index : " + str(-(i_int-cal_match_date_with_insert_eps_projection_index+1)) + " Date : " + str(calendar_date_list[i_int]))
        historical_df.loc[-(i_int - cal_match_date_with_insert_eps_projection_index + 1)] = historical_df.loc[0]
        # qtr_eps_df.loc[-(i_int+1), 'Q_Date'] =  dt.datetime.strptime(fiscal_qtr_dates[i_int], '%m/%d/%Y').date()
        historical_df.loc[-(i_int - cal_match_date_with_insert_eps_projection_index + 1), 'Date'] = calendar_date_list[i_int].strftime('%m/%d/%Y')

      logging.debug("Historical Df after inserting future dates for AAII projections is \n" + historical_df.to_string())
      # historical_df['Date'] = historical_df['Date'].astype('datetime64[D]', format="%m/%d/%Y")
      historical_df['Date'] = pd.to_datetime(historical_df['Date'].str.strip(), format='%m/%d/%Y')

      historical_df.sort_values('Date', inplace=True, ascending=False)
      historical_df.reset_index(inplace=True, drop=True)
      historical_df['Date'] = pd.to_datetime(historical_df['Date']).dt.strftime('%m/%d/%Y')
      logging.debug("Historical Df after sorting future dates for AAII projections is \n" + historical_df.to_string())

      # logging.debug(str(ticker) + " Historical df after inserting eps projection dates is " + historical_df.to_string())
  logging.info("Done adding data for " + str(no_of_years_to_insert_aaii_eps_projections) + " years in qtr_eps_df and historical df for future EPS projections as per AAII EPS df...")
  # -------------------------------------------------------------------------
  #       *****     End of AAII insertion of Projected EPS Insertion    *****
  # -------------------------------------------------------------------------

  ticker_adj_close_list = historical_df.Adj_Close.tolist()
  # date_str_list = historical_df.Date.tolist()
  date_str_list = historical_df['Date'].dropna().tolist()
  logging.debug("The date list - in raw - from historical df is\n" + str(date_str_list) + "\nit has " + str(len(date_str_list)) + " entries")
  date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in date_str_list]
  logging.debug("The date list - in datetime - from historical is\n" + str(date_list) + "\nit has " + str(len(date_list)) + " entries")
  logging.info("Read in the Historical Data...")

  # Remove all rows after the last valid value for row for Column 'Date'
  qtr_eps_df_copy = qtr_eps_df.loc[0:qtr_eps_df.Q_Date.last_valid_index()].copy()
  # This works - but removes the rows after the longest (any)column has last
  # valid value
  # qtr_eps_df_copy = qtr_eps_df.loc[0:qtr_eps_df.last_valid_index()].copy()
  qtr_eps_df = qtr_eps_df_copy.copy()
  qtr_eps_df_copy = pd.DataFrame()
  logging.debug("The Earnings df after removing all trailing NaN from the 'Q_Date' column is \n" + qtr_eps_df.to_string())

  # I can do dropna right away from the df 'Date' column but I want to make sure
  # that all the values in the Date column are in the format that can be converted
  # to Date so the try and except is more versatile
  # qtr_eps_date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in qtr_eps_df.Date.dropna().tolist()]
  try:
    qtr_eps_date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in qtr_eps_df.Q_Date.tolist()]
  except (TypeError):
    logging.error("**********                                ERROR                               **********")
    logging.error("**********  Some of the entries for Column 'Date' in the Earnings file are    **********")
    logging.error("**********  either missing (blank) or do not have proper mm/dd/yyyy format.   **********")
    logging.error("**********  Please correct the Earnings file 'Date' column and run again      **********")
    sys.exit(1)

  qtr_eps_list = qtr_eps_df.Q_EPS_Diluted.tolist()
  logging.debug("The name of the columns in the earnings file are" + str(list(qtr_eps_df.columns.values)))
  # Set the length of qtr_eps_list same as qtr_eps_date_list.
  # This gets rid of any earnings that are beyond the last date.
  # This is not a common case but could occur because of copy and paste and then
  # ignorance on the part of the user to not remove the "extra" earnings
  # This also makes sure that the eps date list and eps value list have the same
  # number of entries.
  if (len(qtr_eps_date_list) < len(qtr_eps_list)):
    del qtr_eps_list[len(qtr_eps_date_list):]
  logging.debug("The Earnings list for qtr_eps is\n" + str(qtr_eps_list) + "\nand the number of elements are " + str(len(qtr_eps_list)))

  # Check if now the qtr_eps_list still has any undefined elements...flag an error and exit
  # This will indicate any empty cells are either the beginning or in the middle of the eps
  # column in the csv
  if (sum(math.isnan(x) for x in qtr_eps_list) > 0):
    logging.error("**********                                ERROR                               **********")
    logging.error("**********  There seems to be either blank cells for Earnings or their        **********")
    logging.error("**********  format is undefined. Please correct the rerun the script          **********")
    sys.exit()

  # So - if we are successful till this point - we have made sure that
  # 1. There are no nan in the date list
  # 2. There are no nan in the eps list
  # 3. Number of elements in the qtr_eps_date_list are equal to the number of
  #    element in the qtr_eps_list
  logging.info("Read in the Earnings Data...")
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Price Target section
  # ---------------------------------------------------------------------------
  price_target_dict_needs_rename = {}
  price_target_date_list_dt = []
  price_target_amount_list = []
  pt_print_str = ""
  if ticker in price_target_json.keys():
    price_target_dict_needs_rename = price_target_json[ticker]
    logging.debug("Price target data for " + str(ticker) + " in Price Target Json : \n" + str(price_target_json[ticker]['Price_Target']))
    len_price_target = len(price_target_json[ticker]["Price_Target"])
    for i in range(len_price_target):
      i_price_target_date = price_target_json[ticker]["Price_Target"][i]["Date"]
      i_price_target_amount = price_target_json[ticker]["Price_Target"][i]["Target"].replace(',','')
      try:
        price_target_date_list_dt.append(dt.datetime.strptime(i_price_target_date, "%m/%d/%Y").date())
        price_target_amount_list.append(float(i_price_target_amount))
      except (ValueError):
        logging.error(
          "\n***** Error : Either the Dates or the Price Target Amount are not in proper format for Price_Target in Price Target json file.\n"
          "***** Error : The Dates should be in the format %m/%d/%Y and the Adjust Amount should be a int/float\n"
          "***** Error : Found somewhere in : Date : " + str(i_price_target_date) + ", Price Target : " + str(i_price_target_amount))
        sys.exit(1)

    # -----------------------------------------------------
    # Check for duplicate dates and ask the user to fix
    # duplicate dates - This should be rare, and if it happens
    # then the user needs to clean the json file
    # -----------------------------------------------------
    logging.debug("The price Target datelist is : " + str(price_target_date_list_dt))
    if (len(price_target_date_list_dt) != len(set(price_target_date_list_dt))):
      duplicate_items_list = [k for k,v in Counter(price_target_date_list_dt).items() if v>1]
      logging.error ("There are some duplicate dates in the Price_Target in Price Target json file...Please correct and rerun")
      logging.error ("Duplicates : " + str(duplicate_items_list))
      sys.exit(1)
    # -----------------------------------------------------

    # -----------------------------------------------------
    # Convert the date and the target amount arrays to np arrays
    # Then sort the date array - that will give us the index of
    # the sorted array. Then sort the target amount array with
    # the same indexes so they are sorted "in sync"
    # -----------------------------------------------------
    price_target_date_list_dt_np = np.array(price_target_date_list_dt)
    price_target_amount_list_np = np.array(price_target_amount_list)
    price_target_date_list_sorted_idx = np.flip(np.array(price_target_date_list_dt).argsort())
    logging.debug("The SORTED PT datelist index : " + str(price_target_date_list_sorted_idx))

    price_target_date_list_sorted_dt = price_target_date_list_dt_np[price_target_date_list_sorted_idx]
    price_target_amount_list_sorted = price_target_amount_list_np[price_target_date_list_sorted_idx]
    logging.debug("The SORTED PT datelist  : " + str(price_target_date_list_sorted_dt))
    logging.debug("The SORTED PT amount    : " + str(price_target_amount_list_sorted))
    # -----------------------------------------------------

    # -----------------------------------------------------
    # Prepare a string that will be put on the chart
    # -----------------------------------------------------
    # For now only display the latest 4 price targets, when can get
    # sophisticated as we see more price targets. For that we have
    # to do some splicing of the date_list to find the difference
    # in the various dates available and then do the math - so
    # in a year I may update the chart 12 times (approximately once a
    # month, but we may not want to display just the last three entries
    # of PT, I may want to do back and display last 2 and then going
    # back and quarter and then going back a year...it is not clear
    # at this point what would be good do display...so as I mentioned
    # above, it will evolve
    no_of_pt_to_display = len(price_target_amount_list_sorted)
    if no_of_pt_to_display > 7:
      no_of_pt_to_display = 7

    for i_idx in range(no_of_pt_to_display):
      logging.debug("Index " + str(i_idx) + ", Date  " + str(price_target_date_list_sorted_dt[i_idx]) + ", value " + str(price_target_amount_list_sorted[i_idx]))
      pt_print_str = pt_print_str + str(price_target_date_list_sorted_dt[i_idx]) + ", PT : " + str(price_target_amount_list_sorted[i_idx])
      if i_idx != no_of_pt_to_display-1:
        pt_print_str = pt_print_str + "\n"
    logging.debug("The PT string is " + str(pt_print_str))
  # ---------------------------------------------------------------------------





  # =============================================================================
  # Handle splits before proceeding as splits can change the qtr_eps
  # =============================================================================
  # todo : Test out various cases of splits so that the code is robust
  split_dates = list()
  split_multiplier = list()
  # print("Tickers in json data: ", config_json.keys())
  if (ticker not in config_json.keys()):
    logging.debug("json data for " + ticker + "does not exist in" + configuration_json_file + "file")
  else:
    if ("Splits" in config_json[ticker]):
      # if the length of the keys is > 0
      if (len(config_json[ticker]["Splits"].keys()) > 0):
        split_keys = config_json[ticker]["Splits"].keys()
        logging.debug("Split Date list is: " + str(split_keys))
        for i_key in split_keys:
          logging.debug("Split Date : " + str(i_key) + ", Split Factor : " + str(config_json[ticker]["Splits"][i_key]))
          try:
            split_dates.append(dt.datetime.strptime(str(i_key), "%m/%d/%Y").date())
          except (ValueError):
            logging.error("\n***** Error : The split Date: " + str(i_key) +
                          "does not seem to be right. Should be in the format %m/%d/%Y...please check *****")
            sys.exit(1)
          try:
            (numerator, denominator) = config_json[ticker]["Splits"][i_key].split(":")
            split_multiplier.append(float(denominator) / float(numerator))
          except (ValueError):
            logging.error("\n***** Error : The split factor: " + str(config_json[ticker]["Splits"][i_key]) + "for split date :" + str(i_key) +
                          "does not seem to have right format [x:y]...please check *****")
            sys.exit(1)
        for i in range(len(split_dates)):
          qtr_eps_list_mod = qtr_eps_list.copy()
          logging.debug("Split Date :" + str(split_dates[i]) + " Multiplier : " + str(split_multiplier[i]))
          for j in range(len(qtr_eps_date_list)):
            if (split_dates[i] > qtr_eps_date_list[j]):
              qtr_eps_list_mod[j] = round(qtr_eps_list[j] * split_multiplier[i], 4)
              logging.debug("Earnings date " + str(qtr_eps_date_list[j]) + " is older than split date. " +
                            "Changed " + str(qtr_eps_list[j]) + " to " + str(qtr_eps_list_mod[j]))
          qtr_eps_list = qtr_eps_list_mod.copy()
        logging.info("Processed Splits for date(s) : " + str(split_dates) + ",  Mulitplier ratio(s) : " + str(split_multiplier))
      else:
        logging.debug("\"Splits\" exits but seems empty for " + ticker)
    else:
      logging.debug("\"Splits\" does not exist for " + ticker)
  # =============================================================================

  # =============================================================================
  # Check if the dividend file exists
  # =============================================================================
  pays_dividend = 0
  dividend_file = dir_path + "\\" + dividend_dir + "\\" + ticker + "_dividend.csv"
  if (os.path.exists(dividend_file) is True):
    pays_dividend = 1
    dividend_df = pd.read_csv(dir_path + "\\" + dividend_dir + "\\" + ticker + "_dividend.csv")
    # print (dividend_df)
    dividend_date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in dividend_df.Date.dropna().tolist()]
    dividend_list = dividend_df.Amount.tolist()
    logging.debug("The date list for Dividends is\n" + str(dividend_date_list) + "\nand the number of elements are" + str(len(dividend_date_list)))
    logging.debug("The Amounts for dividends is " + str(dividend_list))
    logging.info("Read in the Dividend Data...")
  # =============================================================================

  # ---------------------------------------------------------------------------
  # Calculate analyst accuracy
  # First find out the date from the last reported earnings
  # ---------------------------------------------------------------------------
  if 'Q_EPS_Projections_Date_0' in qtr_eps_df.columns:
    # Get the value from row0 of that column
    qtr_eps_projections_date_0 = dt.datetime.strptime(qtr_eps_df.iloc[0]['Q_EPS_Projections_Date_0'], '%m/%d/%Y').date()
  else:
    logging.error("The Updated column for Earnings does not exist in the Qtr EPS df...this will soon change into error ")
    # eps_projections_date_0 = dt.datetime.strptime(str(ticker_master_tracklist_series['Last_Updated_EPS_Projections']),'%Y-%m-%d %H:%M:%S').date()
  qtr_eps_projections_date_1 = 'NA'
  if 'Q_EPS_Projections_Date_1' in qtr_eps_df.columns:
    # Get the value from row0 of that column
    try:
      qtr_eps_projections_date_1 = dt.datetime.strptime(qtr_eps_df.iloc[0]['Q_EPS_Projections_Date_1'],'%m/%d/%Y').date()
    except:
      qtr_eps_projections_date_1 = 'NA'

  # Check -  _date_0 should not be in the future
  if (qtr_eps_projections_date_0 != 'NA'):
    if (qtr_eps_projections_date_0 > dt.date.today()):
      logging.error("******************************************************************************")
      logging.error("The Earnings Projections update date (in col : Q_EPS_Projections_Date_0) ==> " + str(qtr_eps_projections_date_0) + " <===")
      logging.error("is the future. It is likely just a typo while you were updating the earnings file")
      logging.error("                       Please correct and rerun")
      logging.error("******************************************************************************")
      sys.exit(1)

  # Check -  _date_0 should be newer than the _date_1. This will catch if I forget to update the date
  if (qtr_eps_projections_date_1 != 'NA'):
    if (qtr_eps_projections_date_0 <= qtr_eps_projections_date_1):
      logging.error("The Earnings Projections update date (in col : Q_EPS_Projections_Date_0) ==> " + str(qtr_eps_projections_date_0) + " in the earnings csv file ")
      logging.error("should be later than the Earnings Projection update date from before that (in col :  Q_EPS_Projections_Date_1) ==> " + str(qtr_eps_projections_date_1))
      logging.error("*****     Did you forget to update the date in Column : Q_EPS_Projections_Date_0, while updating earnings csv?     *****")
      sys.exit(1)

  qtr_eps_projections_list = qtr_eps_df['Q_EPS_Projections_1'].tolist()
  logging.debug("The date list for qtr_eps is\n" + str(qtr_eps_date_list) + "\nand the number of elements are " + str(len(qtr_eps_date_list)))
  logging.debug("The Earnings list for qtr_eps is\n" + str(qtr_eps_list) + "\nand the number of elements are " + str(len(qtr_eps_list)))
  logging.debug("The Earnings Projections list for qtr_eps is\n" + str(qtr_eps_projections_list) + "\nand the number of elements are " + str(len(qtr_eps_projections_list)))
  logging.info("The EPS Projections were last updated on : " + str(qtr_eps_projections_date_0) + " and before that on " + str(qtr_eps_projections_date_1))

  # If the last reported Earnings date is later than the Latest earning projections update date
  # then that is errored out here
  # it means that Sundeep did not update the earnings projections but updated the actual reported
  # earnings date - and while that does not violate anything - but that is NOT how things should be done.
  # The earnings projection update date should always be newer (or equal to, if the projection were
  # updated on the same day earnings were reported) than the acutal reported earnings date
  # It is likely the result of a typo in the earnings file - point it out here and let the user
  # look at the earnings file and see what is going on
  if (eps_report_date > qtr_eps_projections_date_0):
    logging.error("")
    logging.error("********************************************************************************")
    logging.error("The Last Reported Earnings date is                : " + str(eps_report_date))
    logging.error("Projected Earnings were last updated on           : " + str(qtr_eps_projections_date_0))
    logging.error("===== The projected Earnings date should not be older than Last Earnings report date =====")
    logging.error("Likely : Did you forget to update the Projected Earnings date in the earnings file???")
    logging.error("Please look at the dates in the earnings file and rerun...")
    logging.error("********************************************************************************")
    sys.exit()

  # Check if the eps projections list has atleat "x" years of data
  # eps_date_list_eps_report_date_match = min(qtr_eps_date_list, key=lambda d: abs(d - eps_report_date))
  # eps_date_list_eps_report_date_index = qtr_eps_date_list.index(eps_date_list_eps_report_date_match)
  # logging.debug("The match date for Last reported Earnings date : " + str(eps_report_date) + " in the Earnings df is : " + str(eps_date_list_eps_report_date_match) + " at index " + str(eps_date_list_eps_report_date_index))
  # # If the date match in the eps_date_list is a date in the future date (that can happen if
  # # the eps_report_date is more than 45 days after the quarter date. In this case we need to
  # # move the match date index back by a quarter (by adding 1 to it - as the index starts
  # # from 0 for the futuremost date)
  # if ((eps_date_list_eps_report_date_match >= dt.date.today()) or (eps_date_list_eps_report_date_match >= eps_report_date)):
  #   eps_date_list_eps_report_date_index += 1
  #   eps_date_list_eps_report_date_match = qtr_eps_date_list[eps_date_list_eps_report_date_index]
  #   logging.debug("Adjusting the match date to " + str(eps_date_list_eps_report_date_match) + " at index " + str(eps_date_list_eps_report_date_index))
  eps_date_list_eps_report_date_match, eps_date_list_eps_report_date_index = qtr_date_and_index_matching_eps_report_date(qtr_eps_date_list, eps_report_date)

  historical_date_list_eps_report_date_match = min(date_list,key=lambda d: abs(d - eps_date_list_eps_report_date_match))
  last_black_diamond_index = date_list.index(historical_date_list_eps_report_date_match)
  logging.debug("The match date for Last reported Earnings date : " + str(eps_report_date) + " in the Historical df is : " + str(historical_date_list_eps_report_date_match) + " at index " + str(last_black_diamond_index))

  # Now we know the last quarter earning date index, determine the number of years for
  # which we want to analyze analysts projection accuracy. Default is 2
  # If there are too few entries, which can happen for very new IPOs like ALAB,
  # then reduce the number of years to 1
  # We need atleat one year or earnings available for this to work
  # If you are overzealous and still want to plot a brand new IPO, then please
  # make up the earnings for one year
  years_of_analyst_eps_to_analyze = 2
  # logging.debug("The total number of index in qtr_eps_date_list are : " + str(len(qtr_eps_date_list)) < )
  # If less than two years of earnings are available, then reducde the
  # number of years for which to calculate the variation to 1
  if ( ((len(qtr_eps_date_list)-1) - eps_date_list_eps_report_date_index) < 8):
    logging.info("*** Reduced the number of years for which analyst projections would be analysed to 1 ***")
    years_of_analyst_eps_to_analyze = 1
  # Delete all entries from eps projection list that are older than the date we need for our calculations
  del qtr_eps_projections_list[eps_date_list_eps_report_date_index + years_of_analyst_eps_to_analyze * 4:]
  logging.debug("Will keep (" + str(years_of_analyst_eps_to_analyze) + ") years of Analysts Projections to Analyze")
  logging.debug("The Shortened Earnings Projections list for qtr_eps is\n" + str(qtr_eps_projections_list) + "\nand the number of elements are " + str(len(qtr_eps_projections_list)))
  if (sum(math.isnan(x) for x in qtr_eps_projections_list) > 0):
    logging.error("**********             $$$$$     BIG WARNING      $$$$$                                 **********")
    logging.error("**********  There seems to be either blank cells for Projected Earnings or their        **********")
    logging.error("**********  format is undefined (In Col : Q_EPS_Projections_1) in earnings file         **********")
    logging.error("**********  Please correct/update that column, if you have the data and rerun           **********")
    logging.error("**********  For now will copy the qps to projected eps list                             **********")
    qtr_eps_projections_list = qtr_eps_list.copy()

  # We have the right number of entries available from past eps projections (analysts projections)
  # Now Do the math to calculate the variation for each past quarter b/w actual earnings and
  # projected earning and store it in a vairiation list
  logging.debug("Now calculating EPS variation b/w actual and Analysts projections")
  # Initialize the variation list to all 0s first
  eps_projections_variation_list = [0 for i in range(eps_date_list_eps_report_date_index + years_of_analyst_eps_to_analyze * 4)]
  for i_int in range(eps_date_list_eps_report_date_index, eps_date_list_eps_report_date_index + years_of_analyst_eps_to_analyze * 4):
    variation = (qtr_eps_list[i_int] - qtr_eps_projections_list[i_int]) / qtr_eps_projections_list[i_int] * 100
    logging.debug("Report Date : " + str(qtr_eps_date_list[i_int]) + " Actual QTR EPS : " + str(qtr_eps_list[i_int]) + " Projected QTR EPS : " + str(qtr_eps_projections_list[i_int]) + " Variation : " + str(variation) + " percent")
    eps_projections_variation_list[i_int] = variation

  logging.debug("The EPS Variations list raw is : " + str(eps_projections_variation_list))
  # Now smooth out the variation list and create a accuracy list from it
  analyst_eps_projections_accuracy_list = [1 for i in range(len(qtr_eps_date_list))]
  for i_int in range(years_of_analyst_eps_to_analyze):
    # for each quarter in the year - get the variation and divide by 4 to average out the variations
    # We will treat this as a varition for all the quarters in the year and then assign this to
    # all the quarters below
    smoothed_variation = (eps_projections_variation_list[eps_date_list_eps_report_date_index + i_int * 4 + 0] + \
                          eps_projections_variation_list[eps_date_list_eps_report_date_index + i_int * 4 + 1] + \
                          eps_projections_variation_list[eps_date_list_eps_report_date_index + i_int * 4 + 2] + \
                          eps_projections_variation_list[eps_date_list_eps_report_date_index + i_int * 4 + 3]) / 4
    smoothed_analyst_accuracy = 1 + smoothed_variation / 100
    logging.debug("For year " + str(i_int + 1) + " smoothed variation is : " + str(smoothed_variation) + " Smoothed analyst accuracy is : " + str(smoothed_analyst_accuracy))
    # If this is the (latest) first year then store all the indecies upto the first year with
    # the cacluated accuracy. This is the number that will be used to make the future accuracy channel
    if (i_int == 0):
      for j_int in range(eps_date_list_eps_report_date_index):
        analyst_eps_projections_accuracy_list[j_int] = smoothed_analyst_accuracy

    for j_int in range(4):
      analyst_eps_projections_accuracy_list[eps_date_list_eps_report_date_index + i_int * 4 + j_int] = smoothed_analyst_accuracy

  logging.debug("The Analyst EPS Projections accuracy List is " + str(analyst_eps_projections_accuracy_list))

  logging.info("Created Analyst Accuracy data")
  # ---------------------------------------------------------------------------

  # =============================================================================
  # Create a qtr_eps_expanded and dividend_expanded list
  # We are here trying to create the list that has the same number of elements
  # as the historical date_list and only the elements that have the Quarter EPS
  # / Dividend have valid values, other values in the expanded list are nan...and
  # hence the expanded lists are initially initialized to nan
  # =============================================================================
  qtr_eps_expanded_list = []
  dividend_expanded_list = []
  for i in range(len(date_list)):
    qtr_eps_expanded_list.append(float('nan'))
    if (pays_dividend == 1):
      dividend_expanded_list.append(float('nan'))

  for qtr_eps_date in qtr_eps_date_list:
    curr_index = qtr_eps_date_list.index(qtr_eps_date)
    # print("Looking for ", qtr_eps_date)
    match_date = min(date_list, key=lambda d: abs(d - qtr_eps_date))
    logging.debug("The matching date in historical datelist for QTR EPS Date: " + str(qtr_eps_date) + " is " + str(match_date) + " at index " +
                  str(date_list.index(match_date)) + " and the QTR EPS is " + str(qtr_eps_list[curr_index]))
    qtr_eps_expanded_list[date_list.index(match_date)] = qtr_eps_list[curr_index]
  logging.debug("The expanded qtr eps list is " + str(qtr_eps_expanded_list) + "\nand the number of elements are" + str(len(qtr_eps_expanded_list)))
  logging.info("Prepared the Expanded Q EPS List")

  if (pays_dividend == 1):
    if (math.isnan(ticker_config_series['Dividend_Multiplier_Factor'])):
      dividend_multiplier = 1.0
    else:
      dividend_multiplier = float(ticker_config_series['Dividend_Multiplier_Factor'])
    dividend_list_multiplied = [x * dividend_multiplier for x in dividend_list]
    logging.debug("Dividend List is" + str(dividend_list))
    logging.debug("Multiplied Divided List is" + str(dividend_list_multiplied))

    for dividend_date in dividend_date_list:
      curr_index = dividend_date_list.index(dividend_date)
      # print("Looking for ", dividend_date)
      match_date = min(date_list, key=lambda d: abs(d - dividend_date))
      logging.debug("The matching date in historical datelist for Dividend Date: " + str(dividend_date) + " is " +
                    str(match_date) + " at index " + str(date_list.index(match_date)) +
                    " and the Dividend is" + str(dividend_list_multiplied[curr_index]))
      dividend_expanded_list[date_list.index(match_date)] = dividend_list_multiplied[curr_index]

    logging.debug("The expanded Dividend list is " + str(dividend_expanded_list) + \
                  "\nand the number of elements are " + str(len(dividend_expanded_list)))
    logging.info("Prepared the Expanded Dividend List")
  # =============================================================================

  # =============================================================================
  # There are many yr eps list
  # 1. The yr eps list that has all the earnings
  # Create annual eps date list and then create
  # Expanded annual EPS list just like the expanded Quarter EPS list was created
  # However the expanded Annual EPS list is really three lists...to create a different
  # series in the plot/graph later
  # yr_eps_expanded_list - This will end up to create the price channels
  # yr_past_eps_expanded_list - contains only the yr eps that is older than the
  #   current date - This will end up as black diamonds in the chart
  # yr_projected_eps_expanded_list - contains only the yr epx that is newer
  #   than the current date - This will end up as white diamonds in the chart
  # =============================================================================
  # =============================================================================
  # Create the Annual EPS list from the Quarter EPS list.
  # The last 3 elemnts of the annual EPS are going to be blank because the last annual EPS corresponds
  # the the last but 4th Quarter EPS
  # =============================================================================
  # Remove the last 3 dates from the qtr_eps_date_list to create yr_eps_date_list
  yr_eps_date_list = qtr_eps_date_list[0:len(qtr_eps_date_list) - 3].copy()
  i_int = 0
  yr_eps_list = list()
  while (i_int < (len(qtr_eps_list) - 3)):
    yr_average_eps = (qtr_eps_list[i_int] + \
                      qtr_eps_list[i_int + 1] + \
                      qtr_eps_list[i_int + 2] + \
                      qtr_eps_list[i_int + 3]) / 4

    logging.debug("Iteration # " + str(i_int).ljust(2) + ", Date : " + str(yr_eps_date_list[i_int]) + " : Quartely EPS(es) : Annual EPS " + \
                  str(qtr_eps_list[i_int]) + " " + \
                  str(qtr_eps_list[i_int + 1]) + " " + \
                  str(qtr_eps_list[i_int + 2]) + " " + \
                  str(qtr_eps_list[i_int + 3]) + " : " + \
                  str(yr_average_eps))
    yr_eps_list.append(yr_average_eps)
    i_int += 1
  logging.debug("Annual EPS List " + str(yr_eps_list) + "\nand the number of elements are " + str(len(yr_eps_list)))
  logging.info("Prepared the YR EPS List")
  # ---------------------------------------------------------------------------
  # Adjust the yr_eps if the user wants to...This happens if there was an
  # unusual quarter. The data is availalbe in the json file
  # ---------------------------------------------------------------------------
  yr_eps_adj_start_date_list = []
  yr_eps_adj_stop_date_list = []
  yr_eps_adj_amount_list = []
  len_yr_eps_adj = 0
  annual_eps_adjust_json = 0

  # Read the json file to get the adjustments for the yr eps in lists
  if (ticker not in config_json.keys()):
    logging.debug("json data for " + str(ticker) + " does not exist in " + str(configuration_json_file) + " file")
  else:
    if ("Annual_EPS_Adjust" in config_json[ticker]):
      annual_eps_adjust_json = 1
      len_yr_eps_adj = len(config_json[ticker]["Annual_EPS_Adjust"])
      logging.debug("The number of YR EPS adjustments specified " + str(len_yr_eps_adj))
      for i in range(len_yr_eps_adj):
        i_start_date = config_json[ticker]["Annual_EPS_Adjust"][i]["Start_Date"]
        i_stop_date = config_json[ticker]["Annual_EPS_Adjust"][i]["Stop_Date"]
        i_adj_amount = config_json[ticker]["Annual_EPS_Adjust"][i]["Adj_Amount"]
        try:
          yr_eps_adj_start_date_list.append(dt.datetime.strptime(i_start_date, "%m/%d/%Y").date())
          yr_eps_adj_stop_date_list.append(dt.datetime.strptime(i_stop_date, "%m/%d/%Y").date())
          yr_eps_adj_amount_list.append(float(i_adj_amount))
        except (ValueError):
          logging.error(
            "\n***** Error : Either the Start/Stop Dates or the Adjust Amount are not in proper format for Upper_Price_Channel_Adj in Configuration json file.\n"
            "***** Error : The Dates should be in the format %m/%d/%Y and the Adjust Amount should be a int/float\n"
            "***** Error : Found somewhere in :" + str(i_start_date) + str(i_stop_date) + str(i_adj_amount))
          sys.exit(1)

  logging.debug("The yr eps adjust Start Date List " + str(yr_eps_adj_start_date_list))
  logging.debug("The yr eps adjust Stop Date List" + str(yr_eps_adj_stop_date_list))
  logging.debug("The yr eps adjust List" + str(yr_eps_adj_amount_list))
  # ---------------------------------------------------------------------------
  # Now we have 3 lists - start date list, stop date list and the adjustment amount list
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Now Process the yr_eps_adj_* lists created above  to make the adjustments
  # to the yr eps.
  # We will create a separate list yr_eps_adj_list - this list will be used to
  #   create price channel lines later
  # The original list - which will be used to create two lists - past and future
  #   is used to plot
  # ---------------------------------------------------------------------------
  yr_eps_adj_date_list = yr_eps_date_list.copy()
  yr_eps_adj_list = yr_eps_list.copy()
  yr_eps_has_been_adj_index_list = []
  if (annual_eps_adjust_json == 1):
    for i_idx in range(len_yr_eps_adj):
      yr_eps_adj_start_date = yr_eps_adj_start_date_list[i_idx]
      yr_eps_adj_stop_date = yr_eps_adj_stop_date_list[i_idx]
      yr_eps_adj_amount = yr_eps_adj_amount_list[i_idx]
      for i_date in yr_eps_adj_date_list:
        if (yr_eps_adj_start_date <= i_date <= yr_eps_adj_stop_date):
          i_index: int = yr_eps_adj_date_list.index(i_date)
          logging.debug("Date " + str(i_date) + " lies between EPS Adjust start Date " + str(yr_eps_adj_start_date) +
                        " and EPS Adjust stop Date " + str(yr_eps_adj_stop_date) + " at index " + str(i_index))
          yr_eps_adj_list[i_index] = yr_eps_adj_list[i_index] + yr_eps_adj_amount
          yr_eps_has_been_adj_index_list.append(i_index)

    logging.debug("The original yr EPS is " + str(yr_eps_list))
    logging.debug("The adjusted yr EPS is " + str(yr_eps_adj_list))
    logging.debug("The adjustments has been done at indices " + str(yr_eps_has_been_adj_index_list))
    logging.info("Prepared the Adjusted YR EPS List")
    # ---------------------------------------------------------------------------
    # Create a list that ONLY has the yr_eps that has been adjusted (in other words
    # the yr_eps values that have been adjusted above - This will be used to plot
    # as a separate plot - for easier visualization that the user has adjusted
    # yr_eps
    # ---------------------------------------------------------------------------
    yr_eps_adj_slice_list = []
    yr_eps_adj_slice_date_list = []
    for i_idx in range(len(yr_eps_adj_list)):
      if (i_idx in yr_eps_has_been_adj_index_list):
        # logging.debug("The YR EPS at index " + str(i_idx) + " was adjusted")
        yr_eps_adj_slice_date_list.append(yr_eps_adj_date_list[i_idx])
        yr_eps_adj_slice_list.append(yr_eps_adj_list[i_idx])

    if (annual_eps_adjust_json == 1):
      logging.debug("The date list of adjusted slice of the YR EPS is " + str(yr_eps_adj_slice_date_list))
      logging.debug("The values of YR EPS that were adjusted are " + str(yr_eps_adj_slice_list))
      logging.info("Prepared the Adjusted Slice YR EPS List")

  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # So - in the section above, we have created three yr_eps
  #   (and their corresponding date) lists -
  # 1. The normal yr_eps list that contains all the yr_eps directly calculated from
  #   qtr_eps
  # 2. The yr_eps_adj list that is same as yr_eps_list except that it some of the
  #   eps adjusted to what user specified from json file.
  # 3. The yr_eps_adj_slice_list that ONLY has the yr_eps that was modified based
  #   on the user input from jsom file
  #
  # Now that we have all the 3 versions of yr_eps lists - start creating expanded
  # versions of the list
  # Here the normal yr_eps list will be divided into two (expanded lists)
  # 4. One for all the dates that are in the past (older than current date)
  # 5. One for all the dates that are in the future (younger dates)
  # This is done so that we can have black diamonds (for older dates) and
  # white diamomds (for younger dates)
  # ---------------------------------------------------------------------------
  yr_eps_expanded_list = []
  yr_eps_adj_expanded_list = []
  yr_past_eps_expanded_list = []
  yr_projected_eps_expanded_list = []
  white_diamond_index_list = []
  for i in range(len(date_list)):
    yr_eps_expanded_list.append(float('nan'))
    yr_eps_adj_expanded_list.append(float('nan'))
    yr_past_eps_expanded_list.append(float('nan'))
    yr_projected_eps_expanded_list.append(float('nan'))

  logging.debug("\n\nNow working on Expanding the YR EPS Lists\n")
  logging.debug("The historical datelist is \n" + str(date_list))
  for yr_eps_date in yr_eps_date_list:
    curr_index = yr_eps_date_list.index(yr_eps_date)
    # logging.debug("Looking for " + str(yr_eps_date))
    match_date = min(date_list, key=lambda d: abs(d - yr_eps_date))
    logging.debug("The matching date for YR EPS date " + str(yr_eps_date) + " is " + str(match_date) +
                  " in historical datalist at index " + str(date_list.index(match_date)) + " and the YR EPS is " + str(yr_eps_list[curr_index]))
    yr_eps_expanded_list[date_list.index(match_date)] = yr_eps_list[curr_index]
    yr_eps_adj_expanded_list[date_list.index(match_date)] = yr_eps_adj_list[curr_index]
    # Check if the matching data is in the future or if the match date is greater than
    # when the company last reported earnings - Then it is white diamond
    if ((match_date >= dt.date.today()) or (match_date >= eps_report_date)):
      logging.debug("The matching date is in the future...so adding to the projected eps expanded list - White diamond")
      yr_projected_eps_expanded_list[date_list.index(match_date)] = yr_eps_list[curr_index]
      white_diamond_index_list.append(date_list.index(match_date))
    else:
      logging.debug("The matching date is in the past...so adding to the past eps expanded list - Black diamond")
      yr_past_eps_expanded_list[date_list.index(match_date)] = yr_eps_list[curr_index]
  logging.debug("The Normal Expanded Annual EPS List is: " + str(yr_eps_expanded_list))
  logging.info("Prepared the YR EPS Expanded List, YR Past EPS Expanded List (black Diamonds) and YR Projected EPS List (white Diamonds)")
  logging.debug("The white Diamond index list is :" + str(white_diamond_index_list))
  # We have white_diamond index list here - Note that the index list is in the order of
  # last white diamond (far future) to first while diamond (near future). Append the
  # last black diamond (the latest quarter for eps report date). So now we have the
  # index list that point to the dates - starting from the far white diamond to the
  #  first black diamond (the lastest reported earnings date)
  analyst_channel_adjust_index_list = white_diamond_index_list.copy()
  analyst_channel_adjust_index_list.append(last_black_diamond_index)
  logging.debug("The Analyst Channel Adjust Index list is :" + str(analyst_channel_adjust_index_list))

  yr_eps_adj_slice_date_expanded_list = []
  yr_eps_adj_slice_expanded_list = []
  for i in range(len(date_list)):
    yr_eps_adj_slice_date_expanded_list.append(float('nan'))
    yr_eps_adj_slice_expanded_list.append(float('nan'))

  if (annual_eps_adjust_json == 1):
    for yr_eps_adj_slice_date in yr_eps_adj_slice_date_list:
      curr_index = yr_eps_adj_slice_date_list.index(yr_eps_adj_slice_date)
      # logging.debug("Looking for " + str(yr_eps_adj_slice_date))
      match_date = min(date_list, key=lambda d: abs(d - yr_eps_adj_slice_date))
      logging.debug("The matching date for Adjusted YR EPS date " + str(yr_eps_adj_slice_date) + " is " +
                    str(match_date) + " in historical datelist at index " + str(date_list.index(match_date)) +
                    " and the Adjusted YR EPS is " + str(yr_eps_adj_slice_list[curr_index]))
      yr_eps_adj_slice_expanded_list[date_list.index(match_date)] = yr_eps_adj_slice_list[curr_index]
      yr_eps_adj_slice_date_expanded_list[date_list.index(match_date)] = yr_eps_adj_slice_date_list[curr_index]
    logging.info("Prepared the YR EPS Adjusted Slice Expanded List (Golden Diamonds)")

  # I am not sure why I wanted this but seems like a good thing to be able to make
  # a dataframe from lists. This is not used anywhere in the code ahead...so commented
  # out for now7
  # yr_eps_list_tmp = yr_eps_list.copy()
  # yr_eps_list_tmp.append('Not_calculated')
  # yr_eps_list_tmp.append('Not_calculated')
  # yr_eps_list_tmp.append('Not_calculated')
  # This is good. This works
  # earnings_df = pd.DataFrame(np.column_stack([qtr_eps_date_list, qtr_eps_list, yr_eps_list_tmp]),
  #                                columns=['Date', 'Q EPS', 'Annual EPS'])
  # print ("The Earnings DF is ", earnings_df)
  # =============================================================================

  # =============================================================================
  # Create the price channels using the yr eps sdj list
  # This section also take json input if the user wants to modify the price channels
  # =============================================================================
  # This variable is added to the adjustments that are done to the channels because
  # this is also the nubmer of days by which the channels get shifted left (or these
  #  are the number of nan entries that are inserted in the channel list
  days_in_2_qtrs = 126

  # Get the upper and lower guide lines separation from the annual EPS
  # Use the default value of .1 (10 cents) for separation
  if (math.isnan(ticker_config_series[chart_type_idx + '_Upper_Price_Channel'])):
    upper_price_channel_list_unsmooth = [float(eps) + .1 for eps in yr_eps_adj_expanded_list]
  else:
    upper_price_channel_separation = float(ticker_config_series[chart_type_idx + '_Upper_Price_Channel'])
    upper_price_channel_list_unsmooth = [float(eps) + upper_price_channel_separation for eps in yr_eps_adj_expanded_list]

  if (math.isnan(ticker_config_series[chart_type_idx + '_Lower_Price_Channel'])):
    lower_price_channel_list_unsmooth = [float(eps) - .1 for eps in yr_eps_adj_expanded_list]
  else:
    lower_price_channel_separation = float(ticker_config_series[chart_type_idx + '_Lower_Price_Channel'])
    lower_price_channel_list_unsmooth = [float(eps) - lower_price_channel_separation for eps in yr_eps_adj_expanded_list]

  logging.debug("The upper channel unsmooth list is : " + str(upper_price_channel_list_unsmooth))
  logging.debug("The lower channel unsmooth list is : " + str(lower_price_channel_list_unsmooth))
  upper_price_channel_list = smooth_list(upper_price_channel_list_unsmooth)
  lower_price_channel_list = smooth_list(lower_price_channel_list_unsmooth)
  logging.debug("The upper channel smooth is " + str(upper_price_channel_list) + "\nand the number of element is " + str(len(upper_price_channel_list)))
  logging.debug("The lower channel smooth is " + str(lower_price_channel_list) + "\nand the number of element is " + str(len(lower_price_channel_list)))
  logging.info("Prepared the Upper and Lower Price Channels")

  # ---------------------------------------------------------------------------
  # Get the adjustments that need to be done and do the price channels
  # First read from the json file to know how may adjustments need to be done
  # for the upper and lower price channels and store them in their separate lists
  # respectively. After than process those separate list to make actual adjustments
  # to the channel lines
  # ---------------------------------------------------------------------------
  # It is better to define the list and the variables that are getting created in the read of the json
  # file...as the for loops that use the lists are separated out from the creation of the lists
  upper_price_channel_adj_start_date_list = []
  upper_price_channel_adj_stop_date_list = []
  upper_price_channel_adj_amount_list = []
  len_upper_price_channel_adj = 0
  lower_price_channel_adj_start_date_list = []
  lower_price_channel_adj_stop_date_list = []
  lower_price_channel_adj_amount_list = []
  len_lower_price_channel_adj = 0

  # Read the json file to get the adjustments for the upper and lower channels in
  # their respective list
  if (ticker not in config_json.keys()):
    logging.debug("json data for " + str(ticker) + " does not exist in " + str(configuration_json_file) + "file")
  else:
    if ("Upper_Price_Channel_Adj" in config_json[ticker]):
      len_upper_price_channel_adj = len(config_json[ticker]["Upper_Price_Channel_Adj"])
      logging.debug("The number of Upper channel adjustments specified : " + str(len_upper_price_channel_adj))
      for i in range(len_upper_price_channel_adj):
        i_start_date = config_json[ticker]["Upper_Price_Channel_Adj"][i]["Start_Date"]
        i_stop_date = config_json[ticker]["Upper_Price_Channel_Adj"][i]["Stop_Date"]
        i_adj_amount = config_json[ticker]["Upper_Price_Channel_Adj"][i]["Adj_Amount"]
        try:
          upper_price_channel_adj_start_date_list.append(dt.datetime.strptime(i_start_date, "%m/%d/%Y").date())
          upper_price_channel_adj_stop_date_list.append(dt.datetime.strptime(i_stop_date, "%m/%d/%Y").date())
          upper_price_channel_adj_amount_list.append(float(i_adj_amount))
        except (ValueError):
          logging.error(
            "\n***** Error : Either the Start/Stop Dates or the Adjust Amount are not in proper format for Upper_Price_Channel_Adj in Configuration json file.\n"
            "***** Error : The Dates should be in the format %m/%d/%Y and the Adjust Amount should be a int/float\n"
            "***** Error : Found somewhere in : " + str(i_start_date) + str(i_stop_date) + str(i_adj_amount))
          sys.exit(1)
      logging.debug("The Upper Channel Start Date List" + str(upper_price_channel_adj_start_date_list))
      logging.debug("The Upper Channel Stop Date List" + str(upper_price_channel_adj_stop_date_list))
      logging.debug("The Upper Channel Adjust List" + str(upper_price_channel_adj_amount_list))

  if (ticker not in config_json.keys()):
    logging.debug("json data for " + str(ticker) + " does not exist in " + str(configuration_json_file) + "file")
  else:
    if ("Lower_Price_Channel_Adj" in config_json[ticker]):
      len_lower_price_channel_adj = len(config_json[ticker]["Lower_Price_Channel_Adj"])
      logging.debug("The number of Upper channel adjustments specified : " + str(len_lower_price_channel_adj))
      for i in range(len_lower_price_channel_adj):
        i_start_date = config_json[ticker]["Lower_Price_Channel_Adj"][i]["Start_Date"]
        i_stop_date = config_json[ticker]["Lower_Price_Channel_Adj"][i]["Stop_Date"]
        i_adj_amount = config_json[ticker]["Lower_Price_Channel_Adj"][i]["Adj_Amount"]
        try:
          lower_price_channel_adj_start_date_list.append(dt.datetime.strptime(i_start_date, "%m/%d/%Y").date())
          lower_price_channel_adj_stop_date_list.append(dt.datetime.strptime(i_stop_date, "%m/%d/%Y").date())
          lower_price_channel_adj_amount_list.append(float(i_adj_amount))
        except (ValueError):
          logging.error(
            "\n***** Error : Either the Start/Stop Dates or the Adjust Amount are not in proper format for Lower_Price_Channel_Adj in Configuration json file.\n"
            "***** Error : The Dates should be in the format %m/%d/%Y and the Adjust Amount should be a int/float\n"
            "***** Error : Found somewhere in : " + str(i_start_date) + str(i_stop_date) + str(i_adj_amount))
          sys.exit(1)
      logging.debug("The Upper Channel Start Date List" + str(lower_price_channel_adj_start_date_list))
      logging.debug("The Upper Channel Stop Date List" + str(lower_price_channel_adj_stop_date_list))
      logging.debug("The Upper Channel Adjust List" + str(lower_price_channel_adj_amount_list))

  # Now Process the upper and lower price channel adjustment lists to make the adjustments to the
  # actual price channel list...for the length of the lists created above...and that is why it
  # was a good ides to initialize the length to '0' and crate empty lists above
  for i_idx in range(len_upper_price_channel_adj):
    upper_price_channel_adj_start_date = upper_price_channel_adj_start_date_list[i_idx]
    upper_price_channel_adj_stop_date = upper_price_channel_adj_stop_date_list[i_idx]
    upper_price_channel_adj_amount = upper_price_channel_adj_amount_list[i_idx]
    for i_date in date_list:
      if (upper_price_channel_adj_start_date <= i_date <= upper_price_channel_adj_stop_date):
        i_index = date_list.index(i_date)
        logging.debug("Historical Date " + str(i_date) + " lies between Upper Channel Adjust Start Date " +
                      str(upper_price_channel_adj_start_date) + " and stop Date" + str(upper_price_channel_adj_stop_date) +
                      " at index " + str(i_index))
        upper_price_channel_list[i_index - days_in_2_qtrs] = upper_price_channel_list[
                                                               i_index - days_in_2_qtrs] + upper_price_channel_adj_amount

  for i_idx in range(len_lower_price_channel_adj):
    lower_price_channel_adj_start_date = lower_price_channel_adj_start_date_list[i_idx]
    lower_price_channel_adj_stop_date = lower_price_channel_adj_stop_date_list[i_idx]
    lower_price_channel_adj_amount = lower_price_channel_adj_amount_list[i_idx]
    for i_date in date_list:
      if (lower_price_channel_adj_start_date <= i_date <= lower_price_channel_adj_stop_date):
        i_index = date_list.index(i_date)
        logging.debug("Historical Date " + str(i_date) + " lies between Lower Channel Adjust Start Date " +
                      str(lower_price_channel_adj_start_date) + " and stop Date" + str(lower_price_channel_adj_stop_date) +
                      " at index " + str(i_index))
        lower_price_channel_list[i_index - days_in_2_qtrs] = lower_price_channel_list[
                                                               i_index - days_in_2_qtrs] + lower_price_channel_adj_amount
  # ---------------------------------------------------------------------------

  # Now create the analyst adjusted channel
  analyst_adjusted_channel_upper = []
  analyst_adjusted_channel_lower = []
  for i in range(len(date_list)):
    analyst_adjusted_channel_upper.append(float('nan'))
    analyst_adjusted_channel_lower.append(float('nan'))

  # The index list has (from left to right) - the indices on far future white diamond
  # to near future white diamond to most recent black diamond
  # Reverse the index list - now the list has (from left to right) the most recent
  # black diamond to nearest future white diamond to far future white diamond.
  # For e.g. change to list from
  # [1, 65, 129, 192, 254, 318, 382] to
  # [382, 318, 254, 192, 129, 65, 1]
  analyst_channel_adjust_index_list.reverse()
  logging.debug("The Analyst Channel Adjust Index list (reversed) is :" + str(analyst_channel_adjust_index_list))
  # del analyst_channel_adjust_index_list[:2]

  chunk_size = (analyst_eps_projections_accuracy_list[0] - 1) / 4
  for i_tmp in range(len(analyst_channel_adjust_index_list) - 1):
    start_adjust_index = analyst_channel_adjust_index_list[i_tmp]
    stop_adjust_index = analyst_channel_adjust_index_list[i_tmp + 1]
    if (i_tmp >= 4):
      upper_channel_start_value = upper_price_channel_list[start_adjust_index] * (1 + chunk_size * 4)
      upper_channel_stop_value = upper_price_channel_list[stop_adjust_index] * (1 + chunk_size * 4)
      lower_channel_start_value = lower_price_channel_list[start_adjust_index] * (1 + chunk_size * 4)
      lower_channel_stop_value = lower_price_channel_list[stop_adjust_index] * (1 + chunk_size * 4)
    else:
      upper_channel_start_value = upper_price_channel_list[start_adjust_index] * (1 + chunk_size * i_tmp)
      upper_channel_stop_value = upper_price_channel_list[stop_adjust_index] * (1 + chunk_size * (i_tmp + 1))
      lower_channel_start_value = lower_price_channel_list[start_adjust_index] * (1 + chunk_size * i_tmp)
      lower_channel_stop_value = lower_price_channel_list[stop_adjust_index] * (1 + chunk_size * (i_tmp + 1))
    logging.debug("Starting to work on analyst channel at index " + str(i_tmp) + " with Start adjust index " + str(start_adjust_index) + " and stop adjust index " + str(stop_adjust_index))
    upper_channel_mini_step = (upper_channel_stop_value - upper_channel_start_value) / (start_adjust_index - stop_adjust_index)
    lower_channel_mini_step = (lower_channel_stop_value - lower_channel_start_value) / (start_adjust_index - stop_adjust_index)
    logging.debug("The start value of upper channel is : " + str(upper_channel_start_value) + " and the stop value of upper channel is : " + str(upper_channel_stop_value) + " with mini step : " + str(upper_channel_mini_step))
    logging.debug("The start value of lower channel is : " + str(lower_channel_start_value) + " and the stop value of lower channel is : " + str(lower_channel_stop_value) + " with mini step : " + str(lower_channel_mini_step))
    for j_tmp in range(start_adjust_index, stop_adjust_index, -1):
      analyst_adjusted_channel_upper[j_tmp] = upper_channel_start_value + upper_channel_mini_step * (start_adjust_index - j_tmp)
      analyst_adjusted_channel_lower[j_tmp] = lower_channel_start_value + lower_channel_mini_step * (start_adjust_index - j_tmp)
      logging.debug("The loop index is " + str(j_tmp) + " and the adjusted upper channel value is : " + str(analyst_adjusted_channel_upper[j_tmp]))
      logging.debug("The loop index is " + str(j_tmp) + " and the adjusted lower channel value is : " + str(analyst_adjusted_channel_lower[j_tmp]))

  # Now shift the price channels by two quarters
  # Approximately 6 months = 126 business days by inserting 126 nan at location 0
  nan_list = []
  for i in range(days_in_2_qtrs):
    upper_price_channel_list.insert(0, float('nan'))
    lower_price_channel_list.insert(0, float('nan'))
    analyst_adjusted_channel_upper.insert(0, float('nan'))
    analyst_adjusted_channel_lower.insert(0, float('nan'))
  # =============================================================================

  # =============================================================================
  # Create the earning Growth projection overlays
  # =============================================================================
  # Read the json to get the information for the earnings projection overlays
  # At the end of this - we should have
  # 1. The number of overlays that need to be made in the chart
  # 2. A list that contains the start dates for each of the overlays and
  # 3. A corresponding list that contains the stop dates for each of the overlay

  logging.debug("\n\n##########     Now working on Growth Projection Lines    ##########\n\n")
  number_of_growth_proj_overlays = 0
  start_date_for_yr_eps_growth_proj_list = []
  stop_date_for_yr_eps_growth_proj_list = []
  if (ticker not in config_json.keys()):
    logging.debug("json data for " + str(ticker) + " does not exist in " + str(configuration_json_file) + " file")
  else:
    if ("Earnings_growth_projection_overlay" in config_json[ticker]):
      eps_growth_proj_overlay_df = pd.DataFrame(config_json[ticker]["Earnings_growth_projection_overlay"])
      number_of_growth_proj_overlays = len(eps_growth_proj_overlay_df.index)
      logging.debug("The Earnings growth overlay converted to dataframe is \n" + eps_growth_proj_overlay_df.to_string() +
                    "\nAnd the length of the DateFrame is " + str(number_of_growth_proj_overlays))
      # This works : Delete the rows that have Ignore in any column
      eps_growth_proj_overlay_df.drop(eps_growth_proj_overlay_df[(eps_growth_proj_overlay_df.Start_Date == "Ignore") | (eps_growth_proj_overlay_df.Stop_Date == "Ignore")].index, inplace=True)
      # Conver the start Dates to datetime, add it as a separate column, and then
      # sort the dataframe based on that datetime column and reindex the dateframe
      eps_growth_proj_overlay_df['Start_Date_datetime'] = pd.to_datetime(eps_growth_proj_overlay_df['Start_Date'], format='%m/%d/%Y')
      eps_growth_proj_overlay_df.sort_values('Start_Date_datetime', inplace=True)
      eps_growth_proj_overlay_df.reset_index(inplace=True, drop=True)
      # eps_growth_proj_overlay_df.set_index('Start_Date', inplace=True)
      number_of_growth_proj_overlays = len(eps_growth_proj_overlay_df.index)
      logging.debug("The Sorted (by start date) Earnings growth overlay dataframe - with an added column is \n" + eps_growth_proj_overlay_df.to_string() +
        "\nAnd the length of the DateFrame is " + str(number_of_growth_proj_overlays))

      stop_date_list = eps_growth_proj_overlay_df.Stop_Date.tolist()
      start_date_list = eps_growth_proj_overlay_df.Start_Date.tolist()
      logging.debug("The Stop_Date extracted from Earning growth overlay is" + str(stop_date_list))

      # Now find if there are any "Next" in the stop date
      # If there are then"Next" gets replaced by the next row start date
      # (remember that the dataframe is already sorted ascending with the
      # start dates - so in essence the current row earning projection overlay
      # will stop at the next start date
      next_in_stop_date_list_cnt = 0
      for i_idx in range(number_of_growth_proj_overlays):
        if (stop_date_list[i_idx] == "Next"):
          next_in_stop_date_list_cnt = next_in_stop_date_list_cnt + 1

      logging.debug("The number of \"Next\" found in the Earnings_growth_projection_overlay : " + str(next_in_stop_date_list_cnt))
      # Check if the last row of the dateframe Stop_Date is set to Next - then error out as there is no
      # Next date available corresponding the the last row of the dateframe (remember that the dataframe is
      # already sorted)
      if (eps_growth_proj_overlay_df.loc[number_of_growth_proj_overlays - 1, 'Stop_Date'] == "Next"):
        logging.error("")
        logging.error("The Stop_Date, corresponding the the Start_Date : " + str(eps_growth_proj_overlay_df.loc[number_of_growth_proj_overlays - 1, 'Start_Date']))
        logging.error("in the Earnings_growth_projection_overlay is set as \"Next\"")
        logging.error("This cannot be supported as there is no next date available after that date...")
        logging.error("Please correct in Configuration.json file and rerun...Exiting")
        sys.exit(1)
      elif (next_in_stop_date_list_cnt > 0):
        # This used to work - but does not work now for some reason
        # eps_growth_proj_overlay_df.Stop_Date.replace(to_replace='Next', value=eps_growth_proj_overlay_df.Start_Date.shift(-1), inplace=True)
        # So now need to replace it with the loop
        for i_idx in range(number_of_growth_proj_overlays):
          if (stop_date_list[i_idx] == "Next"):
            eps_growth_proj_overlay_df.loc[i_idx, 'Stop_Date'] = eps_growth_proj_overlay_df.loc[i_idx + 1, 'Start_Date']

      # Replace the "End" and "Next" in the stop dates with the appropriate value
      # "End" gets replaced by the end date (which it at index 0) that the historical date list has
      # (So the overlay will extent all the way to the right of the chart)
      eps_growth_proj_overlay_df.Stop_Date.replace(to_replace='End', value=date_str_list[0], inplace=True)

      logging.debug("The Earning growth overlay dataframe now populated with real dates and sorted is \n" + eps_growth_proj_overlay_df.to_string() +
        "\nAnd the length of the DateFrame is " + str(number_of_growth_proj_overlays))
      # This works : Finally put those start and stop dates as datetimes in their own lists
      # start_date_for_yr_eps_growth_proj_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in
      #                                           eps_growth_proj_overlay_df.Start_Date.tolist()]
      # stop_date_for_yr_eps_growth_proj_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in
      #                                          eps_growth_proj_overlay_df.Stop_Date.tolist()]
      # print("The Start Date List for EPS Growth Projection is", start_date_for_yr_eps_growth_proj_list)
      # sys.exit(1)

  if (number_of_growth_proj_overlays > 0):
    # Create a list of lists equal to the number of rows of the dataframe - which is the same as
    # the number of overlays that are specified in the json file)
    yr_eps_02_5_growth_expanded_list = [[] for _ in range(number_of_growth_proj_overlays)]
    yr_eps_05_0_growth_expanded_list = [[] for _ in range(number_of_growth_proj_overlays)]
    yr_eps_10_0_growth_expanded_list = [[] for _ in range(number_of_growth_proj_overlays)]
    yr_eps_20_0_growth_expanded_list = [[] for _ in range(number_of_growth_proj_overlays)]

    for i_idx, row in eps_growth_proj_overlay_df.iterrows():
      # This works : Get the Start_Date and Stop_Date columns in a list
      start_date_for_yr_eps_growth_proj = dt.datetime.strptime(row['Start_Date'], '%m/%d/%Y').date()
      stop_date_for_yr_eps_growth_proj = dt.datetime.strptime(row['Stop_Date'], '%m/%d/%Y').date()

      # Match the start and stop dates with the closest dates from yr_eps_date_list to
      # get the index of the matching dates.
      growth_proj_start_match_date = min(yr_eps_date_list, key=lambda d: abs(d - start_date_for_yr_eps_growth_proj))
      growth_proj_start_index = yr_eps_date_list.index(growth_proj_start_match_date)
      growth_proj_stop_match_date = min(yr_eps_date_list, key=lambda d: abs(d - stop_date_for_yr_eps_growth_proj))
      growth_proj_stop_index = yr_eps_date_list.index(growth_proj_stop_match_date)

      yr_eps_02_5_growth_list = []
      yr_eps_05_0_growth_list = []
      yr_eps_10_0_growth_list = []
      yr_eps_20_0_growth_list = []
      # Create the growth list for same number of entries as yr_eps_date_list
      for i in range(len(yr_eps_date_list)):
        yr_eps_02_5_growth_list.append(float('nan'))
        yr_eps_05_0_growth_list.append(float('nan'))
        yr_eps_10_0_growth_list.append(float('nan'))
        yr_eps_20_0_growth_list.append(float('nan'))

      # The first entry for the list comes from the yr_eps_list that matched the start date
      # because the overlay will start from the same black/while diamond
      yr_eps_02_5_growth_list[growth_proj_start_index] = yr_eps_list[growth_proj_start_index]
      yr_eps_05_0_growth_list[growth_proj_start_index] = yr_eps_list[growth_proj_start_index]
      yr_eps_10_0_growth_list[growth_proj_start_index] = yr_eps_list[growth_proj_start_index]
      yr_eps_20_0_growth_list[growth_proj_start_index] = yr_eps_list[growth_proj_start_index]

      # Then grow the growth list from the start date to the stop date by multiplying
      # with the grwoth factor
      for i in reversed(range(growth_proj_stop_index, growth_proj_start_index)):
        logging.debug("Updating for index" + str(i))
        yr_eps_02_5_growth_list[i] = 1.025 * float(yr_eps_02_5_growth_list[i + 1])
        yr_eps_05_0_growth_list[i] = 1.05 * float(yr_eps_05_0_growth_list[i + 1])
        yr_eps_10_0_growth_list[i] = 1.10 * float(yr_eps_10_0_growth_list[i + 1])
        yr_eps_20_0_growth_list[i] = 1.20 * float(yr_eps_20_0_growth_list[i + 1])

      logging.debug("The Annual eps list" + str(yr_eps_list))
      logging.debug("The 2.5% growth rate eps list" + str(yr_eps_02_5_growth_list))
      logging.debug("The   5% growth rate eps list" + str(yr_eps_05_0_growth_list))
      logging.debug("The  10% growth rate eps list" + str(yr_eps_10_0_growth_list))
      logging.debug("The  20% growth rate eps list" + str(yr_eps_20_0_growth_list))

      # Now expand the list to all the dates (from historical date list)
      yr_eps_02_5_growth_expanded_list_unsmooth = []
      yr_eps_05_0_growth_expanded_list_unsmooth = []
      yr_eps_10_0_growth_expanded_list_unsmooth = []
      yr_eps_20_0_growth_expanded_list_unsmooth = []
      for i in range(len(date_list)):
        yr_eps_02_5_growth_expanded_list_unsmooth.append(float('nan'))
        yr_eps_05_0_growth_expanded_list_unsmooth.append(float('nan'))
        yr_eps_10_0_growth_expanded_list_unsmooth.append(float('nan'))
        yr_eps_20_0_growth_expanded_list_unsmooth.append(float('nan'))

      for yr_eps_date in yr_eps_date_list:
        curr_index = yr_eps_date_list.index(yr_eps_date)
        # logging.debug("Looking for " + str(yr_eps_date))
        match_date = min(date_list, key=lambda d: abs(d - yr_eps_date))
        logging.debug("The matching date is " + str(match_date) + " at index " + str(date_list.index(match_date)))
        yr_eps_02_5_growth_expanded_list_unsmooth[date_list.index(match_date)] = yr_eps_02_5_growth_list[curr_index]
        yr_eps_05_0_growth_expanded_list_unsmooth[date_list.index(match_date)] = yr_eps_05_0_growth_list[curr_index]
        yr_eps_10_0_growth_expanded_list_unsmooth[date_list.index(match_date)] = yr_eps_10_0_growth_list[curr_index]
        yr_eps_20_0_growth_expanded_list_unsmooth[date_list.index(match_date)] = yr_eps_20_0_growth_list[curr_index]

      # Populate the list of lists
      yr_eps_02_5_growth_expanded_list[i_idx] = smooth_list(yr_eps_02_5_growth_expanded_list_unsmooth)
      yr_eps_05_0_growth_expanded_list[i_idx] = smooth_list(yr_eps_05_0_growth_expanded_list_unsmooth)
      yr_eps_10_0_growth_expanded_list[i_idx] = smooth_list(yr_eps_10_0_growth_expanded_list_unsmooth)
      yr_eps_20_0_growth_expanded_list[i_idx] = smooth_list(yr_eps_20_0_growth_expanded_list_unsmooth)

    logging.info("Prepared the Earnings Growth Overlays")
  # =============================================================================

  # ===========================================================================
  # SECTION FOR SALES BV OVERLAY : BEGIN
  # Read the AAII Yearly Financial file
  # At the end of this section we have the list extracted from AAII financials file
  # ===========================================================================

  # ---------------------------------------------------------------------------
  # Read the parse the AAII ticker financials file
  # ---------------------------------------------------------------------------
  aaii_ticker = ticker
  if (ticker in sc_funcs.master_to_aaii_ticker_xlate.index):
    aaii_ticker = sc_funcs.master_to_aaii_ticker_xlate.loc[ticker,'aaii_tracking_ticker']
  logging.debug("AAII ticker is  : " + str(aaii_ticker))

  # 03/11/2023 : The usecols codeline was beginning to give a warning like this
  # FutureWarning: Defining usecols with out of bounds indices is deprecated and will raise a ParserError in a future version.  #   **kwds,
  # because sometimes the xlsx file did not have the data in All the columns
  # until AZ (for e.g it only had data until col AB).
  # So instead of using usecols, we can ask python to start reading the xlsx
  # from col C (2 - numerically) until the last col and that works.
  # aaii_qtr_financial_df = pd.read_excel(dir_path + "\\" + aaii_financial_qtr_dir + "\\" + aaii_ticker + "_QTR_FIN.xlsx", sheet_name=aaii_ticker, skiprows=6, usecols="C:AZ")
  aaii_qtr_financial_df = pd.read_excel(dir_path + "\\" + aaii_financial_qtr_dir + "\\" + aaii_ticker + "_QTR_FIN.xlsx", sheet_name=aaii_ticker, skiprows=6).iloc[:,2:]
  logging.debug("The Financial Dataframe is \n" + aaii_qtr_financial_df.to_string())

  # There is some screw up on how python reads the xlsx file with the first row
  # So need to set the first row as columns explicitly and then later in the loop
  # down, ignore the first row while going through the dataframe to extract
  # sales, BV etc. information
  aaii_qtr_financial_df = aaii_qtr_financial_df.transpose()
  aaii_qtr_financial_df.columns = aaii_qtr_financial_df.iloc[0]
  aaii_qtr_dt_list = []
  aaii_qtr_sales_list_org = []
  aaii_qtr_bv_list_org = []
  i_itr = 0
  for i, row in aaii_qtr_financial_df.iterrows():
    if (i_itr > 0):
      try:
        qtr_date_dt = dt.datetime.strptime(str(i), "%Y-%m-%d %H:%M:%S").date()
      except ValueError:
        logging.error("")
        logging.error("===========================================================================")
        logging.error("Error while reading AAII QTR_FIN.xlsx file to get data for Sales, Book Value plot")
        logging.error("This sometimes happens, especially for newer stocks, b/c the AAII QTR_FIN.xlsx file")
        logging.error("===> " + aaii_ticker + "_QTR_FIX.xlsx <===")
        logging.error("has N/A for older dates (generally older than the IPO dates) and they are towards")
        logging.error("the right of the sheet in the xlsx file")
        logging.error("The fix is to delete the columns that have N/A dates in the AAII QTR_FIN.xlsx file")
        logging.error("Please delete those columns and re-run")
        logging.error("===========================================================================")
        sys.exit(1)
      qtr_sales = row['Total Revenue']
      qtr_bv = row['Total Stockholder Equity']
      aaii_qtr_dt_list.append(qtr_date_dt)
      aaii_qtr_sales_list_org.append(qtr_sales)
      aaii_qtr_bv_list_org.append(qtr_bv)
      logging.debug("QTR Date : " + str(qtr_date_dt) + ", Sales : " + str(qtr_sales) + ", BV : " + str(qtr_bv))
    i_itr = i_itr+1

  logging.debug("")
  logging.debug("AAII QTR Date  List          " + str(aaii_qtr_dt_list))
  logging.debug("Original AAII QTR Sales List " + str(aaii_qtr_sales_list_org))
  logging.debug("Original AAII QTR BV    List " + str(aaii_qtr_bv_list_org))

  # ---------------------------------------------------------------------------
  # Average out the 4 qtrs of sales and BV numbers to make a, relatively
  # smooth, annual number. This is akin to creating black diamonds from
  # quarterly pink dots
  # ---------------------------------------------------------------------------
  logging.debug("")
  i_int = 0
  aaii_qtr_sales_list = list()
  while (i_int < (len(aaii_qtr_sales_list_org) - 3)):
    average_sales = (aaii_qtr_sales_list_org[i_int] + \
                     aaii_qtr_sales_list_org[i_int + 1] + \
                     aaii_qtr_sales_list_org[i_int + 2] + \
                     aaii_qtr_sales_list_org[i_int + 3]) / 4

    logging.debug("Iteration # " + str(i_int).ljust(2) + ", Date : " + str(aaii_qtr_dt_list[i_int]) + " : Quartely Sales : Average Yearly Sales : " + \
                  str(aaii_qtr_sales_list_org[i_int]) + " " + \
                  str(aaii_qtr_sales_list_org[i_int + 1]) + " " + \
                  str(aaii_qtr_sales_list_org[i_int + 2]) + " " + \
                  str(aaii_qtr_sales_list_org[i_int + 3]) + " : " + \
                  str(average_sales))
    aaii_qtr_sales_list.append(average_sales)
    i_int += 1

  logging.debug("")
  i_int = 0
  aaii_qtr_bv_list = list()
  while (i_int < (len(aaii_qtr_bv_list_org) - 3)):
    average_bv = (aaii_qtr_bv_list_org[i_int] + \
                  aaii_qtr_bv_list_org[i_int + 1] + \
                  aaii_qtr_bv_list_org[i_int + 2] + \
                  aaii_qtr_bv_list_org[i_int + 3]) / 4

    logging.debug("Iteration # " + str(i_int).ljust(2) + ", Date : " + str(aaii_qtr_dt_list[i_int]) + " : Quartely BV : Average Yearly BV : " + \
                  str(aaii_qtr_bv_list_org[i_int]) + " " + \
                  str(aaii_qtr_bv_list_org[i_int + 1]) + " " + \
                  str(aaii_qtr_bv_list_org[i_int + 2]) + " " + \
                  str(aaii_qtr_bv_list_org[i_int + 3]) + " : " + \
                  str(average_bv))
    aaii_qtr_bv_list.append(average_bv)
    i_int += 1

  # At this point, we have 3 list, aaii qtr date list, and smoothed out sales and BV
  # list. Note that the smoothed out sales and BV list has 3 fewer entries than the
  # date list.

  # Now delete the last 3 elements from the aaii qtr dt list as the qtr sales
  # and bv values have 3 less entries as they have been yearly smoothed out
  # (just list the yr_eps is created out of qtr_eps)
  del aaii_qtr_dt_list[len(aaii_qtr_dt_list) - 3:]
  # Reverse the lists so that they are ordered from oldest date to newest date
  aaii_qtr_dt_list.reverse()
  aaii_qtr_sales_list_org.reverse()
  aaii_qtr_bv_list_org.reverse()
  aaii_qtr_sales_list.reverse()
  aaii_qtr_bv_list.reverse()
  logging.debug("")
  logging.debug("AAII QTR Date  List          " + str(aaii_qtr_dt_list))
  logging.debug("Original AAII QTR Sales List " + str(aaii_qtr_sales_list_org))
  logging.debug("AAII QTR Sales List          " + str(aaii_qtr_sales_list))
  logging.debug("Orignial AAII QTR BV    List " + str(aaii_qtr_bv_list_org))
  logging.debug("AAII QTR BV    List          " + str(aaii_qtr_bv_list))
  # At this point, we have read the AAII ticker financials file and have created
  # 3 lists that have same number of entries and have been reversed (oldest
  # date as element 0 and newest element as element N and so on
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Read the json to get the information for when Sundeep want to start the
  # sales and BV overlays
  # ---------------------------------------------------------------------------
  # At the end of this - we will have
  # 1. The number of overlays that need to be made in the chart
  # 2. A list that contains the start dates for each of the overlays and
  # 3. A corresponding list that contains the stop dates for each of the overlay

  logging.debug("\n\n##########     Now working on Sales, BV and FCF Overlay lines    ##########\n\n")
  entries_in_qtr_sales_bv_fcf_overlay_df = 0
  if (ticker not in config_json.keys()):
    logging.debug("json data for " + str(ticker) + " does not exist in " + str(configuration_json_file) + " file")
  else:
    if ("QTR_Sales_BV_FCF_Overlay" in config_json[ticker]):
      qtr_sales_bv_fcf_overlay_df = pd.DataFrame(config_json[ticker]["QTR_Sales_BV_FCF_Overlay"])
    else:
      # Define a small dataframe that has, by default, 'First' and 'Start'
      # for overlays so that the overlay will start with the first (oldest
      # date (which is AAII qtr date -3)) and stop with the latest qtr for
      # which AAII data is available
      qtr_sales_bv_fcf_overlay_df = pd.DataFrame([{'Start_Date' : 'First', 'Stop_Date' : 'End'}])
      logging.debug("YR_Sales_BV_FCF_Overlay not found in config json, created default dates for overlaying sales and bv")

    entries_in_qtr_sales_bv_fcf_overlay_df = len(qtr_sales_bv_fcf_overlay_df.index)
    logging.debug("The YR Sales, BV and FCV overlay converted to dataframe is \n" + qtr_sales_bv_fcf_overlay_df.to_string() +
                  "\nAnd the length of the DateFrame is " + str(entries_in_qtr_sales_bv_fcf_overlay_df))

    # This works : Delete the rows that have Ignore in any column
    qtr_sales_bv_fcf_overlay_df.drop(qtr_sales_bv_fcf_overlay_df[(qtr_sales_bv_fcf_overlay_df.Start_Date == "Ignore") | (qtr_sales_bv_fcf_overlay_df.Stop_Date == "Ignore")].index, inplace=True)
    # Replace 'First' with the first date that is available for sales in the aaii datafame
    qtr_sales_bv_fcf_overlay_df.Start_Date.replace(to_replace='First', value=dt.datetime.strftime(aaii_qtr_dt_list[0], format='%m/%d/%Y'), inplace=True)

    # Convert the start Dates to datetime, add it as a separate column,
    # and then sort the dataframe based on that datetime column and
    # reindex the dataframe. This gives us the dataframe sorted by
    # 'Start_Date' from newest to oldest, irrespective on how Sundeep
    # put it in the config file :-). Seriously, this is needed in the
    # next step for replacing any 'Next' in the Stop_Date
    qtr_sales_bv_fcf_overlay_df['Start_Date_datetime'] = pd.to_datetime(qtr_sales_bv_fcf_overlay_df['Start_Date'], format='%m/%d/%Y')
    qtr_sales_bv_fcf_overlay_df.sort_values('Start_Date_datetime', inplace=True)
    qtr_sales_bv_fcf_overlay_df.reset_index(inplace=True, drop=True)
    entries_in_qtr_sales_bv_fcf_overlay_df = len(qtr_sales_bv_fcf_overlay_df.index)
    logging.debug("The Sorted (by start date) Sales, BV and FCF overlay dataframe - with an added column is \n" + qtr_sales_bv_fcf_overlay_df.to_string() +
      "\nAnd the length of the DateFrame is " + str(entries_in_qtr_sales_bv_fcf_overlay_df))

    stop_date_list = qtr_sales_bv_fcf_overlay_df.Stop_Date.tolist()
    start_date_list = qtr_sales_bv_fcf_overlay_df.Start_Date.tolist()
    logging.debug("The Stop_Date extracted from Earning growth overlay is" + str(stop_date_list))

    # Now find if there are any "Next" in the stop date
    # If there are, then "Next" gets replaced by the next row start date
    # (remember that the dataframe is already sorted ascending with the
    # start dates - so in essence the current row earning projection overlay
    # will stop at the next start date
    next_in_stop_date_list_cnt = 0
    for i_idx in range(entries_in_qtr_sales_bv_fcf_overlay_df):
      if (stop_date_list[i_idx] == "Next"):
        next_in_stop_date_list_cnt = next_in_stop_date_list_cnt + 1

    logging.debug("The number of \"Next\" found in the Earnings_growth_projection_overlay : " + str(next_in_stop_date_list_cnt))
    # Check if the last row of the dateframe Stop_Date is set to
    # Next - then error out as there is no Next date available
    # corresponding the the last row of the dateframe (remember
    # that the dataframe is already sorted)
    if (qtr_sales_bv_fcf_overlay_df.loc[entries_in_qtr_sales_bv_fcf_overlay_df - 1, 'Stop_Date'] == "Next"):
      logging.error("")
      logging.error("The Stop_Date, corresponding the the Start_Date : " + str(qtr_sales_bv_fcf_overlay_df.loc[entries_in_qtr_sales_bv_fcf_overlay_df - 1, 'Start_Date']))
      logging.error("in the Earnings_growth_projection_overlay is set as \"Next\"")
      logging.error("This cannot be supported as there is no next date available after that date...")
      logging.error("Please correct in Configuration.json file and rerun...Exiting")
      sys.exit(1)
    elif (next_in_stop_date_list_cnt > 0):
      for i_idx in range(entries_in_qtr_sales_bv_fcf_overlay_df):
        if (stop_date_list[i_idx] == "Next"):
          qtr_sales_bv_fcf_overlay_df.loc[i_idx, 'Stop_Date'] = qtr_sales_bv_fcf_overlay_df.loc[i_idx + 1, 'Start_Date']

    # Replace "End" by the end date (which it at index -1)
    qtr_sales_bv_fcf_overlay_df.Stop_Date.replace(to_replace='End', value=dt.datetime.strftime(aaii_qtr_dt_list[-1], format='%m/%d/%Y'), inplace=True)
    qtr_sales_bv_fcf_overlay_df['Stop_Date_datetime'] = pd.to_datetime(qtr_sales_bv_fcf_overlay_df['Stop_Date'], format='%m/%d/%Y')
    logging.debug("The Earning growth overlay dataframe now populated with real dates and sorted is \n" + qtr_sales_bv_fcf_overlay_df.to_string() +
                "\nAnd the length of the DateFrame is " + str(entries_in_qtr_sales_bv_fcf_overlay_df))
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Now start processing each row in the dataframe for start and stop dates
  # (without the "Next" and "End") to create the list(s) that will be plotted
  # later. The number of lists created will be equal to the number of rows
  # in the dataframe
  # ---------------------------------------------------------------------------
  if (entries_in_qtr_sales_bv_fcf_overlay_df > 0):
    # Create a list of lists equal to the number of rows of the
    # dataframe - which is the same as the number of overlays
    # that are specified in the json file
    qtr_sales_expanded_list = [[] for _ in range(entries_in_qtr_sales_bv_fcf_overlay_df)]
    qtr_bv_expanded_list = [[] for _ in range(entries_in_qtr_sales_bv_fcf_overlay_df)]

    for i_idx, row in qtr_sales_bv_fcf_overlay_df.iterrows():
      logging.debug("Processing Row number " + str(i_idx) + " : \n" + str(row) + ", from the dataframe\n")
      # logging.debug("The type of Start_Date is : " + str(type(row['Start_Date'])))
      # logging.debug("The type of Stop_Date is : " + str(type(row['Stop_Date'])))
      # logging.debug("The type of Start_Date_datetime is : " + str(type(row['Start_Date_datetime'])))
      # logging.debug("The type of Stop_Date_datetime is : " + str(type(row['Stop_Date_datetime'])))
      start_qtr_for_sales_overlay_dt = date.fromtimestamp(row['Start_Date_datetime'].timestamp())
      stop_qtr_for_sales_overlay_dt = date.fromtimestamp(row['Stop_Date_datetime'].timestamp())
      logging.debug("The Start Date for Sales, BV, FCF Overlay : " + str(start_qtr_for_sales_overlay_dt))
      logging.debug("The Stop  Date for Sales, BV, FCF Overlay : " + str(stop_qtr_for_sales_overlay_dt))

      tmp_match_date = min(aaii_qtr_dt_list, key=lambda d: abs(d - start_qtr_for_sales_overlay_dt))
      start_qtr_for_sales_overlay_index = aaii_qtr_dt_list.index(tmp_match_date)
      logging.debug("The Start Date matches AAII QTR dt list at index : " + str(start_qtr_for_sales_overlay_index))
      tmp_match_date = min(aaii_qtr_dt_list, key=lambda d: abs(d - stop_qtr_for_sales_overlay_dt))
      stop_qtr_for_sales_overlay_index = aaii_qtr_dt_list.index(tmp_match_date)
      logging.debug("The Stop Date matches AAII QTR dt list index : " + str(stop_qtr_for_sales_overlay_index))

      # Match the start and stop dates with the closest dates from yr_eps_date_list to
      # get the index of the matching dates.
      growth_proj_start_match_date = min(yr_eps_date_list, key=lambda d: abs(d - start_qtr_for_sales_overlay_dt))
      growth_proj_start_index = yr_eps_date_list.index(growth_proj_start_match_date)
      logging.debug("The sales, bv and fcf start date matches yr eps date : " + str(growth_proj_start_match_date) + ", at yr eps date list index : " + str(growth_proj_start_index))

      qtr_sales_list = []
      qtr_bv_list = []
      # Create the sales list for same number of entries as yr_eps_date_list
      for i in range(len(yr_eps_date_list)):
        qtr_sales_list.append(float('nan'))
        qtr_bv_list.append(float('nan'))

      # The first entry for the list comes from the yr_eps_list that matched the start date
      # because the overlay will start from the same black/while diamond
      # qtr_sales_list[growth_proj_start_index] = yr_eps_list[growth_proj_start_index]
      # qtr_bv_list[growth_proj_start_index] = yr_eps_list[growth_proj_start_index]
      yr_eps_start_val = yr_eps_list[growth_proj_start_index]
      if (yr_eps_start_val < 0):
        # If the starting eps was negtaive, then invert it as it does not matter
        # what the starting value is. It is just used to normalize the sales and bv
        # todo : what to do if the starting eps is 0 -- probably prudent to look at
        # the range of the chart and then decide...or maybe look around to find a
        # postiive eps nearby and use than number....not sure what the right solution is
        # right now
        yr_eps_start_val = -yr_eps_start_val
        logging.debug("The starting yr eps is : " + str(yr_eps_start_val) + ", which is negative, inverting it")

      qtr_sales_start_val = aaii_qtr_sales_list[start_qtr_for_sales_overlay_index]
      # todo : what to do if the starting bv is negative or nan or 0
      qtr_bv_start_val = aaii_qtr_bv_list[start_qtr_for_sales_overlay_index]
      logging.debug("The starting value for sales is  : " + str(qtr_sales_start_val))
      logging.debug("The starting value for bv is     : " + str(qtr_bv_start_val))
      logging.debug("The starting value for YR EPS is : " + str(yr_eps_start_val))
      logging.debug("")
      for i in (range((stop_qtr_for_sales_overlay_index-start_qtr_for_sales_overlay_index)+1)):
        qtr_sales_list_index = growth_proj_start_index - i
        qtr_sales_change_ratio = aaii_qtr_sales_list[i+start_qtr_for_sales_overlay_index]/qtr_sales_start_val
        qtr_bv_change_ratio = aaii_qtr_bv_list[i+start_qtr_for_sales_overlay_index]/qtr_bv_start_val
        logging.debug("")
        logging.debug("Fetching aaii_list index : " + str(i+start_qtr_for_sales_overlay_index) + \
                      ", QTR Sales : " + str(aaii_qtr_sales_list[i+start_qtr_for_sales_overlay_index]) + \
                      ", QTR BV : " + str(aaii_qtr_bv_list[i + start_qtr_for_sales_overlay_index]))
        qtr_sales_val = yr_eps_start_val*qtr_sales_change_ratio
        qtr_bv_val = yr_eps_start_val*qtr_bv_change_ratio
        qtr_sales_list[qtr_sales_list_index] = qtr_sales_val
        qtr_bv_list[qtr_sales_list_index] = qtr_bv_val
        logging.debug("The ratio b/w : " + str(aaii_qtr_sales_list[i+start_qtr_for_sales_overlay_index]) + \
                      ", and staring QTR Sales value : " + str(qtr_sales_start_val) + \
                      ", is " + str(qtr_sales_change_ratio))
        logging.debug("Updating qtr_sales_list at index : " + str(qtr_sales_list_index) + ", with yr_eps_start_val*ratio : " + str(qtr_sales_val))
        logging.debug("The ratio b/w : " + str(aaii_qtr_bv_list[i + start_qtr_for_sales_overlay_index]) + \
                      ", and staring QTR BV value : " + str(qtr_bv_start_val) + \
                      ", is " + str(qtr_bv_change_ratio))
        logging.debug("Updating qtr_bv_list at index : " + str(qtr_sales_list_index) + ", with yr_eps_start_val*ratio : " + str(qtr_bv_val))

      logging.debug("The qtr_sales_list : \n" + str(qtr_sales_list))
      logging.debug("The bv_sales_list : \n" + str(qtr_bv_list))

      # Now expand the list to all the dates (from historical date list)
      qtr_sales_expanded_list_unsmooth = []
      qtr_bv_expanded_list_unsmooth = []
      for i in range(len(date_list)):
        qtr_sales_expanded_list_unsmooth.append(float('nan'))
        qtr_bv_expanded_list_unsmooth.append(float('nan'))

      for yr_eps_date in yr_eps_date_list:
        curr_index = yr_eps_date_list.index(yr_eps_date)
        # logging.debug("Looking for " + str(yr_eps_date))
        match_date = min(date_list, key=lambda d: abs(d - yr_eps_date))
        logging.debug("The matching date is " + str(match_date) + " at index " + str(date_list.index(match_date)))
        qtr_sales_expanded_list_unsmooth[date_list.index(match_date)] = qtr_sales_list[curr_index]
        qtr_bv_expanded_list_unsmooth[date_list.index(match_date)] = qtr_bv_list[curr_index]

      # Populate the list of lists
      qtr_sales_expanded_list[i_idx] = smooth_list(qtr_sales_expanded_list_unsmooth)
      qtr_bv_expanded_list[i_idx] = smooth_list(qtr_bv_expanded_list_unsmooth)

    logging.info("Prepared the Sales, BV Overlays")
  # ===========================================================================
  # SECTION FOR SALES BV OVERLAY : END
  # =============================================================================

  # ---------------------------------------------------------------------------
  # Find out the growth for 1yr, 3yr and 5yr for eps and price
  # ---------------------------------------------------------------------------
  get_eps_and_price_growth = 1
  price_eps_growth_str_textbox = "This is the box in top center"
  if (get_eps_and_price_growth):
    # This works : Get the first non nan value from the list. That is the current price.
    # Can't do a round here - as it round 81.6999 to 81.7 and 81.7 will not match
    # to get us the current date as there is not index that will now match in the
    # adj_close_list
    # ticker_curr_price = round(next(x for x in ticker_adj_close_list if not math.isnan(x)),2)
    ticker_curr_price = next(x for x in ticker_adj_close_list if not math.isnan(x))
    ticker_curr_date = date_list[ticker_adj_close_list.index(ticker_curr_price)]
    # Now round the ticker_curr_price to 2 decimal places
    round(ticker_curr_price, 2)

    # Based on the latest date from the ticker, get the latest past date for yr_eps.
    # In other words, if the current ticker date is - say 07/17/2019 - then get the latest
    # past date for yr eps - which can be 06/30/2019. In other words - it is possible that we
    # are - say 89 days into the quarter (say the current ticker date is 03/29/2019) - then also
    # we want to latest past quarter day (in this case it may be 12/31/2018). This is needed
    # because we want to get the growth rates based on latest reported earnings and not
    # the projected earnings - which is what that match function will find if the ticker
    # current date is more than half way into the quarter
    #
    # If the match date for yr_eps is newer than the current date (that can happen if the current
    # date is in the later half of the quarter) - then substract 60 days and genearte
    # matching date again - That will certainly give us a date that is the immdediately
    # of the latest reported quarter
    yr_eps_curr_date = min(yr_eps_date_list, key=lambda d: abs(d - ticker_curr_date))
    if (yr_eps_curr_date > dt.date.today()):
      logging.debug("The match date for yr eps is newer than the current date. Will use yr eps from one quarter ago")
      yr_eps_curr_date = min(yr_eps_date_list, key=lambda d: abs(d - (ticker_curr_date - dt.timedelta(days=60))))

    yr_eps_curr = round(yr_eps_list[yr_eps_date_list.index(yr_eps_curr_date)], 2)

    yr_eps_next_q_date = min(yr_eps_date_list, key=lambda d: abs(d - ticker_curr_date))
    logging.debug("The date for next quarter is " + str(yr_eps_next_q_date))
    if (yr_eps_next_q_date <= dt.date.today()):
      logging.debug("The match date for next quarter eps is older than the current date. Will use date from one quarter ahead")
      yr_eps_next_q_date = min(yr_eps_date_list, key=lambda d: abs(d - (ticker_curr_date + dt.timedelta(days=60))))

    yr_eps_next_yr_date = min(yr_eps_date_list, key=lambda d: abs(d - (yr_eps_next_q_date + dt.timedelta(days=273))))
    yr_eps_next_q = round(yr_eps_list[yr_eps_date_list.index(yr_eps_next_q_date)], 2)
    yr_eps_next_yr = round(yr_eps_list[yr_eps_date_list.index(yr_eps_next_yr_date)], 2)
    logging.debug("The date for next quarter is " + str(yr_eps_next_q_date) + " and the projected eps is " + str(yr_eps_next_q))
    logging.debug("The date for next year is " + str(yr_eps_next_yr_date) + " and the projected eps is " + str(yr_eps_next_yr))

    # Get dates 1, 3 and 5 yr ago - based on curr eps date
    ticker_1_yr_ago_date_raw = yr_eps_curr_date - dt.timedelta(days=365)
    ticker_3_yr_ago_date_raw = yr_eps_curr_date - dt.timedelta(days=3 * 365)
    ticker_5_yr_ago_date_raw = yr_eps_curr_date - dt.timedelta(days=5 * 365)

    # Match the raw dates to get the closest dates 1, 3 and 5 yr ago for eps
    ticker_1_yr_ago_date_for_eps = min(yr_eps_date_list, key=lambda d: abs(d - ticker_1_yr_ago_date_raw))
    ticker_3_yr_ago_date_for_eps = min(yr_eps_date_list, key=lambda d: abs(d - ticker_3_yr_ago_date_raw))
    ticker_5_yr_ago_date_for_eps = min(yr_eps_date_list, key=lambda d: abs(d - ticker_5_yr_ago_date_raw))

    # Match the raw dates to get the closest dates 1, 3 and 5 yr ago for price. So
    # note that the price that we will get is not 1, 3 and 5 yr ago from the current ticker date
    # but rather 1, 3 and 5 yr ago from the latest past quarter
    ticker_1_yr_ago_date_for_price = min(date_list, key=lambda d: abs(d - ticker_1_yr_ago_date_raw))
    ticker_3_yr_ago_date_for_price = min(date_list, key=lambda d: abs(d - ticker_3_yr_ago_date_raw))
    ticker_5_yr_ago_date_for_price = min(date_list, key=lambda d: abs(d - ticker_5_yr_ago_date_raw))

    # Note that the price that we get here is the 1, 3 and 5 yr ago price for date from the curr eps
    # date (and not the current price date)
    ticker_1_yr_ago_price = round(ticker_adj_close_list[date_list.index(ticker_1_yr_ago_date_for_price)], 2)
    ticker_3_yr_ago_price = round(ticker_adj_close_list[date_list.index(ticker_3_yr_ago_date_for_price)], 2)
    ticker_5_yr_ago_price = round(ticker_adj_close_list[date_list.index(ticker_5_yr_ago_date_for_price)], 2)

    yr_eps_1_yr_ago = round(yr_eps_list[yr_eps_date_list.index(ticker_1_yr_ago_date_for_eps)], 2)
    yr_eps_3_yr_ago = round(yr_eps_list[yr_eps_date_list.index(ticker_3_yr_ago_date_for_eps)], 2)
    yr_eps_5_yr_ago = round(yr_eps_list[yr_eps_date_list.index(ticker_5_yr_ago_date_for_eps)], 2)

    logging.debug("The Last     price for ticker is " + str(ticker_curr_price) + " on date " + str(ticker_curr_date) + " with earnings at " + str(yr_eps_curr) + " is at index" + str(date_list.index(ticker_curr_date)))
    logging.debug("The 1 Yr ago price for ticker is " + str(ticker_1_yr_ago_price) + " on date " + str(ticker_1_yr_ago_date_for_price) + " with earnings at " + str(yr_eps_1_yr_ago) + " is at index" + str(date_list.index(ticker_1_yr_ago_date_for_price)))
    logging.debug("The 3 Yr ago price for ticker is " + str(ticker_3_yr_ago_price) + " on date " + str(ticker_3_yr_ago_date_for_price) + " with earnings at " + str(yr_eps_3_yr_ago) + " is at index" + str(date_list.index(ticker_3_yr_ago_date_for_price)))
    logging.debug("The 5 Yr ago price for ticker is " + str(ticker_5_yr_ago_price) + " on date " + str(ticker_5_yr_ago_date_for_price) + " with earnings at " + str(yr_eps_5_yr_ago) + " is at index" + str(date_list.index(ticker_5_yr_ago_date_for_price)))

    eps_growth_next_yr = get_growth(yr_eps_next_yr, yr_eps_curr)
    eps_growth_next_q = get_growth(yr_eps_next_q, yr_eps_curr)
    eps_growth_1_yr_ago = get_growth(yr_eps_curr, yr_eps_1_yr_ago)
    eps_growth_3_yr_ago = get_growth(yr_eps_curr, yr_eps_3_yr_ago)
    eps_growth_5_yr_ago = get_growth(yr_eps_curr, yr_eps_5_yr_ago)

    price_growth_1_yr = get_growth(ticker_curr_price, ticker_1_yr_ago_price)
    price_growth_3_yr = get_growth(ticker_curr_price, ticker_3_yr_ago_price)
    price_growth_5_yr = get_growth(ticker_curr_price, ticker_5_yr_ago_price)

    price_eps_growth_str_textbox = "     Date".ljust(20, " ") + "|  Earnings".ljust(20, " ") + ("| Price(" + str(ticker_curr_date) + ")").ljust(16, " ")
    price_eps_growth_str_textbox += ("\nNext yr- " + str(yr_eps_next_yr_date)).ljust(21, " ")
    price_eps_growth_str_textbox += ("| " + str(yr_eps_next_yr) + "(" + str(eps_growth_next_yr) + "%)").ljust(20, " ")
    price_eps_growth_str_textbox += ("| ").ljust(20)

    price_eps_growth_str_textbox += ("\nNext q - " + str(yr_eps_next_q_date)).ljust(21, " ")
    price_eps_growth_str_textbox += ("| " + str(yr_eps_next_q) + "(" + str(eps_growth_next_q) + "%)").ljust(20, )
    price_eps_growth_str_textbox += ("| ").ljust(20)

    price_eps_growth_str_textbox += ("\nCurr   - " + str(ticker_curr_date)).ljust(21, " ")
    price_eps_growth_str_textbox += ("| " + str(yr_eps_curr)).ljust(20, " ")
    price_eps_growth_str_textbox += ("| " + str(ticker_curr_price)).ljust(20, " ")

    price_eps_growth_str_textbox += ("\n1 Yr   - " + str(ticker_1_yr_ago_date_for_eps)).ljust(21, " ")
    price_eps_growth_str_textbox += ("| " + str(yr_eps_1_yr_ago) + "(" + str(eps_growth_1_yr_ago) + "%)").ljust(20)
    price_eps_growth_str_textbox += ("| " + str(ticker_1_yr_ago_price) + "(" + str(price_growth_1_yr) + "%)").ljust(20)

    price_eps_growth_str_textbox += ("\n3 Yr   - " + str(ticker_3_yr_ago_date_for_eps)).ljust(21, " ")
    price_eps_growth_str_textbox += ("| " + str(yr_eps_3_yr_ago) + "(" + str(eps_growth_3_yr_ago) + "%)").ljust(20)
    price_eps_growth_str_textbox += ("| " + str(ticker_3_yr_ago_price) + "(" + str(price_growth_3_yr) + "%)").ljust(20)

    price_eps_growth_str_textbox += ("\n5 Yr   - " + str(ticker_5_yr_ago_date_for_eps)).ljust(21, " ")
    price_eps_growth_str_textbox += ("| " + str(yr_eps_5_yr_ago) + "(" + str(eps_growth_5_yr_ago) + "%)").ljust(20)
    price_eps_growth_str_textbox += ("| " + str(ticker_5_yr_ago_price) + "(" + str(price_growth_5_yr) + "%)").ljust(20)

    logging.debug("\n" + str(price_eps_growth_str_textbox))
    logging.info("Prepared the Earnings growth Text box")
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Get the company info for company name, sector and industry
  # Also Get the Last date when the Earnings Projections were updated and
  # tack it on to ticker industry
  # ---------------------------------------------------------------------------
  yahoo_comany_info_df = pd.read_excel(dir_path + user_dir + "\\" + 'Yahoo_Company_Info.xlsm', sheet_name="Company_Info")
  yahoo_comany_info_df.set_index('Ticker', inplace=True)
  # print (yahoo_comany_info_df)
  ticker_company_name = "#NA#"
  ticker_sector = "#NA#"
  ticker_industry = "#NA#"
  chart_update_date_str = "#NA#"
  if (yahoo_comany_info_df.index.isin([(ticker)]).any()):
    # This works - get the value in the column corresponding to the index
    ticker_company_name = yahoo_comany_info_df.loc[ticker, 'Company_Name']
    ticker_sector = yahoo_comany_info_df.loc[ticker, 'Sector']
    ticker_industry = yahoo_comany_info_df.loc[ticker, 'Industry']

  is_ticker_foreign = ""
  is_ticker_foreign = str(ticker_master_tracklist_series['Is_Foreign'])
  is_ticker_foreign = is_ticker_foreign.strip()
  cnbc_matches_reported_eps = 'NA'
  # Sundeep is here
  if ('CNBC_Matches_Reported_EPS' in qtr_eps_df.columns):
    cnbc_matches_reported_eps = qtr_eps_df.CNBC_Matches_Reported_EPS.tolist()[0]
  else:
    cnbc_matches_reported_eps = str(ticker_master_tracklist_series['CNBC_Matches_Reported_EPS'])
  logging.debug("The Last Earnings were reported on  : " + str(eps_report_date))
  logging.debug("CNBC report match reported EPS = " + str(cnbc_matches_reported_eps) + \
                "If it matches then it means that the future earnings projections should actual numbers and not adjusted numbers...though the company can adjust the earnings anytime :-))" + \
                "If it does not match, then that means that the future projected earnings are likely to be adjusted by the company...It is your job to find out why the current earnings were adjusted")

  chart_update_date_str = "Earnings Reported - " + str(eps_report_date) + " :: Earnings Projections Last Updated - " + str(qtr_eps_projections_date_0) + ", " + str(qtr_eps_projections_date_1)
  chart_update_date_str += "\nCNBC Earnings - " + str(cnbc_matches_reported_eps) + " :: Added AAII EPS Projections for : " + str(no_of_years_to_insert_aaii_eps_projections) + " years"
  if not ((is_ticker_foreign == 'nan') or (len(is_ticker_foreign) == 0)):
    chart_update_date_str += " :: Country - " + is_ticker_foreign
  logging.debug(str(ticker_company_name) + str(ticker_sector) + str(ticker_industry) + str(chart_update_date_str))
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Calculated the Analysts accuracy
  # ---------------------------------------------------------------------------
  adjusted_eps_str = "Analysts Accuracy : " + str(format(analyst_eps_projections_accuracy_list[0] * 100, '^8.3f')) + "%"
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Read in the various _lim_upper and _lim_lower from config file
  # ---------------------------------------------------------------------------
  if math.isnan(ticker_config_series[chart_type_idx + '_Price_Scale_Low']):
    logging.error("Price_Scale_Low - is not set in the configurations file")
    logging.error("Please correct and rerun")
    sys.exit(1)
  else:
    price_lim_lower = ticker_config_series[chart_type_idx + '_Price_Scale_Low']
    logging.debug("Price_Scale_Low from Config file is " + str(price_lim_lower))

  if math.isnan(ticker_config_series[chart_type_idx + '_Price_Scale_High']):
    # ticker_adj_close_list_nonan = [x for x in ticker_adj_close_list if math.isnan(x) is False]
    logging.error("Price_Scale_High - is not set in the configurations file")
    logging.error("Please correct and rerun")
    sys.exit(1)
  else:
    price_lim_upper = ticker_config_series[chart_type_idx + '_Price_Scale_High']
    logging.debug("Price_Scale_High from Config file is " + str(price_lim_upper))

  if math.isnan(ticker_config_series[chart_type_idx + '_Earnings_Scale_High']):
    logging.error("EPS Scale - High is not set in the configurations file")
    logging.error("Please correct and rerun")
    sys.exit(1)
  else:
    qtr_eps_lim_upper = ticker_config_series[chart_type_idx + '_Earnings_Scale_High']
    logging.debug("EPS Scale - High from Config file " + str(qtr_eps_lim_upper))

  if math.isnan(ticker_config_series[chart_type_idx + '_Earnings_Scale_Low']):
    logging.error("EPS Scale - Low is not set in the configurations file")
    logging.error("Please correct and rerun")
    sys.exit(1)
  else:
    qtr_eps_lim_lower = ticker_config_series[chart_type_idx + '_Earnings_Scale_Low']
    logging.debug("EPS Scale - Low from Config file " + str(qtr_eps_lim_lower))

  # If AAII EPS Projections were inserted and the projected EPS was greater than the qtr_eps_lim_upper
  # then increase the upper eps and uuper price limits
  if (no_of_years_to_insert_aaii_eps_projections > 0):
    logging.debug("The white diamond EPS list is " + str(yr_projected_eps_expanded_list))
    tmp_list = [x for x in yr_projected_eps_expanded_list if str(x) != 'nan']
    yr_projected_eps_list_max = max(tmp_list)
    logging.debug("The maximum value White Diamond EPS list is " + str(yr_projected_eps_list_max))
    if (yr_projected_eps_list_max > qtr_eps_lim_upper):
      pe_ratio_from_config_file = price_lim_upper / qtr_eps_lim_upper
      logging.debug("The max yr eps from inserting projected eps : " + str(yr_projected_eps_list_max) + " is greater than : " + str(qtr_eps_lim_upper) + " specified by configurations file")
      logging.debug("The PE ratio (upper limit of the price/upper limit of the eps) of the chart specified in the config file is (" + str(price_lim_upper) + "/" + str(qtr_eps_lim_upper) + ") = " + str(pe_ratio_from_config_file))
      qtr_eps_lim_upper = yr_projected_eps_list_max + (yr_projected_eps_list_max - qtr_eps_lim_upper) * .25
      price_lim_upper = qtr_eps_lim_upper * pe_ratio_from_config_file
      logging.debug("Reset the Upper eps limit to : " + str(qtr_eps_lim_upper) + " and Upper price limit to : " + str(price_lim_upper))
  # ---------------------------------------------------------------------------

  # ===========================================================================
  # Loop for Linear, Long_Linear charts
  # ===========================================================================
  # Figure out if we have to loop once - for log charts or
  # twice - for Linear charts (Linear and Long_Linear)
  if (chart_type_idx == 'Linear'):
    linear_chart_type_list = g_dict_chart_options['Linear_chart_types']
  else:
    # The chart_type_idx is log. So this list and the variable it creates below (linear_chart_type_idx)
    # does not get used if the chart_type_idx is Log
    linear_chart_type_list = ['Not_applicable']

  if (len(linear_chart_type_list) > 1):
    logging.info("User wants more than one iteration for Linear charts - through 'g_dict_chart_options['Linear_chart_types'] options")
    logging.info("Will iterate for two types of Linear Charts" + str(linear_chart_type_list))

  # This is the loop that will execute for Log or Linear charts.
  #   It will execute only one for Log charts (as we don't have Long_Log option.
  #   There is only one option for Log chart
  #   It will execute twice for Linear Charts, if the user wants
  #   Once for Linear (default) and Once for Long_Linear
  for linear_chart_type_idx in linear_chart_type_list:
    if (len(linear_chart_type_list) > 1):
      logging.info("")
      logging.info("***** Iterating for Linear Chart with \"linear_chart_type_idx\" set to : " + str(linear_chart_type_idx))
    else:
      if (chart_type_idx == 'Linear'):
        logging.info("Preparing Linear Chart type : " + str(linear_chart_type_idx))
      else:
        logging.info("Preparing Chart type : " + str(chart_type_idx))

    # -----------------------------------------------------------------------------
    # Find out how many years need to be plotted. If the historical data is available
    # for lesser time, then adjust the period to the length of the data_list
    # -----------------------------------------------------------------------------
    if (math.isnan(ticker_config_series[chart_type_idx + '_Chart_Duration_Years'])):
      logging.error("The Chart_Duration_Years for " + str(chart_type_idx) + " is not defined in the config file. Please correct and rerun")
      sys.exit(1)
    plot_period_int = 252 * (int(ticker_config_series[chart_type_idx + '_Chart_Duration_Years']) + no_of_years_to_insert_aaii_eps_projections)
    if (linear_chart_type_idx == 'Long_Linear'):
      plot_period_int = plot_period_int + 252 * 15

    if (len(date_list) <= plot_period_int):
      plot_period_int = len(date_list) - 1
      logging.debug("Since the Historical Data (Length of the date list) is not available for all\
      the years that user is asking to plot for, so adjusting the plot for " +
                    str(float(plot_period_int / 252)) + " years (or " + str(plot_period_int) + " days)")
    else:
      logging.debug("Will plot for " + str(int(plot_period_int / 252)) + " years")
    # ---------------------------------------------------------

    # Get the index factor to pin/anchor/align the index and the price of the stock
    # to the same point at the start of the plot
    if (plot_spy):
      # Get the spy for the plot_period_int and then normalize it to stock price from
      # that date onwards
      spy_adj_close_list = spy_df.Adj_Close.tolist()
      # find the length of adj_close_list
      if (len(ticker_adj_close_list) < plot_period_int):
        spy_adjust_factor = spy_adj_close_list[len(ticker_adj_close_list)] / ticker_adj_close_list[len(ticker_adj_close_list)]
      else:
        spy_adjust_factor = spy_adj_close_list[plot_period_int] / ticker_adj_close_list[plot_period_int]
      spy_adj_close_list[:] = [x / spy_adjust_factor for x in spy_adj_close_list]

    # ---------------------------------------------------------------------------
    # Create the schiller PE line for the plot
    # ---------------------------------------------------------------------------
    average_schiller_pe = 15
    # Divide the schiller PE values by average_schiller_pe to normalize it
    schiller_pe_normalized_list = [float(schiller_pe / average_schiller_pe) for schiller_pe in schiller_pe_value_list]

    schiller_pe_value_expanded_list = []
    schiller_pe_normalized_expanded_list = []
    oldest_date_in_date_list = date_list[len(date_list) - 1]
    logging.debug("Oldest Date in Historical Date List is " + str(oldest_date_in_date_list))
    for i in range(len(date_list)):
      schiller_pe_value_expanded_list.append(float('nan'))
      schiller_pe_normalized_expanded_list.append(float('nan'))

    for schiller_pe_date in schiller_pe_date_list:
      if (schiller_pe_date > oldest_date_in_date_list):
        curr_index = schiller_pe_date_list.index(schiller_pe_date)
        # print("Looking for ", qtr_eps_date)
        match_date = min(date_list, key=lambda d: abs(d - schiller_pe_date))
        logging.debug("The matching date for Schiller PE Date : " + str(schiller_pe_date) + " in historical datelist is " +
          str(match_date) + " at index " + str(date_list.index(match_date)) + " and the Schiller PE is " + str(schiller_pe_normalized_list[curr_index]))
        schiller_pe_value_expanded_list[date_list.index(match_date)] = schiller_pe_value_list[curr_index]
        schiller_pe_normalized_expanded_list[date_list.index(match_date)] = schiller_pe_normalized_list[curr_index]
    # print("The expanded Schiller PE list is ", schiller_pe_normalized_expanded_list, "\nand the number of elements are",len(schiller_pe_normalized_expanded_list))

    # make sure that the lenght of the two expanded lists are the same
    if (len(schiller_pe_normalized_expanded_list) != len(yr_eps_adj_expanded_list)):
      logging.debug("Error ")
      sys.exit()
    schiller_pe_value_list_smooth = smooth_list(schiller_pe_value_expanded_list)
    schiller_pe_normalized_list_smooth = smooth_list(schiller_pe_normalized_expanded_list)
    yr_eps_adj_expanded_list_smooth = smooth_list(yr_eps_adj_expanded_list)

    ann_constant = (4 * qtr_eps_lim_upper) / price_lim_upper
    logging.debug("Earning Limit upper" + str(qtr_eps_lim_upper))
    logging.debug("Price Limit upper" + str(price_lim_upper))
    logging.debug("Ann Constant" + str(ann_constant))
    # time.sleep(3)
    schiller_ann_requested_red_line_list_0 = [a * b for a, b in zip(schiller_pe_value_list_smooth, yr_eps_adj_expanded_list_smooth)]
    schiller_ann_requested_red_line_list_3 = [i * ann_constant for i in schiller_ann_requested_red_line_list_0]
    # schiller_ann_requested_red_line_list_1 = [i * 4 for i in schiller_ann_requested_red_line_list_0]
    # schiller_ann_requested_red_line_list_2 = [i * qtr_eps_lim_upper for i in schiller_ann_requested_red_line_list_1]
    # schiller_ann_requested_red_line_list_3 = [i / price_lim_upper for i in schiller_ann_requested_red_line_list_2]
    # Now multiply the schiller expanded list with the yr eps expanded list
    schiller_pe_times_yr_eps_list = [a * b for a, b in zip(schiller_pe_normalized_list_smooth, yr_eps_adj_expanded_list_smooth)]
    logging.debug("The smooth Schiller Normalized PE list miltiplied by YR EPS list is " + str(schiller_pe_times_yr_eps_list))
    # ---------------------------------------------------------------------------

    # ---------------------------------------------------------------------------
    # Do the calculations needed to xtick and xtick labels for main plt
    # ---------------------------------------------------------------------------
    # This works - Good resource
    # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.date_range.html
    # https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#timeseries-offset-aliases

    # It is possible the plot_period_int might have changed because of
    # Long_Linear so this needs to be regenerated
    # logging.debug("The date list is " + str(date_list))
    # logging.debug("The number of element : " + str(len(date_list)))
    # logging.debug("The plot period is    : " + str(plot_period_int))
    fiscal_yr_dates_raw = pd.date_range(date_list[plot_period_int], date_list[0], freq=fiscal_yr_str)
    fiscal_qtr_and_yr_dates_raw = pd.date_range(date_list[plot_period_int], date_list[0], freq=fiscal_qtr_str)
    # yr_dates = pd.date_range(date_list[plot_period_int], date_list[0], freq='Y')
    # qtr_dates = pd.date_range(date_list[plot_period_int], date_list[0], freq='Q')
    logging.debug("Yearly Dates are " + str(fiscal_yr_dates_raw))
    logging.debug("Quarterly Dates are " + str(type(fiscal_qtr_and_yr_dates_raw)))

    fiscal_qtr_dates = []
    fiscal_yr_dates = []
    for x in fiscal_qtr_and_yr_dates_raw:
      logging.debug("The original Quarterly Date is : " + str(x))
      if (x in fiscal_yr_dates_raw):
        logging.debug("This quarter is also year end date. Removing " + str(type(x)))
      else:
        fiscal_qtr_dates.append(x.date().strftime('%m/%d/%Y'))

    for x in fiscal_yr_dates_raw:
      logging.debug("The original Yearly Date is : " + str(x))
      if (chart_type_idx == 'Log') or (linear_chart_type_idx == 'Long_Linear'):
        # if the chart type is long linear then only print the year or
        # can choose to print the month and the year but then make the
        # fonts smaller on the xticklables.
        fiscal_yr_dates.append(x.date().strftime('%Y'))
      else:
        fiscal_yr_dates.append(x.date().strftime('%m/%d/%Y'))

    logging.debug("The original yr dates list is\n" + str(fiscal_yr_dates_raw))
    logging.debug("The original qtr dates list is\n" + str(fiscal_qtr_and_yr_dates_raw))
    logging.debug("The modified qtr dates list is\n" + str(fiscal_qtr_dates))
    logging.debug("The modified yr dates list is\n" + str(fiscal_yr_dates))
    logging.info("Prepared the Fiscal year and Quarter ticks")
    # ---------------------------------------------------------------------------

    # ---------------------------------------------------------------------------
    # Extract and generate information needed for candlesticks and volume chart
    # ---------------------------------------------------------------------------
    if (math.isnan(ticker_config_series['Candle_Chart_Duration_Days'])):
      candle_chart_duration = 65
    else:
      candle_chart_duration = int(ticker_config_series['Candle_Chart_Duration_Days'])

    historical_columns_list = list(historical_df)
    logging.debug("The columns in Historical Dataframe " + str(historical_columns_list))
    # Get the candlestick_df from historical_df - candlesticks_df has all the data
    # past the first date when the prices are available.
    candlestick_df = historical_df.loc[ticker_adj_close_list.index(ticker_curr_price):]
    candlestick_df.columns = historical_columns_list
    logging.debug("Candlestick Dataframe is " + candlestick_df.to_string())

    date_str_list_candles = candlestick_df.Date.tolist()
    # Change the Date to mdates
    dates_2_mdates = [mdates.date2num(dt.datetime.strptime(d, '%m/%d/%Y').date()) for d in date_str_list_candles]
    candlestick_df.insert(loc=1, column='MDate', value=dates_2_mdates)
    logging.debug("Candlestick Dataframe after chanings the Dates to mdates is \n" + candlestick_df.to_string())
    MA_Price_200_list = candlestick_df.MA_Price_200_day.tolist()
    MA_Price_50_list = candlestick_df.MA_Price_50_day.tolist()
    MA_Price_20_list = candlestick_df.MA_Price_20_day.tolist()
    MA_Price_10_list = candlestick_df.MA_Price_10_day.tolist()
    MA_volume_50_list = candlestick_df.MA_Volume_50_day.tolist()

    # Candlesticks likes to put everything in tuple before plotting
    quotes = [tuple(x) for x in candlestick_df[['MDate', 'Open', 'High', 'Low', 'Close']].values]
    date_list_candles = candlestick_df.MDate.tolist()
    volume = candlestick_df.Volume.tolist()
    logging.debug("The type of quotes is " + str(quotes))
    logging.debug("The type of volume is " + str(volume))

    # Set the bar color for volume bars by comparing the current close with the previous close
    price_close_list = candlestick_df.Close.tolist()
    bar_color_list = ['darksalmon'] * len(price_close_list)
    for i_idx in range(len(price_close_list) - 1):
      bar_color_list[i_idx] = 'darksalmon'
      # logging.debug("Comparing " + str(price_close_list[i_idx]) + " with " + str(price_close_list[i_idx+1]) + " to detemine the color of the candle")
      if (price_close_list[i_idx] > price_close_list[i_idx + 1]):
        # logging.debug("Changing the color of the candle for  " + str(date_list_candles[i_idx]))
        bar_color_list[i_idx] = 'mediumseagreen'

    logging.debug("The bar color list is " + str(bar_color_list))
    logging.info("Prepared the Data for Candlesticks and the Moving Averages")

    # ---------------------------------------------------------
    # Generate the data that will be used for ticks and
    # ticklabels for y-axis for volume
    # ---------------------------------------------------------
    ticker_volume_max = max(volume[0:candle_chart_duration])
    ticker_volume_max_no_of_digits = len(str(abs(int(ticker_volume_max))))
    ticker_volume_max_first_digit = int(str(ticker_volume_max)[:1])
    logging.debug("The max volume is " + str(ticker_volume_max) + " and the number of digits are " + str(ticker_volume_max_no_of_digits) + " and the first digit is " + str(ticker_volume_max_first_digit))
    if (ticker_volume_max_first_digit == 1):
      ticker_volume_upper_limit = 2 * math.pow(10, ticker_volume_max_no_of_digits - 1)
    elif (ticker_volume_max_first_digit == 2):
      ticker_volume_upper_limit = 4 * math.pow(10, ticker_volume_max_no_of_digits - 1)
    elif (2 < ticker_volume_max_first_digit <= 4):
      ticker_volume_upper_limit = 5 * math.pow(10, ticker_volume_max_no_of_digits - 1)
    elif (5 < ticker_volume_max_first_digit <= 7):
      ticker_volume_upper_limit = 8 * math.pow(10, ticker_volume_max_no_of_digits - 1)
    else:
      ticker_volume_upper_limit = 10 * math.pow(10, ticker_volume_max_no_of_digits - 1)

    logging.debug("The upper limit for volume is " + str(ticker_volume_upper_limit))
    ticker_volume_ytick_list = []
    ticker_volume_yticklabels_list = []
    for i_idx in range(0, 5, 1):
      ticker_volume_ytick_list.append(i_idx * (ticker_volume_upper_limit / 4))
      ticker_volume_yticklabels_list.append(human_format(ticker_volume_ytick_list[i_idx], precision=1))
      logging.debug("Index " + str(i_idx) + " Tick Label " + str(ticker_volume_ytick_list[i_idx]) + " Tick label Text " + str(ticker_volume_yticklabels_list[i_idx]))

    # Get the Sundays in the date range to act as grid in the candle and volume plots
    candle_sunday_dates = pd.date_range(date_str_list_candles[candle_chart_duration], date_str_list_candles[0],freq='W-SUN')
    logging.debug("The Sunday dates are\n" + str(candle_sunday_dates))

    candle_sunday_dates_str = []
    for x in candle_sunday_dates:
      logging.debug("The original Sunday Date is :" + str(x))
      candle_sunday_dates_str.append(x.date().strftime('%m/%d/%Y'))

    logging.debug("The modified Sunday dates are\n" + str(candle_sunday_dates_str))
    logging.info("Prepared the Data for Volume Bars")
    # ---------------------------------------------------------------------------

    chart_print_eps_div_numbers_list = []
    if (g_dict_chart_options['print_eps_and_div_numbers'] == "Both"):
      logging.debug("User Specified that the script should make two sets of charts")
      logging.debug("One     Set with EPS and Dividend Numbers Printed on the chart")
      logging.debug("Another Set with EPS and Dividend Numbers NOT printed on the chart")
      chart_print_eps_div_numbers_list = [1, 0]
    elif (g_dict_chart_options['print_eps_and_div_numbers'] == "Yes"):
      logging.debug("User Specified that the script should print the EPS and dividend numbers on the chart")
      logging.debug("So, the script will prepare ONE chart  per ticker WITH the EPS and Dividend numbers on the chart")
      chart_print_eps_div_numbers_list = [1]
    elif (g_dict_chart_options['print_eps_and_div_numbers'] == "No"):
      logging.debug("User Specified that the script should NOT print the EPS and dividend numbers on the chart")
      logging.debug("So, the script will prepare ONE chart  per ticker WITHOUT the EPS and Dividend numbers on the chart")
      chart_print_eps_div_numbers_list = [0]
    else:
      logging.error("Could not figure out whether to prepare charts with or without ")
      logging.error("printing the EPS and Dividend numbers of the chart")
      logging.error("Please correctly specify in g_dict_chart_options->print_eps_and_div_numbers and rerun")
      sys.exit(1)

    # #############################################################################
    # #############################################################################
    # #############################################################################
    # ###########                                                        ##########
    # ###########                                                        ##########
    # ###########                    NOW PLOT EVERYTHING                 ##########
    # ###########                                                        ##########
    # ###########                                                        ##########
    # #############################################################################
    # #############################################################################
    # #############################################################################
    # fig, main_plt = plt.subplots()

    logging.info("Now starting to Plot everything that was prepared")
    if (len(chart_print_eps_div_numbers_list) > 1):
      logging.info("User wants more than one iteration for charts loop - through 'g_dict_chart_options['print_eps_and_div_numbers']' options")
      logging.info("Will Iterate with values for chart_print_eps_div_numbers_val set as : " + str(chart_print_eps_div_numbers_list))

    for chart_print_eps_div_numbers_val in chart_print_eps_div_numbers_list:
      if (len(chart_print_eps_div_numbers_list) > 1):
        logging.info("")
        logging.info("***** Iterating through Chart loop with \"chart_print_eps_div_numbers_val\" set to : " + str(chart_print_eps_div_numbers_val))
      else:
        logging.debug("Preparing Chart with \"chart_print_eps_div_numbers_val\" set to : " + str(chart_print_eps_div_numbers_val))

      fig = plt.figure()
      main_plt = plt.subplot2grid((5, 6), (0, 0), colspan=5, rowspan=5)
      candle_plt = plt.subplot2grid((5, 6), (0, 5), colspan=1, rowspan=4)
      volume_plt = plt.subplot2grid((5, 6), (4, 5), colspan=1, rowspan=1)
      plt.subplots_adjust(hspace=0, wspace=0)

      # fig.set_size_inches(16, 10)  # Length x height
      fig.set_size_inches(14.431, 7.639)  # Length x height
      # fig.subplots_adjust(right=0.90)

      # fig.autofmt_xdate()
      # This works - Named colors / color palette in matplotlib
      # https://stackoverflow.com/questions/22408237/named-colors-in-matplotlib
      main_plt.set_facecolor("lightgrey")
      candle_plt.set_facecolor("aliceblue")
      volume_plt.set_facecolor("honeydew")

      plt.text(x=0.03, y=0.915, s=ticker_company_name + "(" + ticker + ")", fontsize=18, fontweight='bold', ha="left", transform=fig.transFigure)
      ## Append to show that if chart uses Adjusted Earnings and if so,
      ## change the color of sector and industry line
      if (str(ticker_config_series['Use_Diluted_or_Adjusted_EPS']) == "Adjusted"):
        ticker_industry += " (( Plot uses Adj Earnings ))"
        plt.text(x=0.03, y=0.90, s=ticker_sector + " - " + ticker_industry, fontsize=11, fontweight='bold', fontstyle='italic', ha="left", color="magenta", transform=fig.transFigure)
      else:
        plt.text(x=0.03, y=0.90, s=ticker_sector + " - " + ticker_industry, fontsize=11, fontweight='bold', fontstyle='italic', ha="left", transform=fig.transFigure)

      plt.text(x=0.03, y=0.866, s=chart_update_date_str, fontsize=9, fontweight='bold', fontstyle='italic', ha="left", transform=fig.transFigure)
      # main_plt.text(x=.45, y=.95, s=adjusted_eps_str, fontsize=9, family='monospace', transform=fig.transFigure, bbox=dict(facecolor='lavender', edgecolor='k', pad=2.0, alpha=1))
      main_plt.text(x=.28, y=.98, s=adjusted_eps_str, fontsize=9, family='monospace', transform=fig.transFigure, bbox=dict(facecolor='lavender', edgecolor='k', pad=2.0, alpha=1))
      main_plt.text(x=.526, y=.8655, s=pt_print_str, fontsize=9, family='monospace', transform=fig.transFigure, bbox=dict(facecolor='lavender', edgecolor='k', pad=2.0, alpha=1))
      main_plt.text(x=.653, y=.865, s=price_eps_growth_str_textbox, fontsize=9, family='monospace', transform=fig.transFigure, bbox=dict(facecolor='lavender', edgecolor='k', pad=2.0, alpha=1))

      # fig.suptitle(r'{\fontsize{30pt}{3em}\selectfont{}{Mean WRFv3.5 LHF\n}{\fontsize{18pt}{3em}\selectfont{}(September 16 - October 30, 2012)}')
      # fig.suptitle(ticker_company_name + "("  +ticker +")" + "\n" + ticker_sector + "  " + ticker_industry, fontsize=18,x=0.22,y=.95)
      # This works too...may use that is set the subtitle for the plot
      # main_plt.set_title(ticker_company_name + "("  +ticker +")", fontsize=18,horizontalalignment='right')

      # Various plots that share the same x axis(date)
      price_plt = main_plt.twinx()
      annual_past_eps_plt = main_plt.twinx()
      annual_projected_eps_plt = main_plt.twinx()
      # schiller_pe_times_yr_eps_plt = main_plt.twinx()
      # # schiller_pe_normalized_plt  = main_plt.twinx()
      # schiller_ann_requested_red_line_plt = main_plt.twinx()
      upper_channel_plt = main_plt.twinx()
      lower_channel_plt = main_plt.twinx()
      analyst_adjusted_channel_upper_plt = main_plt.twinx()
      analyst_adjusted_channel_lower_plt = main_plt.twinx()
      # yr_eps_02_5_plt = main_plt.twinx()
      # yr_eps_05_0_plt = main_plt.twinx()
      # yr_eps_10_0_plt = main_plt.twinx()
      # yr_eps_20_0_plt = main_plt.twinx()
      # yr_eps_02_5_plt[0] = main_plt.twinx()
      if (annual_eps_adjust_json):
        annual_eps_adjusted_slice_plt = main_plt.twinx()
      if (plot_spy):
        spy_plt = main_plt.twinx()
      if (pays_dividend == 1):
        dividend_plt = main_plt.twinx()

      logging.debug("Type of fig " + str(type(fig)) + \
                    "\nType of main_plt " + str(type(main_plt)) + \
                    "\nType of price_plt: " + str(type(price_plt)) + \
                    "\nType of yr_eps_plt: " + str(type(annual_past_eps_plt)) + \
                    "\nType of upper_channel_plt: " + str(type(upper_channel_plt)))
      # -----------------------------------------------------------------------------
      # Main Plot - This is the Q EPS vs Date
      # -----------------------------------------------------------------------------
      # This works - I have commented out so that the code does not print out the xlate
      # and I can get more space below the date ticks
      # main_plt.set_xlabel('Date')
      # main_plt.set_ylabel('Earnings')
      main_plt.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
      main_plt.tick_params(axis="y", direction="in", pad=-22)
      main_plt.set_yscale(chart_type_idx.lower())
      main_plt_inst = main_plt.plot(date_list[0:plot_period_int], qtr_eps_expanded_list[0:plot_period_int], label='Q EPS',
                                    color="deeppink", marker='.', markersize='10')

      # Print out the last reported Q_EPS on the chart
      # check if the date is in the plot range
      logging.debug("The last black diamond is at index" + str(eps_date_list_eps_report_date_index) + "and the date is" + str(eps_date_list_eps_report_date_match) + "and the repored Q EPS is " + str(qtr_eps_list[eps_date_list_eps_report_date_index]))
      # check if the date is in the plot range
      if (chart_print_eps_div_numbers_val == 1):
        for i in range(5):
          if (date_list[plot_period_int] <= qtr_eps_date_list[eps_date_list_eps_report_date_index + i] <= date_list[0]):
            if (qtr_eps_lim_lower <= qtr_eps_list[eps_date_list_eps_report_date_index + i] <= qtr_eps_lim_upper):
              x = float("{0:.2f}".format(qtr_eps_list[eps_date_list_eps_report_date_index + i]))
              main_plt.text(qtr_eps_date_list[eps_date_list_eps_report_date_index + i], qtr_eps_list[eps_date_list_eps_report_date_index + i], x, color='Purple', fontsize='small',fontstyle='italic', fontweight=1000,
                            bbox=dict(facecolor='lavender', edgecolor='k', pad=2.0, alpha=0.1),horizontalalignment='center', verticalalignment='bottom')
      logging.info("Printed the QTR EPS number on the chart (For the Last 4 reported quarters)")
      # -----------------------------------------------------------------------------

      # -----------------------------------------------------------------------------
      # Historical Price Plot
      # -----------------------------------------------------------------------------
      # Now printing price on the right side of the candle plot
      # price_plt.set_ylabel('Price', color='k')
      # This works - this will move the tick labels inside the plot
      price_plt.tick_params(axis="y", direction="in", pad=-22)
      price_plt.set_ylim(price_lim_lower, price_lim_upper)
      price_plt.set_yscale(chart_type_idx.lower())
      price_plt_inst = price_plt.plot(date_list[0:plot_period_int], ticker_adj_close_list[0:plot_period_int],
                                      label='Adj Close', color="brown", linestyle='-')
      # Get the buy and sells from the personal json file, along with the comments.
      # The buy and sells are plotted throught markers while the comments are
      # plotted through the annotate
      if (ticker not in personal_json.keys()):
        logging.debug("json data for " + str(ticker) + "does not exist in " + str(personal_json_file) + " file")
      else:
        markers_buy_date = []
        markers_sell_date = []
        buy_price = ""
        sell_price = ""
        for i_idx in range(len(personal_json[ticker]["Buy_Sell"])):
          if ("Buy_Date" in personal_json[ticker]["Buy_Sell"][i_idx]):
            buy_date_str = personal_json[ticker]["Buy_Sell"][i_idx]["Buy_Date"]
            buy_date_datetime = dt.datetime.strptime(buy_date_str, '%m/%d/%Y').date()
            buy_match_date = min(date_list, key=lambda d: abs(d - buy_date_datetime))
            markers_buy_date.append(date_list.index(buy_match_date))
            logging.debug("Index " + str(i_idx) + " Buy Match Date " + str(buy_match_date))
            if ("Buy_Price_str" in personal_json[ticker]["Buy_Sell"][i_idx]):
              buy_price_str = personal_json[ticker]["Buy_Sell"][i_idx]["Buy_Price_str"]
              price_plt.annotate(buy_price_str, xy=(date_list[date_list.index(buy_match_date)], ticker_adj_close_list[date_list.index(buy_match_date)]),
                                 xytext=(-15, -30), textcoords='offset points', ha='left', fontweight='bold',
                                 bbox=dict(facecolor='white', edgecolor='black', boxstyle='square,pad=.5', alpha=.25))
          if ("Sell_Date" in personal_json[ticker]["Buy_Sell"][i_idx]):
            sell_date_str = personal_json[ticker]["Buy_Sell"][i_idx]["Sell_Date"]
            sell_date_datetime = dt.datetime.strptime(sell_date_str, '%m/%d/%Y').date()
            sell_match_date = min(date_list, key=lambda d: abs(d - sell_date_datetime))
            markers_sell_date.append(date_list.index(sell_match_date))
            logging.debug("Index " + str(i_idx) + " Sell Match Date " + str(sell_match_date))
            if ("Sell_Price_str" in personal_json[ticker]["Buy_Sell"][i_idx]):
              sell_price_str = personal_json[ticker]["Buy_Sell"][i_idx]["Sell_Price_str"]
              price_plt.annotate(sell_price_str, xy=(date_list[date_list.index(sell_match_date)], ticker_adj_close_list[date_list.index(sell_match_date)]),
                                 xytext=(-15, -30), textcoords='offset points', ha='left', fontweight='bold',
                                 bbox=dict(facecolor='white', edgecolor='black', boxstyle='square,pad=.5', alpha=.25))

        # This works : This is outside the for loop because it has the list for markevery
        price_plt.plot(date_list[0:plot_period_int], ticker_adj_close_list[0:plot_period_int],
                       marker="^", markerfacecolor=buy_sell_color, markeredgewidth=1, markeredgecolor='k',
                       markersize=13, markevery=markers_buy_date, linestyle='None')
        price_plt.plot(date_list[0:plot_period_int], ticker_adj_close_list[0:plot_period_int],
                       marker="s", markerfacecolor=buy_sell_color, markeredgewidth=1, markeredgecolor='k',
                       markersize=12, markevery=markers_sell_date, linestyle='None')
        logging.info("Inserted Buy and Sell Points on the Chart, if specified")

      g_var_annotate_actual_qtr_earnings = 0
      if (g_var_annotate_actual_qtr_earnings == 1):
        logging.debug("Will annotate the price plt at actual qtr earnings date")
        i_idx = 0

        for i_date in (qtr_eps_report_date_list_dt):
          y_coord = 75
          annotate_text = ""
          # (x_coord, y_coord) = config_json[ticker]["Plot_Annotate"][i_idx]["Line_Length"].split(":")
          match_date = min(date_list, key=lambda d: abs(d - i_date))
          logging.debug("The matching date is " + str(match_date) + " at index " + str(date_list.index(match_date)) +
                        " and the price is " + str(ticker_adj_close_list[date_list.index(match_date)]))
          if (i_idx % 2 == 0):
            y_coord = -75
          price_plt.annotate(annotate_text,
                             xy=(date_list[date_list.index(match_date)], ticker_adj_close_list[date_list.index(match_date)]),
                             xytext=(0, y_coord), textcoords='offset points',
                             # arrowprops=dict(arrowstyle='->',facecolor='black', headwidth=.2),
                             arrowprops={'arrowstyle': '-', 'ls': 'dashed', 'lw': '.75', 'color': 'black'},
                             bbox=dict(facecolor='none', edgecolor='black', boxstyle='round,pad=1'))
          i_idx += 1
      # -----------------------------------------------------------------------------

      # -----------------------------------------------------------------------------
      # Index Price Plot
      # -----------------------------------------------------------------------------
      if (plot_spy):
        spy_plt.set_ylim(price_lim_lower, price_lim_upper)
        spy_plt.set_yscale(chart_type_idx)
        spy_plt_inst = spy_plt.plot(date_list[0:plot_period_int], spy_adj_close_list[0:plot_period_int], label='S&P',
                                    color="green", linestyle='-')
      # -----------------------------------------------------------------------------

      # -----------------------------------------------------------------------------
      # Average Annual EPS Plot
      # -----------------------------------------------------------------------------
      # Find the eps points that fall in the plot range
      annual_past_eps_plt.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
      annual_past_eps_plt.set_yscale(chart_type_idx.lower())
      annual_past_eps_plt.set_yticks([])
      annual_past_eps_plt_inst = annual_past_eps_plt.plot(date_list[0:plot_period_int],
                                                          yr_past_eps_expanded_list[0:plot_period_int], label='4 qtrs/4',
                                                          color="black", marker='D', markersize='4')
      annual_projected_eps_plt.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
      annual_projected_eps_plt.set_yscale(chart_type_idx.lower())
      annual_projected_eps_plt.set_yticks([])
      annual_projected_eps_plt_inst = annual_projected_eps_plt.plot(date_list[0:plot_period_int],
                                                                    yr_projected_eps_expanded_list[0:plot_period_int],
                                                                    label='4 qtrs/4', color="White", marker='D',
                                                                    markersize='4')
      # todo : maybe change this to only have the value printed out at the year ends
      if (chart_print_eps_div_numbers_val == 1):
        for i in range(len(yr_eps_date_list)):
          logging.debug("The Date is " + str(yr_eps_date_list[i]) + " Corresponding EPS " + str(yr_eps_list[i]))
          # check if the date is in the plot range
          if (date_list[plot_period_int] <= yr_eps_date_list[i] <= date_list[0]):
            if (qtr_eps_lim_lower <= yr_eps_list[i] <= qtr_eps_lim_upper):
              # This works - This will only print out the yr_eps numbers at fiscal year end - This is desired by Ann
              # I am just commeting it out for now as I want to see all yr_eps numbers for all the quarters
              # Only put the numbers for fiscal year
              # Get the abbreviated month of the eps report date...sometimes the company
              # will report a few days later after the end of the month - so get the prev
              # month too and compare it against the Fiscal year end of the company
              # yr_eps_date_curr_month = yr_eps_date_list[i].month
              # yr_eps_date_prev_month = yr_eps_date_list[i].month-1 if yr_eps_date_list[i].month > 1 else 12
              # yr_eps_date_curr_month_abbr = calendar.month_abbr[yr_eps_date_curr_month]
              # yr_eps_date_prev_month_abbr = calendar.month_abbr[yr_eps_date_prev_month]
              # # print ("The month for earnings is", yr_eps_date_curr_month_abbr, "and the previous month is ",yr_eps_date_prev_month_abbr)
              # if ( ("BA-"+yr_eps_date_curr_month_abbr == fiscal_yr_str) or ("BA-"+yr_eps_date_prev_month_abbr == fiscal_yr_str)):
              #   x = float("{0:.2f}".format(yr_eps_list[i]))
              #   main_plt.text(yr_eps_date_list[i], yr_eps_list[i], x, fontsize=11, horizontalalignment='center',
              #                 verticalalignment='bottom')

              x = float("{0:.2f}".format(yr_eps_list[i]))
              main_plt.text(yr_eps_date_list[i], yr_eps_list[i], x, fontsize=11, horizontalalignment='center', verticalalignment='bottom')
      logging.info("Printed the YR EPS numbers on the chart (For Black and White Diamonds)")
      if (annual_eps_adjust_json):
        # If the annual eps was ajusted, then plot those diamonds in <the color Ann likes>
        annual_eps_adjusted_slice_plt.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
        annual_eps_adjusted_slice_plt.set_yticks([])
        annual_eps_adjusted_slice_plt_inst = annual_eps_adjusted_slice_plt.plot(date_list[0:plot_period_int],
                                                                                yr_eps_adj_slice_expanded_list[0:plot_period_int], label='4 qtrs/4',
                                                                                color="gold", marker='D', markersize='4')
        if (chart_print_eps_div_numbers_val == 1):
          for i in range(len(yr_eps_adj_slice_date_list)):
            logging.debug("The Date is " + str(yr_eps_adj_slice_date_list[i]) + " Corresponding EPS " + str(yr_eps_adj_slice_list[i]))
            # check if the date is in the plot range
            if (date_list[plot_period_int] <= yr_eps_adj_slice_date_list[i] <= date_list[0]):
              if (qtr_eps_lim_lower <= yr_eps_adj_slice_list[i] <= qtr_eps_lim_upper):
                x = float("{0:.2f}".format(yr_eps_adj_slice_list[i]))
                main_plt.text(yr_eps_adj_slice_date_list[i], yr_eps_adj_slice_list[i], x, fontsize=11,horizontalalignment='center',
                              verticalalignment='bottom')
        logging.info("Printed the Adjusted YR EPS numbers on the chart (For Golden Diamonds)")
      # -----------------------------------------------------------------------------

      # Comment out the plotting of Ann Schiller PE stuff temporarily
      # # -----------------------------------------------------------------------------
      # # Plot normalzied Schiller PE
      # # -----------------------------------------------------------------------------
      # # schiller_pe_normalized_plt.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
      # # schiller_pe_normalized_plt.set_yticks([])
      # # schiller_pe_normalized_plt_inst = schiller_pe_normalized_plt.plot(date_list[0:plot_period_int],
      # #                                             schiller_pe_normalized_list_smooth[0:plot_period_int],
      # #                                             label='Normalized Schiller PE', color='green', linestyle='-')
      #
      # schiller_ann_requested_red_line_plt.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
      # schiller_ann_requested_red_line_plt.set_yticks([])
      # schiller_ann_requested_red_line_plt_inst = schiller_ann_requested_red_line_plt.plot(date_list[0:plot_period_int],
      #                                             schiller_ann_requested_red_line_list_3[0:plot_period_int],
      #                                             label='Normalized Schiller PE', color='red', linestyle='-')
      #
      # # -----------------------------------------------------------------------------
      #
      #
      # # -----------------------------------------------------------------------------
      # # Plot normalized Schiller PE mulitpled by YR EPS
      # # -----------------------------------------------------------------------------
      # schiller_pe_times_yr_eps_plt.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
      # schiller_pe_times_yr_eps_plt.set_yticks([])
      # schiller_pe_times_yr_eps_plt_inst = schiller_pe_times_yr_eps_plt.plot(date_list[0:plot_period_int],
      #                                             schiller_pe_times_yr_eps_list[0:plot_period_int],
      #                                             label='Schiller PE time EPS', color='darkviolet', linestyle='-')
      # for i_date_str in fiscal_yr_dates:
      #   i_date = dt.datetime.strptime(i_date_str, '%m/%d/%Y').date()
      #   if (i_date < dt.datetime.now().date()):
      #     match_date = min(date_list, key=lambda d: abs(d - i_date))
      #     i_idx = date_list.index(match_date)
      #     if (date_list[plot_period_int] <= match_date <= date_list[0]):
      #       x = float("{0:.2f}".format(schiller_pe_times_yr_eps_list[i_idx]))
      #       y = float("{0:.2f}".format(schiller_pe_normalized_list_smooth[i_idx]))
      #       z = float("{0:.2f}".format(schiller_ann_requested_red_line_list_3[i_idx]))
      #       main_plt.text(date_list[i_idx], schiller_pe_times_yr_eps_list[i_idx], x, fontsize=11, horizontalalignment='center', verticalalignment='bottom')
      #       # main_plt.text(date_list[i_idx], schiller_pe_normalized_list_smooth[i_idx], y, fontsize=11, horizontalalignment='center', verticalalignment='bottom')
      #       main_plt.text(date_list[i_idx], schiller_ann_requested_red_line_list_3[i_idx], z, fontsize=11, horizontalalignment='center', verticalalignment='bottom')
      # # -----------------------------------------------------------------------------

      # -----------------------------------------------------------------------------
      # Dividend plot
      # -----------------------------------------------------------------------------
      if (pays_dividend == 1):
        dividend_plt.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
        dividend_plt.set_yscale(chart_type_idx.lower())
        dividend_plt.set_yticks([])
        dividend_plt_inst = dividend_plt.plot(date_list[0:plot_period_int], dividend_expanded_list[0:plot_period_int],
                                              label='Dividend', color="Saddlebrown", marker='x', markersize='8')
        if (chart_print_eps_div_numbers_val == 1):
          for i in range(len(dividend_date_list)):
            if (date_list[plot_period_int] <= dividend_date_list[i] <= date_list[0]):
              if (qtr_eps_lim_lower <= dividend_list[i] <= qtr_eps_lim_upper):
                x = float("{0:.2f}".format(dividend_list[i]))
                main_plt.text(dividend_date_list[i], dividend_list_multiplied[i], x, fontsize=6,horizontalalignment='center',
                              verticalalignment='bottom')
        logging.info("Printed the Dividend numbers on the chart")
      # -----------------------------------------------------------------------------

      # -----------------------------------------------------------------------------
      # Price channels
      # -----------------------------------------------------------------------------
      for i_idx in range(number_of_growth_proj_overlays):

        # Search google for :
        # TypeError: 'AxesSubplot'  object  does  not support  item  assignment
        # https: // stackoverflow.com / questions / 19953348 / error - when - looping - to - produce - subplots
        # https: // stackoverflow.com / questions / 45993370 / matplotlib - indexing - error - on - plotting
        # Probably something needs to be done with subplots are declared ahove...need to know how many subplots will
        # be created
        # yr_eps_02_5_plt[i_idx,0] = main_plt.twinx()
        # yr_eps_02_5_plt[i_idx,0].set_ylim(qtr_eps_lim_lower,qtr_eps_lim_upper)
        # yr_eps_02_5_plt[i_idx,0].set_yticks([])
        # yr_eps_02_5_plt_inst[i_idx,0] = yr_eps_02_5_plt[i_idx,0].plot(date_list[0:plot_period_int],
        #                                                 yr_eps_02_5_growth_expanded_list[i_idx][0:plot_period_int],
        #                                                 label='Q 2.5%',color="Cyan", linestyle='-', linewidth=1)

        # This is a hack for now
        if (i_idx == 0):
          yr_eps_02_5_plt_0 = main_plt.twinx()
          yr_eps_02_5_plt_0.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
          yr_eps_02_5_plt_0.set_yticks([])
          yr_eps_02_5_plt_inst_0 = yr_eps_02_5_plt_0.plot(date_list[0:plot_period_int],
                                                          yr_eps_02_5_growth_expanded_list[i_idx][0:plot_period_int],
                                                          label='Q 2.5%', color="Cyan", linestyle='-', linewidth=1)
          yr_eps_05_0_plt_0 = main_plt.twinx()
          yr_eps_05_0_plt_0.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
          yr_eps_05_0_plt_0.set_yticks([])
          yr_eps_05_0_plt_inst_0 = yr_eps_05_0_plt_0.plot(date_list[0:plot_period_int],
                                                          yr_eps_05_0_growth_expanded_list[i_idx][0:plot_period_int],
                                                          label='Q 5.0%', color="Yellow", linestyle='-', linewidth=1)
          yr_eps_10_0_plt_0 = main_plt.twinx()
          yr_eps_10_0_plt_0.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
          yr_eps_10_0_plt_0.set_yticks([])
          yr_eps_10_0_plt_inst_0 = yr_eps_10_0_plt_0.plot(date_list[0:plot_period_int],
                                                          yr_eps_10_0_growth_expanded_list[i_idx][0:plot_period_int],
                                                          label='Q 10%', color="Cyan", linestyle='-', linewidth=1)
          yr_eps_20_0_plt_0 = main_plt.twinx()
          yr_eps_20_0_plt_0.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
          yr_eps_20_0_plt_0.set_yticks([])
          yr_eps_20_0_plt_inst_0 = yr_eps_20_0_plt_0.plot(date_list[0:plot_period_int],
                                                          yr_eps_20_0_growth_expanded_list[i_idx][0:plot_period_int],
                                                          label='Q 20%', color="Yellow", linestyle='-', linewidth=1)
        elif (i_idx == 1):
          yr_eps_02_5_plt_1 = main_plt.twinx()
          yr_eps_02_5_plt_1.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
          yr_eps_02_5_plt_1.set_yticks([])
          yr_eps_02_5_plt_inst_1 = yr_eps_02_5_plt_1.plot(date_list[0:plot_period_int],
                                                          yr_eps_02_5_growth_expanded_list[i_idx][0:plot_period_int],
                                                          label='Q 2.5%', color="Cyan", linestyle='-', linewidth=1)
          yr_eps_05_0_plt_1 = main_plt.twinx()
          yr_eps_05_0_plt_1.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
          yr_eps_05_0_plt_1.set_yticks([])
          yr_eps_05_0_plt_inst_1 = yr_eps_05_0_plt_1.plot(date_list[0:plot_period_int],
                                                          yr_eps_05_0_growth_expanded_list[i_idx][0:plot_period_int],
                                                          label='Q 5.0%', color="Yellow", linestyle='-', linewidth=1)
          yr_eps_10_0_plt_1 = main_plt.twinx()
          yr_eps_10_0_plt_1.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
          yr_eps_10_0_plt_1.set_yticks([])
          yr_eps_10_0_plt_inst_1 = yr_eps_10_0_plt_1.plot(date_list[0:plot_period_int],
                                                          yr_eps_10_0_growth_expanded_list[i_idx][0:plot_period_int],
                                                          label='Q 10%', color="Cyan", linestyle='-', linewidth=1)
          yr_eps_20_0_plt_1 = main_plt.twinx()
          yr_eps_20_0_plt_1.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
          yr_eps_20_0_plt_1.set_yticks([])
          yr_eps_20_0_plt_inst_1 = yr_eps_20_0_plt_1.plot(date_list[0:plot_period_int],
                                                          yr_eps_20_0_growth_expanded_list[i_idx][0:plot_period_int],
                                                          label='Q 20%', color="Yellow", linestyle='-', linewidth=1)
        elif (i_idx == 2):
          yr_eps_02_5_plt_2 = main_plt.twinx()
          yr_eps_02_5_plt_2.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
          yr_eps_02_5_plt_2.set_yticks([])
          yr_eps_02_5_plt_inst_2 = yr_eps_02_5_plt_2.plot(date_list[0:plot_period_int],
                                                          yr_eps_02_5_growth_expanded_list[i_idx][0:plot_period_int],
                                                          label='Q 2.5%', color="Cyan", linestyle='-', linewidth=1)
          yr_eps_05_0_plt_2 = main_plt.twinx()
          yr_eps_05_0_plt_2.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
          yr_eps_05_0_plt_2.set_yticks([])
          yr_eps_05_0_plt_inst_2 = yr_eps_05_0_plt_2.plot(date_list[0:plot_period_int],
                                                          yr_eps_05_0_growth_expanded_list[i_idx][0:plot_period_int],
                                                          label='Q 5.0%', color="Yellow", linestyle='-', linewidth=1)
          yr_eps_10_0_plt_2 = main_plt.twinx()
          yr_eps_10_0_plt_2.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
          yr_eps_10_0_plt_2.set_yticks([])
          yr_eps_10_0_plt_inst_2 = yr_eps_10_0_plt_2.plot(date_list[0:plot_period_int],
                                                          yr_eps_10_0_growth_expanded_list[i_idx][0:plot_period_int],
                                                          label='Q 10%', color="Cyan", linestyle='-', linewidth=1)
          yr_eps_20_0_plt_2 = main_plt.twinx()
          yr_eps_20_0_plt_2.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
          yr_eps_20_0_plt_2.set_yticks([])
          yr_eps_20_0_plt_inst_2 = yr_eps_20_0_plt_2.plot(date_list[0:plot_period_int],
                                                          yr_eps_20_0_growth_expanded_list[i_idx][0:plot_period_int],
                                                          label='Q 20%', color="Yellow", linestyle='-', linewidth=1)

      # yr_eps_02_5_plt.set_ylim(qtr_eps_lim_lower,qtr_eps_lim_upper)
      # yr_eps_02_5_plt.set_yticks([])
      # yr_eps_02_5_plt_inst = yr_eps_02_5_plt.plot(date_list[0:plot_period_int], yr_eps_02_5_growth_expanded_list[0:plot_period_int], label = 'Q 2.5%',color="Cyan",linestyle = '-', linewidth=1)

      # yr_eps_05_0_plt.set_ylim(qtr_eps_lim_lower,qtr_eps_lim_upper)
      # yr_eps_05_0_plt.set_yticks([])
      # yr_eps_05_0_plt_inst = yr_eps_05_0_plt.plot(date_list[0:plot_period_int], yr_eps_05_0_growth_expanded_list[0:plot_period_int], label = 'Q 5%',color="Yellow",linestyle = '-', linewidth=1)
      #
      # yr_eps_10_0_plt.set_ylim(qtr_eps_lim_lower,qtr_eps_lim_upper)
      # yr_eps_10_0_plt.set_yticks([])
      # yr_eps_10_0_plt_inst = yr_eps_10_0_plt.plot(date_list[0:plot_period_int], yr_eps_10_0_growth_expanded_list[0:plot_period_int], label = 'Q 10%',color="Cyan",linestyle = '-', linewidth=1)
      #
      # yr_eps_20_0_plt.set_ylim(qtr_eps_lim_lower,qtr_eps_lim_upper)
      # yr_eps_20_0_plt.set_yticks([])
      # yr_eps_20_0_plt_inst = yr_eps_20_0_plt.plot(date_list[0:plot_period_int], yr_eps_20_0_growth_expanded_list[0:plot_period_int], label = 'Q 20%',color="Yellow",linestyle = '-', linewidth=1)
      # -----------------------------------------------------------------------------

      # -----------------------------------------------------------------------------
      # Price channels
      # -----------------------------------------------------------------------------
      for i_idx in range(entries_in_qtr_sales_bv_fcf_overlay_df):


        # This is a hack for now
        if (i_idx == 0):
          qtr_sales_plt_0 = main_plt.twinx()
          qtr_sales_plt_0.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
          qtr_sales_plt_0.set_yticks([])
          qtr_sales_plt_0_inst_0 = qtr_sales_plt_0.plot(date_list[0:plot_period_int],
                                                          qtr_sales_expanded_list[i_idx][0:plot_period_int],
                                                          label='Q 2.5%', color="Green", linestyle='-', linewidth=7, alpha=0.4)
          # x = float("{0:.2f}".format(qtr_sales_expanded_list[i_idx][plot_period_int]))
          # main_plt.text(date_list[plot_period_int], qtr_sales_expanded_list[i_idx][plot_period_int], x, fontsize=6,
          #               horizontalalignment='center', verticalalignment='bottom')


          qtr_bv_plt_0 = main_plt.twinx()
          qtr_bv_plt_0.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
          qtr_bv_plt_0.set_yticks([])
          qtr_bv_plt_0 = qtr_bv_plt_0.plot(date_list[0:plot_period_int],
                                                          qtr_bv_expanded_list[i_idx][0:plot_period_int],
                                                          label='Q 5.0%', color="Brown", linestyle='-', linewidth=7, alpha=0.3)
        elif (i_idx == 1):
          qtr_sales_plt_1 = main_plt.twinx()
          qtr_sales_plt_1.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
          qtr_sales_plt_1.set_yticks([])
          qtr_sales_plt_1 = qtr_sales_plt_1.plot(date_list[0:plot_period_int],
                                                          qtr_sales_expanded_list[i_idx][0:plot_period_int],
                                                          label='Q 2.5%', color="Green", linestyle='-', linewidth=7, alpha=0.4)
          qtr_bv_plt_1 = main_plt.twinx()
          qtr_bv_plt_1.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
          qtr_bv_plt_1.set_yticks([])
          qtr_bv_plt_1 = qtr_bv_plt_1.plot(date_list[0:plot_period_int],
                                                          qtr_bv_expanded_list[i_idx][0:plot_period_int],
                                                          label='Q 5.0%', color="Brown", linestyle='-', linewidth=7, alpha=0.3)
        elif (i_idx == 2):
          qtr_sales_plt_1 = main_plt.twinx()
          qtr_sales_plt_1.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
          qtr_sales_plt_1.set_yticks([])
          qtr_sales_plt_1 = qtr_sales_plt_1.plot(date_list[0:plot_period_int],
                                                          qtr_sales_expanded_list[i_idx][0:plot_period_int],
                                                          label='Q 2.5%', color="Green", linestyle='-', linewidth=7, alpha=0.4)
          qtr_bv_plt_2 = main_plt.twinx()
          qtr_bv_plt_2.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
          qtr_bv_plt_2.set_yticks([])
          qtr_bv_plt_2 = qtr_bv_plt_2.plot(date_list[0:plot_period_int],
                                                          qtr_bv_expanded_list[i_idx][0:plot_period_int],
                                                          label='Q 5.0%', color="Brown", linestyle='-', linewidth=7, alpha=0.3)
      # -----------------------------------------------------------------------------



      # -----------------------------------------------------------------------------
      # Upper Price Channel Plot
      # -----------------------------------------------------------------------------
      # upper_channel_plt.set_ylabel('Upper_guide', color = 'b')
      # upper_channel_plt.spines["right"].set_position(("axes", 1.2))
      if (chart_type_idx == "Linear"):
        upper_channel_plt.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
        upper_channel_plt.set_yscale(chart_type_idx.lower())
        upper_channel_plt.set_yticks([])
        upper_channel_plt_inst = upper_channel_plt.plot(date_list[0:plot_period_int],
                                                        upper_price_channel_list[0:plot_period_int], label='Channel', color="blue",
                                                        linestyle='-')

        analyst_adjusted_channel_upper_plt.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
        analyst_adjusted_channel_upper_plt.set_yscale(chart_type_idx.lower())
        analyst_adjusted_channel_upper_plt.set_yticks([])
        analyst_adjusted_channel_upper_plt_inst = analyst_adjusted_channel_upper_plt.plot(date_list[0:plot_period_int],
                                                                                          analyst_adjusted_channel_upper[
                                                                                          0:plot_period_int],label='Channel',
                                                                                          color="blue",
                                                                                          linestyle='-.')
        analyst_adjusted_channel_lower_plt.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
        analyst_adjusted_channel_lower_plt.set_yscale(chart_type_idx.lower())
        analyst_adjusted_channel_lower_plt.set_yticks([])
        analyst_adjusted_channel_lower_plt_inst = analyst_adjusted_channel_lower_plt.plot(date_list[0:plot_period_int],
                                                                                          analyst_adjusted_channel_lower[
                                                                                          0:plot_period_int],label='Channel',
                                                                                          color="blue",
                                                                                          linestyle='-.')
      # -----------------------------------------------------------------------------

      # -----------------------------------------------------------------------------
      # Lower Price Channel Plot
      # -----------------------------------------------------------------------------
      # upper_channel_plt.set_ylabel('Upper_guide', color = 'b')
      # upper_channel_plt.spines["right"].set_position(("axes", 1.2))
      if (chart_type_idx == "Linear"):
        lower_channel_plt.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
        lower_channel_plt.set_yscale(chart_type_idx.lower())
        lower_channel_plt.set_yticks([])
        lower_channel_plt_inst = lower_channel_plt.plot(date_list[0:plot_period_int],
                                                        lower_price_channel_list[0:plot_period_int],label='Price Channel', color="blue",
                                                        linestyle='-')
      # -----------------------------------------------------------------------------

      # -----------------------------------------------------------------------------
      # Candlestick and volume Plots
      # -----------------------------------------------------------------------------
      # Google search - remove weekends from matplotlib plot
      # Note the candlestick chart - while deciding the color of candle - compare the current day open with current day close
      # If the current day close is higher than the current day open - then the color of the candle is choosen as colorup
      # If the current day close is lower  than the current day open - then the color of the candle is choosen as colordown
      # It does not compare the current day close with previous day close -- This can be investigated but it is not too
      # bad for our use - First off we can look at the relative position of the candles to see whether it is up or down from
      # the previous day candle (many a times it is clear just by looking at it). And then I have put in the code that
      # compare the previous close with the current close to decide upon the color of the volume bars...so the volume bars
      # can be helpful in that situation. Note that this creates difference in the color of the volume bars and candles but
      # if the user knows what is going on then it is not that bad
      candle_plt_inst = candlestick_ohlc(candle_plt, quotes[0:candle_chart_duration], width=1, colorup='mediumseagreen', colordown='darksalmon')
      candle_plt_MA200_inst = candle_plt.plot(date_list_candles[0:candle_chart_duration], MA_Price_200_list[0:candle_chart_duration], linewidth=.5, color='black', label='SMA200')
      candle_plt_MA50_inst = candle_plt.plot(date_list_candles[0:candle_chart_duration], MA_Price_50_list[0:candle_chart_duration], linewidth=.5, color='blue', label='SMA50')
      candle_plt_MA20_inst = candle_plt.plot(date_list_candles[0:candle_chart_duration], MA_Price_20_list[0:candle_chart_duration], linewidth=.5, color='green', label='SMA20')
      candle_plt_MA10_inst = candle_plt.plot(date_list_candles[0:candle_chart_duration], MA_Price_10_list[0:candle_chart_duration], linewidth=.5, color='deeppink', label='SMA10')
      volume_plt_inst = volume_plt.bar(date_list_candles[0:candle_chart_duration], volume[0:candle_chart_duration], width=1, color=bar_color_list[0:candle_chart_duration])
      volume_plt_MA = volume_plt.twinx()
      volume_plt_MA_inst = volume_plt_MA.plot(date_list_candles[0:candle_chart_duration],MA_volume_50_list[0:candle_chart_duration], color='blue', label='SMA10')
      # -----------------------------------------------------------------------------

      # -----------------------------------------------------------------------------
      # Set the gridlines for all plots
      # -----------------------------------------------------------------------------
      # import matplotlib.pyplot as plt
      # fig, ax = plt.subplots()
      # ax.set_yticks([0.2, 0.6, 0.8], minor=False)
      # ax.set_yticks([0.3, 0.55, 0.7], minor=True)
      # ax.yaxis.grid(True, which='major')
      # ax.yaxis.grid(True, which='minor')
      # plt.show()
      #  Set the Minor and Major ticks and then show the gird
      # xstart,xend = price_plt.get_xlim()
      # ystart,yend = price_plt.get_ylim()
      # xstart_date = matplotlib.dates.num2date(xstart)
      # xend_date = matplotlib.dates.num2date(xend)
      #
      # print ("The xlimit Start: ", xstart_date, " End: ", xend_date, "Starting year", xstart_date.year )
      # print ("The ylimit Start: ", ystart, " End: ", yend )
      #
      # print ("The years between the start and end dates are : ", range(xstart_date.year, xend_date.year+1))
      # qtr_dates = pd.date_range(xstart_date.year, xend_date.year, freq='Q')
      # yr_dates = pd.date_range('2018-01', '2020-05', freq='Y')
      # print ("Quarterly Dates are ", qtr_dates)
      #
      # main_plt.set_xticks(qtr_dates, minor=True)
      # # main_plt.set_xticks(yr_dates, minor=False)
      # main_plt.xaxis.grid(which='major', linestyle='-')
      # main_plt.xaxis.grid(which='minor',linestyle='--')
      # main_plt.minorticks_on()
      # main_plt.yaxis.grid(True)
      #
      major_xgrid_color = "darkgrey"
      if (fiscal_yr_str != "BA-Dec"):
        major_xgrid_color = "peru"

      main_plt.set_xticks(fiscal_yr_dates, minor=False)
      main_plt.set_xticks(fiscal_qtr_dates, minor=True)
      main_plt.xaxis.set_tick_params(width=5)
      # This works - Just turning this off as Ann did not want them...
      # if (chart_type_idx == "Linear"):
      # main_plt.set_xticklabels(fiscal_qtr_dates, rotation=90, fontsize=7,  color='k',  minor=True)
      # main_plt.set_xticklabels(fiscal_yr_dates, rotation=90, fontsize=8, color='blue', minor=False, fontstyle='italic')
      main_plt.set_xticklabels(fiscal_yr_dates, rotation=0, fontsize=10, color='blue', minor=False, fontstyle='italic')
      main_plt.grid(which='major', axis='x', linestyle='-', color=major_xgrid_color, linewidth=1.25)
      if (chart_type_idx == "Linear"):
        main_plt.grid(which='minor', axis='x', linestyle='--', color='darkturquoise', linewidth=.4)
      main_plt.grid(which='major', axis='y', linestyle='--', color='green', linewidth=.5)

      # candle_plt.set_xticks([])
      candle_plt.set_xticks(candle_sunday_dates, minor=False)
      candle_plt.grid(True)
      candle_plt.grid(True, axis='x', which='major', linestyle='--', color='lightgray')
      # This works - To turn individual grid axis off or on
      # candle_plt.grid(False,axis='y')
      # candle_plt.set_ylabel('Price', color='k')
      candle_plt.yaxis.set_label_position("right")
      candle_plt.yaxis.tick_right()

      volume_plt.set_xticks(candle_sunday_dates, minor=False)
      volume_plt.grid(True)
      volume_plt.grid(True, axis='x', which='major', linestyle='--', color='lightgray')
      # volume_plt.set_xticklabels(candle_sunday_dates_str,rotation=90, fontsize=7, color='k', minor=False)
      volume_plt.set_xticklabels([])
      volume_plt.set_ylim(0, ticker_volume_upper_limit)
      volume_plt.yaxis.tick_right()
      volume_plt.set_yticks(ticker_volume_ytick_list)
      volume_plt.set_yticklabels(ticker_volume_yticklabels_list, rotation=0, fontsize=8, color='k', minor=False)

      volume_plt_MA.set_ylim(0, ticker_volume_upper_limit)
      # volume_plt_MA.set_xticks([])
      volume_plt_MA.set_yticks([])
      volume_plt_MA.text(date_list_candles[0], MA_volume_50_list[0], human_format(MA_volume_50_list[0]),
                         fontsize=7, color='blue', fontweight='bold',
                         bbox=dict(facecolor='lavender', edgecolor='k', pad=2.0, alpha=1))
      plt.setp(plt.gca().get_xticklabels(), rotation=90)
      # -----------------------------------------------------------------------------

      # -----------------------------------------------------------------------------
      # Collect the labels for the subplots and then create the legends
      # -----------------------------------------------------------------------------
      '''
      # This works perfectly well - but Ann wants no Legends for now
      lns = price_plt_inst + main_plt_inst + annual_past_eps_plt_inst + lower_channel_plt_inst
      if (pays_dividend):
        lns = lns + dividend_plt_inst
      if (number_of_growth_proj_overlays > 0):
        lns = lns + yr_eps_02_5_plt_inst_0 + yr_eps_05_0_plt_inst_0 \
                  + yr_eps_10_0_plt_inst_0 + yr_eps_20_0_plt_inst_0
      if (plot_spy):
        lns = lns + spy_plt_inst
      # sys.exit(1)
      labs = [l.get_label() for l in lns]
      main_plt.legend(lns, labs, bbox_to_anchor=(-.06, -0.13), loc="lower right", borderaxespad=2, fontsize='x-small')
      '''
      # This works perfectly well as well
      # main_plt.legend(lns, labs,bbox_to_anchor=(-.10,-0.13), loc="lower left", borderaxespad=2,fontsize = 'x-small')
      # This works if we don't have defined the inst of the plots. In this case we
      # collect the things manually and then put them in legend
      # h1,l1 = main_plt.get_legend_handles_labels()
      # h2,l2 = price_plt.get_legend_handles_labels()
      # main_plt.legend(h1+h2, l1+l2, loc=2)
      # -----------------------------------------------------------------------------

      # -----------------------------------------------------------------------------
      # If there is an Text box that needs to be inserted then
      # insert it here...There can be multiple of them inserted
      # The locations for AnchoredText at
      # https://matplotlib.org/api/offsetbox_api.html
      # 'upper right'  : 1,
      # 'upper left'   : 2,
      # 'lower left'   : 3,
      # 'lower right'  : 4,
      # 'right'        : 5, (same as 'center right', for back-compatibility)
      # 'center left'  : 6,
      # 'center right' : 7,
      # 'lower center' : 8,
      # 'upper center' : 9,
      # 'center'       : 10,
      # -----------------------------------------------------------------------------
      if ((ticker in config_json.keys()) and ("Anchored_Text" in config_json[ticker])):
        logging.debug("Found Anchored Text " + str(config_json[ticker]["Anchored_Text"]))
        if (len(config_json[ticker]["Anchored_Text"].keys()) > 0):
          split_keys = config_json[ticker]["Anchored_Text"].keys()
          logging.debug("Location(s) are : " + str(split_keys))
          for i_key in split_keys:
            location = i_key
            my_text = config_json[ticker]["Anchored_Text"][i_key]
            logging.debug("Location : " + str(location) + ", Text : " + str(my_text))
            a_text = AnchoredText(my_text, loc=location)
            main_plt.add_artist(a_text)
      else:
        number_of_anchored_texts = 4
        for i in range(number_of_anchored_texts):
          if (i == 0):
            location = 9
            my_text = "Ann Constant is: " + str(round(ann_constant, 4))
          elif (i == 1):
            location = 6
            my_text = "Test for Box number 2"
          elif (i == 2):
            location = 2
            my_text = "Test Box in upper left"
          else:
            location = 4
            my_text = "What do you want me to put here?"
          # todo : Maybe add transparency to the box?
          a_text = AnchoredText(my_text, loc=location)
          main_plt.add_artist(a_text)
      # -----------------------------------------------------------------------------

      # -----------------------------------------------------------------------------
      # Annonate at a particular (x,y) = (Date,Prcie) on the chart.
      # User can sepcifiy muliple annotates - however right now the code only supports
      # annotated on (Date, Price) pair - price_plt. The user specifies the date and
      # the code finds out the corresponding price and annotates that point.
      # If however - there is a need to annotate (say on annual eps) then that can
      # be done as well - In order to support that feature the use has the specify
      # it in the annoate jon and then there will have to be a if statement, that will
      # choose the appropriate plot
      # -----------------------------------------------------------------------------
      if (ticker not in config_json.keys()):
        logging.debug("json data for " + str(ticker) + " does not exist in " + str(configuration_json_file) + " file")
      else:
        if ("Plot_Annotate" in config_json[ticker]):
          logging.debug("The number of plot annotates requested by the user are " + str(len(config_json[ticker]["Plot_Annotate"])))
          for i_idx in range(len(config_json[ticker]["Plot_Annotate"])):
            date_to_annotate = config_json[ticker]["Plot_Annotate"][i_idx]["Date"]
            date_to_annotate_datetime = dt.datetime.strptime(date_to_annotate, '%m/%d/%Y').date()
            annotate_text = config_json[ticker]["Plot_Annotate"][i_idx]["Text"]
            (x_coord, y_coord) = config_json[ticker]["Plot_Annotate"][i_idx]["Line_Length"].split(":")

            match_date = min(date_list, key=lambda d: abs(d - date_to_annotate_datetime))
            logging.debug("The matching date is " + str(match_date) + " at index " + str(date_list.index(match_date)) +
                          " and the price is " + str(ticker_adj_close_list[date_list.index(match_date)]))
            price_plt.annotate(annotate_text,
                               xy=(date_list[date_list.index(match_date)],ticker_adj_close_list[date_list.index(match_date)]),
                               xytext=(int(x_coord), int(y_coord)), textcoords='offset points',arrowprops=dict(facecolor='black', width=.25),
                               bbox=dict(facecolor='none', edgecolor='black', boxstyle='round,pad=1'))
            # arrowprops=dict(facecolor='black', width=1))

      # -----------------------------------------------------------------------------

      # -----------------------------------------------------------------------------
      # Save the Chart with the date and time as prefix
      # -----------------------------------------------------------------------------
      # This works too instead of two line
      # date_time =  dt.datetime.now().strftime("%Y_%m_%d_%H_%M")

      # This adjusts the dimensions (in relative tems of the plot area
      # so example the plots take from 5% to 95% of the horizontal space (start the 5% and stop at 95%)
      fig.subplots_adjust(left=.02, right=.97, bottom=0.05, top=.86)

      now = dt.datetime.now()
      # date_time = now.strftime("%Y_%m_%d_%H_%M")
      date_time = now.strftime("%Y_%m_%d")
      # Only show the plot if we are making only one chart
      if (chart_type_idx == "Log"):
        if (chart_print_eps_div_numbers_val == 1):
          fig.savefig(chart_dir + "\\" + chart_type_idx + "\\" + "Charts_With_Numbers" + "\\" + ticker + "_Log_" + date_time + ".jpg",dpi=200, bbox_inches=0)
        else:
          fig.savefig(chart_dir + "\\" + chart_type_idx + "\\" + "Charts_Without_Numbers" + "\\" + ticker + "_Log_" + date_time + ".jpg",dpi=200, bbox_inches=0)
      else:
        if (linear_chart_type_idx == 'Linear'):
          if (chart_print_eps_div_numbers_val == 1):
            fig.savefig(chart_dir + "\\" + "Linear" + "\\" + "Charts_With_Numbers" + "\\" + ticker + "_" + date_time + ".jpg",dpi=200, bbox_inches=0)
          else:
            fig.savefig(chart_dir + "\\" + "Linear" + "\\" + "Charts_Without_Numbers" + "\\" + ticker + "_" + date_time + ".jpg",dpi=200, bbox_inches=0)
        else:
          if (chart_print_eps_div_numbers_val == 1):
            fig.savefig(chart_dir + "\\" + "Long_Linear" + "\\" + "Charts_With_Numbers" + "\\" + ticker + "_Long_Linear_" + date_time + ".jpg",dpi=200, bbox_inches=0)
          else:
            fig.savefig(chart_dir + "\\" + "Long_Linear" + "\\" + "Charts_Without_Numbers" + "\\" + ticker + "_Long_Linear_" + date_time + ".jpg",dpi=200, bbox_inches=0)

      if (len(ticker_list) == 1) and (len(linear_chart_type_list) == 1) and (len(chart_print_eps_div_numbers_list) == 1):
        plt.show()
      else:
        plt.close(fig)

  logging.info("All Done")
  # -----------------------------------------------------------------------------

