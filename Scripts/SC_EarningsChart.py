import pandas as pd
import matplotlib
import os
import math
import json
import sys
import datetime as dt
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from matplotlib.offsetbox import AnchoredText
from SC_logger import my_print as my_print
from yahoofinancials import YahooFinancials
from mpl_finance import candlestick_ohlc
from pandas.plotting import register_matplotlib_converters

register_matplotlib_converters()

def millify(n):
  n = float(n)
  millidx = max(0,min(len(millnames)-1,int(math.floor(0 if n == 0 else math.log10(abs(n))/3))))
  return '{:.0f}{}'.format(n / 10**(3 * millidx), millnames[millidx])

def human_format(num, precision=2, suffixes=['', 'K', 'M', 'B', 'T', 'P']):
  m = sum([abs(num / 1000.0 ** x) >= 1 for x in range(1, len(suffixes))])
  return f'{num / 1000.0 ** m:.{precision}f}{suffixes[m]}'
# =============================================================================
# User defined function
# This function takes in a list that has nan in between numeric values and
# replaces the nan in the middle with a step so that the 'markers' can be
#  converted to a line while plotting
# # =============================================================================
def get_growth(current, previous):
  if current == previous:
    return 0
  try:
    return round((abs(current - previous) / previous) * 100.0,2)
  except ZeroDivisionError:
    return float('inf')

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

  print("The original List is ", l)
  print("The clean List is ", l_clean)
  print("The indices of non non values is ", l_indices)

  i_int = 0
  while (i_int < len(l_clean) - 1):
    print("Clean List index:", i_int, ", Clean List value:", l_clean[i_int], ", Corresponding List index:",
          l_indices[i_int])
    step = (l_clean[i_int] - l_clean[i_int + 1]) / (l_indices[i_int + 1] - l_indices[i_int])
    start_index = l_indices[i_int]
    stop_index = l_indices[i_int + 1]
    print("The step is ", step, "Start and Stop Indices are ", start_index, stop_index)
    j_int = start_index + 1
    while (j_int < stop_index):
      l_mod[j_int] = float(l_mod[j_int - 1]) - step
      print("Updating index", j_int, "to ", l_mod[j_int])
      j_int += 1

    i_int += 1

  print("Modified List is", l_mod)
  return (l_mod)


# =============================================================================

# todo :
# deal with fiscal quarter
# Handle Annotated text
# See how you can add comments
# What format the file should be save
# Get the code debug friendly
# How to create other subplots that have the book value etc
#   Maybe use subplots for it
# How to use earnings projections
# Test out the values from the file
# How to show values when you click
# Get the Average PE for last 1, 3, 5 and 10 years and get the forward PE
#   and get it printed in the box
# If possible superimpose the PE line in the chart

# =============================================================================
# Define the various filenames and Directory Paths to be used
# =============================================================================
dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
chart_dir = "..\\" + "Charts"
historical_dir = "\\..\\" + "Historical"
earnings_dir = "\\..\\" + "Earnings"
dividend_dir = "\\..\\" + "Dividend"
log_dir = "\\..\\" + "Logs"
tracklist_file = "Tracklist.csv"
tracklist_file_full_path = dir_path + user_dir + "\\" + tracklist_file
configuration_file = "Configurations.csv"
configuration_json = "Configurations.json"
configurations_file_full_path = dir_path + user_dir + "\\" + configuration_file

config_df = pd.read_csv(dir_path + user_dir + "\\" + configuration_file)
with open(dir_path + user_dir + "\\" + configuration_json) as json_file:
  config_json = json.load(json_file)
# =============================================================================


# todo : Should be able to read from the Tracklist file in a loop
# and save the charts in the charts directory
ticker = "MED"

# Open the Log file in write mode
logfile = dir_path + log_dir + "\\" + ticker + "_log.txt"
debug_fh = open(logfile, "w+")

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

# =============================================================================
# Read the Earnings file for the ticker
# =============================================================================
qtr_eps_df = pd.read_csv(dir_path + "\\" + earnings_dir + "\\" + ticker + "_earnings.csv",delimiter=",")
log_lvl = "error"
debug_str = "The Earnings df is \n" + qtr_eps_df.to_string()
stdout = 0;
my_print(debug_fh, debug_str, stdout, log_lvl.upper())

print ("The Earnings df is \n", qtr_eps_df)
# todo : Error out if any elements in the date_list are nan except the trailing (this includes
# todo : leading nan and any nan in the list itself
qtr_eps_date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in qtr_eps_df.Date.dropna().tolist()]
qtr_eps_list = qtr_eps_df.Q_EPS_Diluted.tolist()
print("The date list for qtr_eps is ", qtr_eps_date_list, "\nand the number of elements are", len(qtr_eps_date_list))
print("The Earnings list for qtr_eps is ", qtr_eps_list)
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
  print("The date list for Dividends is ", dividend_date_list, "\nand the number of elements are",
        len(dividend_date_list))
  print("The Amounts for dividends is ", dividend_list)
# =============================================================================

# =============================================================================
# Read the config file and decide all the parms that are needed for plot
# =============================================================================
config_df.set_index('Ticker', inplace=True)
print("The configuration df", config_df)
if ticker in config_df.index:
  ticker_config_series = config_df.loc[ticker]
  print("Then configurations for ", ticker, " is ", ticker_config_series)
else:
  # Todo : Create a default series with all nan so that it can be cleaned up in the next step
  print("Configuration Entry for ", ticker, " not found...continuing with default values")


# =============================================================================
# Handle splits before proceeding as splits can change the qtr_eps
# =============================================================================
# todo : Test out various cases of splits so that the code is robust
split_dates = list()
split_multiplier = list()
print("Tickers in json data: ", config_json.keys())
if (ticker not in config_json.keys()):
  print("json data for ", ticker, "does not exist in", configuration_json, "file")
else:
  if ("Splits" in config_json[ticker]):
    # if the length of the keys is > 0
    if (len(config_json[ticker]["Splits"].keys()) > 0):
      split_keys = config_json[ticker]["Splits"].keys()
      print("Split Date list is: ", split_keys)
      for i_key in split_keys:
        print("Split Date :", i_key, "Split Factor :", config_json[ticker]["Splits"][i_key])
        try:
          split_dates.append(dt.datetime.strptime(str(i_key), "%m/%d/%Y").date())
        except (ValueError):
          print("\n***** Error : The split Date: ", i_key,
                "does not seem to be right. Should be in the format %m/%d/%Y...please check *****")
          sys.exit(1)
        try:
          (numerator, denominator) = config_json[ticker]["Splits"][i_key].split(":")
          split_multiplier.append(float(denominator) / float(numerator))
        except (ValueError):
          print("\n***** Error : The split factor: ", config_json[ticker]["Splits"][i_key], "for split date :", i_key,
                "does not seem to have right format [x:y]...please check *****")
          sys.exit(1)
      for i in range(len(split_dates)):
        qtr_eps_list_mod = qtr_eps_list.copy()
        print("Split Date :", split_dates[i], " Multiplier : ", split_multiplier[i])
        for j in range(len(qtr_eps_date_list)):
          if (split_dates[i] > qtr_eps_date_list[j]):
            qtr_eps_list_mod[j] = round(qtr_eps_list[j] * split_multiplier[i], 4)
            print("Earnings date ", qtr_eps_date_list[j], " is older than split date. Changed ", qtr_eps_list[j],
                  " to ",
                  qtr_eps_list_mod[j])
        qtr_eps_list = qtr_eps_list_mod.copy()
    else:
      print("\"Splits\" exits but seems empty for ", ticker)
  else:
    print("\"Splits\" does not exist for ", ticker)
# =============================================================================


# ============================================================================
# Get the eps value list to the same length as eps date list and
# check if these list has any nan. If it has any nan then error out and let
# the user correct the earning file.

# Set the length of qtr_eps_list same as date_list.
# This gets rid of any earnings that are beyond the last date.
# This is not a common case but could occur because of copy and paste and then
# ignorance on the part of the user to not remove the "extra" earnings
# This also makes sure that the eps date list and eps value list have the same
# number of entries.
len_qtr_eps_date_list = len(qtr_eps_date_list)
len_qtr_eps_list = len(qtr_eps_list)
if (len_qtr_eps_date_list < len_qtr_eps_list):
  del qtr_eps_list[len_qtr_eps_date_list:]
print("The Earnings list for qtr_eps is ", qtr_eps_list)

# Check if now the qtr_eps_list still has any undefined elements...flag an error and exit
# This will indicate any empty cells are either the beginning or in the middle of the eps
# column in the csv
if (sum(math.isnan(x) for x in qtr_eps_list) > 0):
  print("ERROR : There are some undefined EPS numbers in the Earnings file, Please correct and rerun")
  exit()

# So - if we are successful till this point - we have made sure that
# 1. There are no nan in the date list
# 2. There are no nan in the eps list
# 3. Number of elements in the qtr_eps_date_list are equal to the number of
#    element in the qtr_eps_list
# =============================================================================

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
print("The Historical df is \n", historical_df)
ticker_adj_close_list = historical_df.Adj_Close.tolist()
print ("Historical Adj. Prices", type(ticker_adj_close_list))
date_str_list = historical_df.Date.tolist()
print("The date list from historical df is ", date_str_list)
date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in date_str_list]
print("The date list for historical is ", date_list, "\nit has ", len(date_list), " entries")
# =============================================================================

# =============================================================================
# Create the Annual EPS list from the Quarter EPS list.
# The last 3 elemnts of the annual EPS are going to be blank because the last annual EPS corresponds
# the the last but 4th Quarter EPS
# =============================================================================
i_int = 0
yr_eps_list = list()
while (i_int < (len(qtr_eps_list) - 3)):
  annual_average_eps = (qtr_eps_list[i_int] + \
                        qtr_eps_list[i_int + 1] + \
                        qtr_eps_list[i_int + 2] + \
                        qtr_eps_list[i_int + 3]) / 4

  print("Iteration #, ", i_int, " Quartely EPS, Annual EPS", \
        qtr_eps_list[i_int], \
        qtr_eps_list[i_int + 1], \
        qtr_eps_list[i_int + 2], \
        qtr_eps_list[i_int + 3], \
        annual_average_eps)
  yr_eps_list.append(annual_average_eps)
  i_int += 1
print("Annual EPS List ", yr_eps_list, "\nand the number of elements are", len(yr_eps_list))

# I am not sure why I wanted this but seems like a good thing to be able to make
# a dataframe from lists. This is not used anywhere in the code ahead...so commented
# out for now7
# yr_eps_list_tmp = yr_eps_list
# yr_eps_list_tmp.append('Not_calculated')
# yr_eps_list_tmp.append('Not_calculated')
# yr_eps_list_tmp.append('Not_calculated')
# This is good. This works
# earnings_df = pd.DataFrame(np.column_stack([qtr_eps_date_list, qtr_eps_list, yr_eps_list_tmp]),
#                                columns=['Date', 'Q EPS', 'Annual EPS'])
# print ("The Earnings DF is ", earnings_df)
# =============================================================================


# =============================================================================
# Create a qtr_eps_expanded and dividend_expanded list
# We are here trying to create the list that has the same number of elements
# as the historical date_list and only the elements that have the Quarter EPS
# have valid values, other values in the expanded list are nan...and hence the
# expanded lists are initially initialized to nan
# =============================================================================
qtr_eps_expanded_list = []
dividend_expanded_list = []
for i in range(len(date_list)):
  qtr_eps_expanded_list.append(float('nan'))
  if (pays_dividend == 1):
    dividend_expanded_list.append(float('nan'))

# Now look for the date in eps datelist, match it with the closest index in the
# date list from historical and then assign the qtr eps to that index in the qtr
# eps expanded list. Do the same for divident expanded list
for qtr_eps_date in qtr_eps_date_list:
  curr_index = qtr_eps_date_list.index(qtr_eps_date)
  print("Looking for ", qtr_eps_date)
  match_date = min(date_list, key=lambda d: abs(d - qtr_eps_date))
  print("The matching date for QTR EPS Date: ", qtr_eps_date, "is ", match_date, " at index ",
        date_list.index(match_date))
  qtr_eps_expanded_list[date_list.index(match_date)] = qtr_eps_list[curr_index]

print("The expanded qtr eps list is ", qtr_eps_expanded_list, "\nand the number of elements are",
      len(qtr_eps_expanded_list))


if (pays_dividend == 1):
  if (math.isnan(ticker_config_series['Dividend_Multiplier_Factor'])):
    dividend_multiplier = 1.0
  else:
    dividend_multiplier = float(ticker_config_series['Dividend_Multiplier_Factor'])
  dividend_list_multiplied = [x * dividend_multiplier for x in dividend_list]
  print ("Dividend List is", dividend_list)
  print ("Multiplied Divided List is", dividend_list_multiplied)

  for dividend_date in dividend_date_list:
    curr_index = dividend_date_list.index(dividend_date)
    print("Looking for ", dividend_date)
    match_date = min(date_list, key=lambda d: abs(d - dividend_date))
    print("The matching date for QTR EPS Date: ", dividend_date, "is ", match_date, " at index ",
          date_list.index(match_date))
    dividend_expanded_list[date_list.index(match_date)] = dividend_list_multiplied[curr_index]

  print("The expanded Dividend list is ", dividend_expanded_list, "\nand the number of elements are",
        len(dividend_expanded_list))
# =============================================================================

# =============================================================================
# Create annual eps date list and then create
# Expanded annual EPS list just like the expanded Quarter EPS list was created
# However the expanded Annual EPS list is really three lists...to create a different
# series in the plot/graph later
# yr_eps_expanded_list - This will end up to create the price channels
# annual_past_eps_expanded_list - contains only the yr eps that is older than the
#   current date - This will end up as black diamonds in the chart
# annual_projected_eps_expanded_list - contains only the yr epx that is newer
#   than the current date - This will end up as white diamonds in the chart
# =============================================================================
# Remove the last 3 dates from the qtr_eps_date_list to create yr_eps_date_list
yr_eps_date_list = qtr_eps_date_list[0:len(qtr_eps_date_list) - 3]

yr_eps_expanded_list = []
annual_past_eps_expanded_list = []
annual_projected_eps_expanded_list = []
for i in range(len(date_list)):
  yr_eps_expanded_list.append(float('nan'))
  annual_past_eps_expanded_list.append(float('nan'))
  annual_projected_eps_expanded_list.append(float('nan'))

for yr_eps_date in yr_eps_date_list:
  curr_index = yr_eps_date_list.index(yr_eps_date)
  print("Looking for ", yr_eps_date)
  match_date = min(date_list, key=lambda d: abs(d - yr_eps_date))
  print("The matching date is ", match_date, " at index ", date_list.index(match_date))
  yr_eps_expanded_list[date_list.index(match_date)] = yr_eps_list[curr_index]
  # Check if the matching data is in the past or in the future
  if (match_date < dt.date.today()):
    print("The matching date is in the past")
    annual_past_eps_expanded_list[date_list.index(match_date)] = yr_eps_list[curr_index]
  else:
    print("The matching date is in the future")
    annual_projected_eps_expanded_list[date_list.index(match_date)] = yr_eps_list[curr_index]
print("The Expanded Annual EPS List is: ", yr_eps_expanded_list)
# =============================================================================

# =============================================================================
# Handle the earning Growth projection overlays
# =============================================================================
# Read the json to get the information for the earnings projection overlays
# At the end of this - we should have
# 1. The number of overlays that need to be made in the chart
# 2. A list that contains the start dates for each of the overlays and
# 3. A corresponding list that contains the stop dates for each of the overlay

number_of_growth_proj_overlays = 0
start_date_for_yr_eps_growth_proj_list = []
stop_date_for_yr_eps_growth_proj_list = []
if (ticker not in config_json.keys()):
  print("json data for ", ticker, "does not exist in", configuration_json, "file")
else:
  if ("Earnings_growth_projection_overlay" in config_json[ticker]):
    tmp_df = pd.DataFrame(config_json[ticker]["Earnings_growth_projection_overlay"])
    number_of_growth_proj_overlays = len(tmp_df.index)
    print("The Sorted and reindexed dataframe is \n", tmp_df, "\nAnd the length of the DateFrame is",
          number_of_growth_proj_overlays)
    # This works : Delete the rows that have Ignore in any column
    tmp_df.drop(tmp_df[(tmp_df.Start_Date == "Ignore") | (tmp_df.Stop_Date == "Ignore")].index, inplace=True)
    # Conver the start Dates to datetime, add it as a separate column, and then
    # sort the dataframe based on that datetime column and reindex the dateframe
    tmp_df['Start_Date_datetime'] = pd.to_datetime(tmp_df['Start_Date'], format='%m/%d/%Y')
    tmp_df.sort_values('Start_Date_datetime', inplace=True)
    tmp_df.reset_index(inplace=True, drop=True)
    # tmp_df.set_index('Start_Date', inplace=True)
    number_of_growth_proj_overlays = len(tmp_df.index)
    print("The Sorted and reindexed dataframe is \n", tmp_df, "\nAnd the length of the DateFrame is",
          number_of_growth_proj_overlays)
    # Replace the "End" and "Next" in the stop dates with the appropriate value
    # "End" gets replaced by the end date (which it at index 0) that the historical date list has
    # (So the overlay will extent all the way to the right of the chart)
    # "Next" gets replaced by the next row start date (remember that the dataframe is already sorted
    # ascending with the start dates - so in essence the current row earning projection overlay
    # will stop at the next start date
    tmp_df.Stop_Date.replace(to_replace='End', value=date_str_list[0], inplace=True)
    # This works : Replaces the stop date of the current row with the value of start date from the next row
    tmp_df.Stop_Date.replace(to_replace='Next', value=tmp_df.Start_Date.shift(-1), inplace=True)
    print("The Sorted and reindexed and cleaned dataframe is \n", tmp_df, "\nAnd the length of the DateFrame is",
          number_of_growth_proj_overlays)
    # This works : Finally put those start and stop dates as datetimes in their own lists
    # start_date_for_yr_eps_growth_proj_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in
    #                                           tmp_df.Start_Date.tolist()]
    # stop_date_for_yr_eps_growth_proj_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in
    #                                          tmp_df.Stop_Date.tolist()]
    # print("The Start Date List for EPS Growth Projection is", start_date_for_yr_eps_growth_proj_list)
    # sys.exit(1)

if (number_of_growth_proj_overlays > 0):
  # Create a list of lists equal to the number of rows of the dataframe - which is the same as
  # the number of overlays that are specified in the json file)
  yr_eps_02_5_growth_expanded_list = [[] for _ in range(number_of_growth_proj_overlays)]
  yr_eps_05_0_growth_expanded_list = [[] for _ in range(number_of_growth_proj_overlays)]
  yr_eps_10_0_growth_expanded_list = [[] for _ in range(number_of_growth_proj_overlays)]
  yr_eps_20_0_growth_expanded_list = [[] for _ in range(number_of_growth_proj_overlays)]

  for i_idx, row in tmp_df.iterrows():
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
      print("Updating for index", i)
      yr_eps_02_5_growth_list[i] = 1.025 * float(yr_eps_02_5_growth_list[i + 1])
      yr_eps_05_0_growth_list[i] = 1.05 * float(yr_eps_05_0_growth_list[i + 1])
      yr_eps_10_0_growth_list[i] = 1.10 * float(yr_eps_10_0_growth_list[i + 1])
      yr_eps_20_0_growth_list[i] = 1.20 * float(yr_eps_20_0_growth_list[i + 1])

    print("The Annual eps list", yr_eps_list)
    print("The 2.5% growth rate eps list", yr_eps_02_5_growth_list)
    print("The   5% growth rate eps list", yr_eps_05_0_growth_list)
    print("The  10% growth rate eps list", yr_eps_10_0_growth_list)
    print("The  20% growth rate eps list", yr_eps_20_0_growth_list)

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
      print("Looking for ", yr_eps_date)
      match_date = min(date_list, key=lambda d: abs(d - yr_eps_date))
      print("The matching date is ", match_date, " at index ", date_list.index(match_date))
      yr_eps_02_5_growth_expanded_list_unsmooth[date_list.index(match_date)] = yr_eps_02_5_growth_list[curr_index]
      yr_eps_05_0_growth_expanded_list_unsmooth[date_list.index(match_date)] = yr_eps_05_0_growth_list[curr_index]
      yr_eps_10_0_growth_expanded_list_unsmooth[date_list.index(match_date)] = yr_eps_10_0_growth_list[curr_index]
      yr_eps_20_0_growth_expanded_list_unsmooth[date_list.index(match_date)] = yr_eps_20_0_growth_list[curr_index]

    # Populate the list of lists
    yr_eps_02_5_growth_expanded_list[i_idx] = smooth_list(yr_eps_02_5_growth_expanded_list_unsmooth)
    yr_eps_05_0_growth_expanded_list[i_idx] = smooth_list(yr_eps_05_0_growth_expanded_list_unsmooth)
    yr_eps_10_0_growth_expanded_list[i_idx] = smooth_list(yr_eps_10_0_growth_expanded_list_unsmooth)
    yr_eps_20_0_growth_expanded_list[i_idx] = smooth_list(yr_eps_20_0_growth_expanded_list_unsmooth)
# =============================================================================



# -----------------------------------------------------------------------------
# Find out how many years need to be plotted. If the historical data is available
# for lesser time, then adjust the period to the length of the data_list
# -----------------------------------------------------------------------------
# todo : Maybe support a date there?
if (math.isnan(ticker_config_series['Linear_Chart_Duration_Years'])):
  # Deal with if the data availalbe in the historical tab is less than
  # user specified in the config file
  plot_period_int = 252 * 10
else:
  plot_period_int = 252 * int(ticker_config_series['Linear_Chart_Duration_Years'])

if (len(date_list) < plot_period_int):
  plot_period_int = len(date_list) -1
  print("Since the Historical Data (Length of the date list) is not available for all\
  the years that user is asking to plot for, so adjusting the plot for",\
  float(plot_period_int/252), "years (or", plot_period_int, "days)")
else:
  print ("Will plot for", plot_period_int, "years")

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

# ---------------------------------------------------------
# Get the upper and lower guide lines separation from the annual EPS
# ---------------------------------------------------------
# todo : what if the eps is negative then the multiplication makes it more negative
if (math.isnan(ticker_config_series['Upper Price Channel'])):
  upper_price_channel_list_unsmooth = [float(eps) + .5 * float(eps) for eps in yr_eps_expanded_list]
else:
  upper_price_channel_separation = float(ticker_config_series['Upper Price Channel'])
  upper_price_channel_list_unsmooth = [float(eps) + upper_price_channel_separation for eps in yr_eps_expanded_list]

if (math.isnan(ticker_config_series['Lower Price Channel'])):
  lower_price_channel_list_unsmooth = [float(eps) - .5 * float(eps) for eps in yr_eps_expanded_list]
else:
  lower_price_channel_separation = float(ticker_config_series['Lower Price Channel'])
  lower_price_channel_list_unsmooth = [float(eps) - lower_price_channel_separation for eps in yr_eps_expanded_list]

print("The upper channel unsmooth list is : ", upper_price_channel_list_unsmooth)
upper_price_channel_list = smooth_list(upper_price_channel_list_unsmooth)
lower_price_channel_list = smooth_list(lower_price_channel_list_unsmooth)
print("The upper Guide is ", upper_price_channel_list, "\nand the number of element is ", len(upper_price_channel_list))
print("The upper Guide is ", lower_price_channel_list, "\nand the number of element is ", len(lower_price_channel_list))

# This variable is added to the adjustments that are done to the channels because
# this is also the nubmer of days by which the channels get shifted left (or these
#  are the number of nan entries that are inserted in the channel list
days_in_2_qtrs = 126

# =============================================================================
# Get the adjustments that need to be done and do the price channels
# First read from the json file to know how may adjustments need to be done
# for the upper and lower price channels and store them in their separate lists
# respectively. After than process those separate list to make actual adjustments
# to the channel lines
# =============================================================================
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
  print("json data for ", ticker, "does not exist in", configuration_json, "file")
else:
  if ("Upper_Price_Channel_Adj" in config_json[ticker]):
    len_upper_price_channel_adj = len(config_json[ticker]["Upper_Price_Channel_Adj"])
    print("The number of Upper channel adjustments specified", len_upper_price_channel_adj)
    for i in range(len_upper_price_channel_adj):
      i_start_date = config_json[ticker]["Upper_Price_Channel_Adj"][i]["Start_Date"]
      i_stop_date = config_json[ticker]["Upper_Price_Channel_Adj"][i]["Stop_Date"]
      i_adj_amount = config_json[ticker]["Upper_Price_Channel_Adj"][i]["Adj_Amount"]
      try:
        upper_price_channel_adj_start_date_list.append(dt.datetime.strptime(i_start_date, "%m/%d/%Y").date())
        upper_price_channel_adj_stop_date_list.append(dt.datetime.strptime(i_stop_date, "%m/%d/%Y").date())
        upper_price_channel_adj_amount_list.append(float(i_adj_amount))
      except (ValueError):
        print(
          "\n***** Error : Either the Start/Stop Dates or the Adjust Amount are not in proper format for Upper_Price_Channel_Adj in Configuration json file.\n"
          "***** Error : The Dates should be in the format %m/%d/%Y and the Adjust Amount should be a int/float\n"
          "***** Error : Found somewhere in :", i_start_date, i_stop_date, i_adj_amount)
        sys.exit(1)

print("The Upper Channel Start Date List", upper_price_channel_adj_start_date_list)
print("The Upper Channel Stop Date List", upper_price_channel_adj_stop_date_list)
print("The Upper Channel Adjust List", upper_price_channel_adj_amount_list)

if (ticker not in config_json.keys()):
  print("json data for ", ticker, "does not exist in", configuration_json, "file")
else:
  if ("Lower_Price_Channel_Adj" in config_json[ticker]):
    len_lower_price_channel_adj = len(config_json[ticker]["Lower_Price_Channel_Adj"])
    print("The number of Lower channel adjustments specified", len_lower_price_channel_adj)
    for i in range(len_lower_price_channel_adj):
      i_start_date = config_json[ticker]["Lower_Price_Channel_Adj"][i]["Start_Date"]
      i_stop_date = config_json[ticker]["Lower_Price_Channel_Adj"][i]["Stop_Date"]
      i_adj_amount = config_json[ticker]["Lower_Price_Channel_Adj"][i]["Adj_Amount"]
      try:
        lower_price_channel_adj_start_date_list.append(dt.datetime.strptime(i_start_date, "%m/%d/%Y").date())
        lower_price_channel_adj_stop_date_list.append(dt.datetime.strptime(i_stop_date, "%m/%d/%Y").date())
        lower_price_channel_adj_amount_list.append(float(i_adj_amount))
      except (ValueError):
        print(
          "\n***** Error : Either the Start/Stop Dates or the Adjust Amount are not in proper format for Lower_Price_Channel_Adj in Configuration json file.\n"
          "***** Error : The Dates should be in the format %m/%d/%Y and the Adjust Amount should be a int/float\n"
          "***** Error : Found somewhere in :", i_start_date, i_stop_date, i_adj_amount)
        sys.exit(1)
print("The Lower Channel Start Date List", lower_price_channel_adj_start_date_list)
print("The Lower Channel Stop Date List", lower_price_channel_adj_stop_date_list)
print("The Lower Channel Adjust List", lower_price_channel_adj_amount_list)

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
      print("Date ", i_date, "lies between start Date", upper_price_channel_adj_start_date, "and stop Date",
            upper_price_channel_adj_stop_date, "at index ", i_index)
      upper_price_channel_list[i_index - days_in_2_qtrs] = upper_price_channel_list[
                                                             i_index - days_in_2_qtrs] + upper_price_channel_adj_amount

for i_idx in range(len_lower_price_channel_adj):
  lower_price_channel_adj_start_date = lower_price_channel_adj_start_date_list[i_idx]
  lower_price_channel_adj_stop_date = lower_price_channel_adj_stop_date_list[i_idx]
  lower_price_channel_adj_amount = lower_price_channel_adj_amount_list[i_idx]
  for i_date in date_list:
    if (lower_price_channel_adj_start_date <= i_date <= lower_price_channel_adj_stop_date):
      i_index = date_list.index(i_date)
      print("Date ", i_date, "lies between start Date", lower_price_channel_adj_start_date, "and stop Date",
            lower_price_channel_adj_stop_date, "at index ", i_index)
      lower_price_channel_list[i_index - days_in_2_qtrs] = lower_price_channel_list[
                                                             i_index - days_in_2_qtrs] + lower_price_channel_adj_amount
# =============================================================================

# Now shift the price channels by two quarters
# Approximately 6 months = 126 business days by inserting 126 nan at location 0
nan_list = []
for i in range(days_in_2_qtrs):
  upper_price_channel_list.insert(0, float('nan'))
  lower_price_channel_list.insert(0, float('nan'))

# ---------------------------------------------------------


# ---------------------------------------------------------
# Create the lower and upper Price limit
# ---------------------------------------------------------
if (math.isnan(ticker_config_series['Price_Scale_Low'])):
  price_lim_lower = 0
  print("Price_Scale_Low is set to 0")
else:
  price_lim_lower = int(ticker_config_series['Price_Scale_Low'])
  print("Price_Scale_Low from Config file is ", price_lim_lower)

if (math.isnan(ticker_config_series['Price_Scale_High'])):
  ticker_adj_close_list_nonan = [x for x in ticker_adj_close_list if math.isnan(x) is False]
  price_lim_upper = 1.25 * max(ticker_adj_close_list_nonan)
  print("Price_Scale_High from historical ticker_adj_close_list is ", price_lim_upper)
else:
  price_lim_upper = int(ticker_config_series['Price_Scale_High'])
  print("Price_Scale_High from Config file is ", price_lim_upper)
# ---------------------------------------------------------

# ---------------------------------------------------------
# Create the Upper and Lower EPS Limit
# ---------------------------------------------------------
if (math.isnan(ticker_config_series['Earnings Scale - High'])):
  if (max(qtr_eps_list) > 0):
    qtr_eps_lim_upper = 1.25 * max(qtr_eps_list)
  else:
    qtr_eps_lim_upper = max(qtr_eps_list) / 1.25
  print("EPS Scale - Low from Earnings List is ", qtr_eps_lim_upper)
else:
  qtr_eps_lim_upper = ticker_config_series['Earnings Scale - High']
  print("EPS Scale - High from Config file ", qtr_eps_lim_upper)

if (math.isnan(ticker_config_series['Earnings Scale - Low'])):
  if (min(qtr_eps_list) < 0):
    qtr_eps_lim_lower = 1.25 * min(qtr_eps_list)
  else:
    qtr_eps_lim_lower = min(qtr_eps_list) / 1.25
  print("EPS Scale - Low from Earnings List is ", qtr_eps_lim_lower)
else:
  qtr_eps_lim_lower = ticker_config_series['Earnings Scale - Low']
  print("EPS Scale - Low from Config file ", qtr_eps_lim_lower)
# =============================================================================

# =============================================================================
# Find out the growth for 1yr, 3yr and 5yr for eps and price
# Temporarily iffed out
# =============================================================================
# todo :
# Handle negative earning...in the function
# What if there is no 5 years worth of data available?
# Which text box to use...can I put the text_str outside the plot
# Get the text string to format for left justified with enough space
# So I am ifing the block of code out for now...it works but once I do the
# above two todo then can unif the code

get_eps_and_price_growth = 1
price_eps_growth_str_textbox_loc_09 = "This is the box in top center"
if (get_eps_and_price_growth):
  # This works : Get the first non nan value from the list. That is the current price.
  # Can't do a round here - as it round 81.6999 to 81.7 and 81.7 will not match
  # to get us the current date as there is not index that will now match in the
  # adj_close_list
  # ticker_curr_price = round(next(x for x in ticker_adj_close_list if not math.isnan(x)),2)
  ticker_curr_price = next(x for x in ticker_adj_close_list if not math.isnan(x))
  ticker_curr_date = date_list[ticker_adj_close_list.index(ticker_curr_price)]

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
    print ("The match date for yr eps is newer than the current date. Will use yr eps from one quarter ago")
    yr_eps_curr_date = min(yr_eps_date_list, key=lambda d: abs(d - (ticker_curr_date - dt.timedelta(days=60))))

  yr_eps_curr = round(yr_eps_list[yr_eps_date_list.index(yr_eps_curr_date)],2)

  # Get dates 1, 3 and 5 yr ago - based on curr eps date
  ticker_1_yr_ago_date_raw = yr_eps_curr_date - dt.timedelta(days=365)
  ticker_3_yr_ago_date_raw = yr_eps_curr_date - dt.timedelta(days=3*365)
  ticker_5_yr_ago_date_raw = yr_eps_curr_date - dt.timedelta(days=5*365)

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
  ticker_1_yr_ago_price = round(ticker_adj_close_list[date_list.index(ticker_1_yr_ago_date_for_price)],2)
  ticker_3_yr_ago_price = round(ticker_adj_close_list[date_list.index(ticker_3_yr_ago_date_for_price)],2)
  ticker_5_yr_ago_price = round(ticker_adj_close_list[date_list.index(ticker_5_yr_ago_date_for_price)],2)

  yr_eps_1_yr_ago = round(yr_eps_list[yr_eps_date_list.index(ticker_1_yr_ago_date_for_eps)],2)
  yr_eps_3_yr_ago = round(yr_eps_list[yr_eps_date_list.index(ticker_3_yr_ago_date_for_eps)],2)
  yr_eps_5_yr_ago = round(yr_eps_list[yr_eps_date_list.index(ticker_5_yr_ago_date_for_eps)],2)

  print ("The Last     price for ticker is", ticker_curr_price,     "on date", ticker_curr_date,               "with earnings at", yr_eps_curr,     "is at index", date_list.index(ticker_curr_date))
  print ("The 1 Yr ago price for ticker is", ticker_1_yr_ago_price, "on date", ticker_1_yr_ago_date_for_price, "with earnings at", yr_eps_1_yr_ago, "is at index", date_list.index(ticker_1_yr_ago_date_for_price))
  print ("The 3 Yr ago price for ticker is", ticker_3_yr_ago_price, "on date", ticker_3_yr_ago_date_for_price, "with earnings at", yr_eps_3_yr_ago, "is at index", date_list.index(ticker_3_yr_ago_date_for_price))
  print ("The 5 Yr ago price for ticker is", ticker_5_yr_ago_price, "on date", ticker_5_yr_ago_date_for_price, "with earnings at", yr_eps_5_yr_ago, "is at index", date_list.index(ticker_5_yr_ago_date_for_price))

  eps_growth_1_yr = get_growth(yr_eps_curr, yr_eps_1_yr_ago)
  eps_growth_3_yr = get_growth(yr_eps_curr, yr_eps_3_yr_ago)
  eps_growth_5_yr = get_growth(yr_eps_curr, yr_eps_5_yr_ago)

  price_growth_1_yr = get_growth(ticker_curr_price, ticker_1_yr_ago_price)
  price_growth_3_yr = get_growth(ticker_curr_price, ticker_3_yr_ago_price)
  price_growth_5_yr = get_growth(ticker_curr_price, ticker_5_yr_ago_price)

  price_eps_growth_str_textbox_loc_09 = "                               Earnings             Price\n"
  price_eps_growth_str_textbox_loc_09 = price_eps_growth_str_textbox_loc_09 + "Curr" + " - " + str(ticker_curr_date)             + "   " + str(yr_eps_curr)     + "                     " + str(ticker_curr_price) +"              \n"
  price_eps_growth_str_textbox_loc_09 = price_eps_growth_str_textbox_loc_09 + "1 Yr" + " - " + str(ticker_1_yr_ago_date_for_eps) + "   " + str(yr_eps_1_yr_ago) + "(" + str(eps_growth_1_yr) + "%)     " + str(ticker_1_yr_ago_price) +"("+ str(price_growth_1_yr) + "%)\n"
  price_eps_growth_str_textbox_loc_09 = price_eps_growth_str_textbox_loc_09 + "3 Yr" + " - " + str(ticker_3_yr_ago_date_for_eps) + "   " + str(yr_eps_3_yr_ago) + "(" + str(eps_growth_3_yr) + "%)     " + str(ticker_3_yr_ago_price) +"("+ str(price_growth_3_yr) + "%)\n"
  price_eps_growth_str_textbox_loc_09 = price_eps_growth_str_textbox_loc_09 + "5 Yr" + " - " + str(ticker_5_yr_ago_date_for_eps) + "   " + str(yr_eps_5_yr_ago) + "(" + str(eps_growth_5_yr) + "%)     " + str(ticker_5_yr_ago_price) +"("+ str(price_growth_5_yr) + "%)"
  print (price_eps_growth_str_textbox_loc_09)

# =============================================================================


# =============================================================================
# Get the company info for company name, sector and industry
# =============================================================================
yahoo_comany_info_df = pd.read_excel(dir_path + user_dir + "\\" + 'Yahoo_Company_Info.xlsm', sheet_name="Company_Info")
yahoo_comany_info_df.set_index('Ticker', inplace=True)
# print (yahoo_comany_info_df)
ticker_company_name = "#NA#"
ticker_sector = "#NA#"
ticker_industry = "#NA#"
if (yahoo_comany_info_df.index.isin([(ticker)]).any()):
  # This works - get the value in the column corresponding to the index
  ticker_company_name = yahoo_comany_info_df.loc[ticker, 'Company_Name']
  ticker_sector = yahoo_comany_info_df.loc[ticker, 'Sector']
  ticker_industry = yahoo_comany_info_df.loc[ticker, 'Industry']
print (ticker_company_name, ticker_sector, ticker_industry)
# =============================================================================

# =============================================================================
# Extract and generate information needed for candlesticks and volume chart
# =============================================================================
if (math.isnan(ticker_config_series['Candle_Chart_Duration_Days'])):
  candle_chart_duration = 50
else:
  candle_chart_duration = int(ticker_config_series['Candle_Chart_Duration_Days'])

historical_columns_list = list(historical_df)
print ("The columns in Historical Dataframe ", historical_columns_list)
# Get the candlestick_df from historical_df - candlesticks_df has all the data
# past the first date when the prices are available.
candlestick_df = historical_df.loc[ticker_adj_close_list.index(ticker_curr_price):]
candlestick_df.columns =  historical_columns_list
print ("Candlestick Dataframe is ",candlestick_df)

date_str_list_candles = candlestick_df.Date.tolist()
# Change the Date to mdates - This gives out warning - todo : Take care of the warning.
candlestick_df['Date'] = [mdates.date2num(dt.datetime.strptime(d, '%m/%d/%Y').date()) for d in date_str_list_candles]
print ("Candlestick Dataframe after chanings the Dates to mdates is ",candlestick_df)
MA_Price_200_list = candlestick_df.MA_Price_200_day.tolist()
MA_Price_50_list = candlestick_df.MA_Price_50_day.tolist()
MA_Price_20_list = candlestick_df.MA_Price_20_day.tolist()
MA_Price_10_list = candlestick_df.MA_Price_10_day.tolist()
MA_volume_50_list = candlestick_df.MA_Volume_50_day.tolist()

# Canclesticks likes to put everything in tuple before plotting
quotes = [tuple(x) for x in candlestick_df[['Date', 'Open', 'High', 'Low', 'Close']].values]
date_list_candles = candlestick_df.Date.tolist()
volume = candlestick_df.Volume.tolist()
print ("The type of quotes is",quotes)
print ("The type of volume is",volume)

# Set the bar color for volume by comparing the open and close prices
price_open_list = candlestick_df.Open.tolist()
price_close_list = candlestick_df.Close.tolist()
bar_color_list = ['r'] * len(price_close_list)
for i_idx in range(len(price_close_list)):
  bar_color_list[i_idx] = 'r'
  if (price_close_list[i_idx] > price_open_list[i_idx]):
    bar_color_list[i_idx] = 'g'

print ("The bar color list is ",bar_color_list)

# ---------------------------------------------------------
# Set the ticks and the ticklabels for y-axis for volume
# ---------------------------------------------------------
ticker_volume_max = max(volume[0:candle_chart_duration])
ticker_volume_max_no_of_digits = len(str(abs(int(ticker_volume_max))))
ticker_volume_max_first_digit = int(str(ticker_volume_max)[:1])
print ("The max volume is", ticker_volume_max, "and the number of digits are", ticker_volume_max_no_of_digits, "and the first digit is", ticker_volume_max_first_digit)
if (ticker_volume_max_first_digit == 1):
  ticker_volume_upper_limit = 2 * math.pow(10,ticker_volume_max_no_of_digits-1)
elif (ticker_volume_max_first_digit == 2):
  ticker_volume_upper_limit = 4 * math.pow(10,ticker_volume_max_no_of_digits-1)
elif (2 < ticker_volume_max_first_digit <= 4):
  ticker_volume_upper_limit = 5 * math.pow(10, ticker_volume_max_no_of_digits - 1)
elif (5 < ticker_volume_max_first_digit <= 7):
  ticker_volume_upper_limit = 8 * math.pow(10, ticker_volume_max_no_of_digits - 1)
else:
  ticker_volume_upper_limit = 10 * math.pow(10,ticker_volume_max_no_of_digits-1)

print ("The upper limit for volume is", ticker_volume_upper_limit)
ticker_volume_ytick_list = []
ticker_volume_yticklabels_list = []
for i_idx in range(0,5,1):
  ticker_volume_ytick_list.append(i_idx*(ticker_volume_upper_limit/4))
  ticker_volume_yticklabels_list.append(human_format(ticker_volume_ytick_list[i_idx],precision=0))
  print("Index", i_idx, "Tick Label", ticker_volume_ytick_list[i_idx], "Tick label Text", ticker_volume_yticklabels_list[i_idx])

# Get the Sundays in the date range to act as grid in the candle and volume plots
candle_sunday_dates = pd.date_range(date_str_list_candles[candle_chart_duration], date_str_list_candles[0], freq='W-SUN')
print ("The Sunday dates are", candle_sunday_dates)

candle_sunday_dates_str = []
for x in candle_sunday_dates:
  print("The original Sunday Date is :", x)
  candle_sunday_dates_str.append(x.date().strftime('%m/%d/%Y'))

print ("The modified Sunday dates are", candle_sunday_dates_str)
# =============================================================================


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
chart_type = 'linear'
# fig, main_plt = plt.subplots()

fig=plt.figure()
main_plt = plt.subplot2grid((5,5), (0,0), colspan=4,rowspan=5)
candle_plt = plt.subplot2grid((5,5), (0,4), colspan=1,rowspan=4)
volume_plt = plt.subplot2grid((5,5), (4,4), colspan=1,rowspan=1)
plt.subplots_adjust(hspace=0,wspace=0)



fig.set_size_inches(16, 10)  # Length x height
fig.subplots_adjust(right=0.90)
# fig.autofmt_xdate()
# This works - Named colors in matplotlib
# https://stackoverflow.com/questions/22408237/named-colors-in-matplotlib
main_plt.set_facecolor("lightgrey")
candle_plt.set_facecolor("mistyrose")
volume_plt.set_facecolor("honeydew")

plt.text(x=0.11, y=0.91, s=ticker_company_name + "("  +ticker +")", fontsize=18,fontweight='bold',ha="left", transform=fig.transFigure)
plt.text(x=0.11, y=0.89, s=ticker_sector + " - " + ticker_industry , fontsize=10, fontweight='bold',fontstyle='italic',ha="left", transform=fig.transFigure)
# fig.suptitle(r'{\fontsize{30pt}{3em}\selectfont{}{Mean WRFv3.5 LHF\n}{\fontsize{18pt}{3em}\selectfont{}(September 16 - October 30, 2012)}')
# fig.suptitle(ticker_company_name + "("  +ticker +")" + "\n" + ticker_sector + "  " + ticker_industry, fontsize=18,x=0.22,y=.95)
# This works too...may use that is set the subtitle for the plot
# main_plt.set_title(ticker_company_name + "("  +ticker +")", fontsize=18,horizontalalignment='right')





# Various plots that share the same x axis(date)
price_plt = main_plt.twinx()
if (plot_spy):
  spy_plt = main_plt.twinx()
annual_past_eps_plt = main_plt.twinx()
annual_projected_eps_plt = main_plt.twinx()
upper_channel_plt = main_plt.twinx()
lower_channel_plt = main_plt.twinx()
# yr_eps_02_5_plt = main_plt.twinx()
# yr_eps_05_0_plt = main_plt.twinx()
# yr_eps_10_0_plt = main_plt.twinx()
# yr_eps_20_0_plt = main_plt.twinx()
# yr_eps_02_5_plt[0] = main_plt.twinx()

if (pays_dividend == 1):
  dividend_plt = main_plt.twinx()

print("Type of fig ", type(fig), \
      "\nType of main_plt ", type(main_plt), \
      "\nType of price_plt: ", type(price_plt), \
      "\nType of yr_eps_plt: ", type(annual_past_eps_plt), \
      "\nType of upper_channel_plt: ", type(upper_channel_plt))
# -----------------------------------------------------------------------------
# Main Plot - This is the Q EPS vs Date
# -----------------------------------------------------------------------------
# This works - I have commented out so that the code does not print out the xlate
# and I can get more space below the date ticks
# main_plt.set_xlabel('Date')
main_plt.set_ylabel('Earnings')
main_plt.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
main_plt_inst = main_plt.plot(date_list[0:plot_period_int], qtr_eps_expanded_list[0:plot_period_int], label='Q EPS',
                              color="deeppink", marker='.')
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Historical Price Plot
# -----------------------------------------------------------------------------
# Now printing price on the right side of the candle plot
# price_plt.set_ylabel('Price', color='k')
# This works - this will move the tick labels inside the plot
price_plt.tick_params(axis="y",direction="in", pad=-22)
price_plt.set_ylim(price_lim_lower, price_lim_upper)
price_plt.set_yscale(chart_type)
price_plt_inst = price_plt.plot(date_list[0:plot_period_int], ticker_adj_close_list[0:plot_period_int],
                                label='Adj Close', color="brown", linestyle='-')
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Index Price Plot
# -----------------------------------------------------------------------------
if (plot_spy):
  spy_plt.set_ylim(price_lim_lower, price_lim_upper)
  spy_plt_inst = spy_plt.plot(date_list[0:plot_period_int], spy_adj_close_list[0:plot_period_int], label='S&P',
                              color="green", linestyle='-')
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Average Annual EPS Plot
# -----------------------------------------------------------------------------
# Find the eps points that fall in the plot range
annual_past_eps_plt.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
annual_past_eps_plt.set_yticks([])
annual_past_eps_plt_inst = annual_past_eps_plt.plot(date_list[0:plot_period_int],
                                                    annual_past_eps_expanded_list[0:plot_period_int], label='4 qtrs/4',
                                                    color="black", marker='D', markersize='4')
# todo : maybe change this to only have the value printed out at the year ends
for i in range(len(yr_eps_date_list)):
  print("The Date is ", yr_eps_date_list[i], " Corresponding EPS ", yr_eps_list[i])
  # check if the date is in the plot range
  if (date_list[plot_period_int] <= yr_eps_date_list[i] <= date_list[0]):
    x = float("{0:.2f}".format(yr_eps_list[i]))
    main_plt.text(yr_eps_date_list[i], yr_eps_list[i], x, fontsize=11, horizontalalignment='center',
                  verticalalignment='bottom')
    # main_plt.text(yr_eps_date_list[i],yr_eps_list[i],x, bbox={'facecolor':'white'})

annual_projected_eps_plt.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
annual_projected_eps_plt.set_yticks([])
annual_projected_eps_plt_inst = annual_projected_eps_plt.plot(date_list[0:plot_period_int],
                                                              annual_projected_eps_expanded_list[0:plot_period_int],
                                                              label='4 qtrs/4', color="White", marker='D',
                                                              markersize='4')
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Dividend plot
# -----------------------------------------------------------------------------
if (pays_dividend == 1):
  dividend_plt.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
  dividend_plt.set_yticks([])
  dividend_plt_inst = dividend_plt.plot(date_list[0:plot_period_int], dividend_expanded_list[0:plot_period_int],
                                        label='Dividend', color="Orange", marker='x', markersize='6')
  for i in range(len(dividend_date_list)):
    if (date_list[plot_period_int] <= dividend_date_list[i] <= date_list[0]):
      x = float("{0:.2f}".format(dividend_list[i]))
      main_plt.text(dividend_date_list[i], dividend_list_multiplied[i], x, fontsize=6, horizontalalignment='center',
                    verticalalignment='bottom')
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
# Upper Price Channel Plot
# -----------------------------------------------------------------------------
# upper_channel_plt.set_ylabel('Upper_guide', color = 'b')
# upper_channel_plt.spines["right"].set_position(("axes", 1.2))
upper_channel_plt.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
upper_channel_plt.set_yticks([])
upper_channel_plt_inst = upper_channel_plt.plot(date_list[0:plot_period_int],
                                                upper_price_channel_list[0:plot_period_int], label='Channel', color="blue",
                                                linestyle='-')
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Lower Price Channel Plot
# -----------------------------------------------------------------------------
# upper_channel_plt.set_ylabel('Upper_guide', color = 'b')
# upper_channel_plt.spines["right"].set_position(("axes", 1.2))
lower_channel_plt.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
lower_channel_plt.set_yticks([])
lower_channel_plt_inst = lower_channel_plt.plot(date_list[0:plot_period_int],
                                                lower_price_channel_list[0:plot_period_int], label='Price Channel', color="blue",
                                                linestyle='-')
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Candlestick and volume Plots
# -----------------------------------------------------------------------------
# todo
# Figure out how to adjust the candlestick price y ranges
# Google search - remove weekends from matplotlib plot
candle_plt_inst = candlestick_ohlc(candle_plt, quotes[0:candle_chart_duration], width=1, colorup='g', colordown='r');
candle_plt_MA200_inst = candle_plt.plot(date_list_candles[0:candle_chart_duration],MA_Price_200_list[0:candle_chart_duration],linewidth=.5, color = 'black', label = 'SMA200')
candle_plt_MA50_inst = candle_plt.plot(date_list_candles[0:candle_chart_duration],MA_Price_50_list[0:candle_chart_duration], linewidth=.5,color = 'blue', label = 'SMA50')
candle_plt_MA20_inst = candle_plt.plot(date_list_candles[0:candle_chart_duration],MA_Price_20_list[0:candle_chart_duration],linewidth=.5, color = 'green', label = 'SMA20')
candle_plt_MA10_inst = candle_plt.plot(date_list_candles[0:candle_chart_duration],MA_Price_10_list[0:candle_chart_duration],linewidth=.5, color = 'deeppink', label = 'SMA10')
volume_plt_inst = volume_plt.bar(date_list_candles[0:candle_chart_duration], volume[0:candle_chart_duration], width=1, color=bar_color_list[0:candle_chart_duration])
volume_plt_MA = volume_plt.twinx()
volume_plt_MA_inst = volume_plt_MA.plot(date_list_candles[0:candle_chart_duration],MA_volume_50_list[0:candle_chart_duration], color = 'blue', label = 'SMA10')
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
# This works - Good resource
# https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.date_range.html
# https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#timeseries-offset-aliases
yr_dates = pd.date_range(date_list[plot_period_int], date_list[0], freq='Y')
qtr_dates = pd.date_range(date_list[plot_period_int], date_list[0], freq='Q')
print("Yearly Dates are ", yr_dates)
print("Quarterly Dates are ", type(qtr_dates))

qtr_dates_tmp = []
yr_dates_tmp = []
for x in qtr_dates:
  print("The original Quarterly Date is :", x)
  if (x.is_year_end is True):
    print("This quarter is also year end date. Removing ", type(x))
  if (x in yr_dates):
    print("This quarter is also year end date. Removing ", type(x))
  else:
    qtr_dates_tmp.append(x.date().strftime('%m/%d/%Y'))

for x in yr_dates:
  print("The original Yearly Date is :", x)
  yr_dates_tmp.append(x.date().strftime('%m/%d/%Y'))

print("The modified qtr dates list is: ", qtr_dates)
print("The modified qtr dates list is: ", qtr_dates_tmp)
print("The modified yr dates list is: ", yr_dates_tmp)

main_plt.set_xticks(yr_dates_tmp, minor=False)
main_plt.set_xticks(qtr_dates_tmp, minor=True)
main_plt.xaxis.set_tick_params(width=5)
main_plt.set_xticklabels(yr_dates_tmp, rotation=90, fontsize=8, color='blue', minor=False, fontstyle='italic')
main_plt.set_xticklabels(qtr_dates_tmp, rotation=90, fontsize=7, minor=True)
main_plt.grid(which='major', axis='x', linestyle='-', color='black', linewidth=1.5)
main_plt.grid(which='minor', linestyle='--', color='blue')
main_plt.grid(which='major', axis='y', linestyle='--', color='green', linewidth=1)

# candle_plt.set_xticks([])
candle_plt.set_xticks(candle_sunday_dates, minor=False)
candle_plt.grid(True)
candle_plt.grid(True,axis='x',which='major', linestyle='--', color='lightgray')
# This works - To turn individual grid axis off or on
# candle_plt.grid(False,axis='y')
candle_plt.set_ylabel('Price', color='k')
candle_plt.yaxis.set_label_position("right")
candle_plt.yaxis.tick_right()

volume_plt.set_xticks(candle_sunday_dates, minor=False)
volume_plt.grid(True)
volume_plt.grid(True,axis='x',which='major', linestyle='--', color='lightgray')
volume_plt.set_xticklabels(candle_sunday_dates_str,rotation=90, fontsize=8, color='blue', minor=False, fontstyle='italic')
volume_plt.set_ylim(0, ticker_volume_upper_limit)
volume_plt.yaxis.tick_right()
volume_plt.set_yticks(ticker_volume_ytick_list)
volume_plt.set_yticklabels(ticker_volume_yticklabels_list, rotation=0, fontsize=8, color='k', minor=False)

volume_plt_MA.set_ylim(0, ticker_volume_upper_limit)
# volume_plt_MA.set_xticks([])
volume_plt_MA.set_yticks([])
volume_plt_MA.text(date_list_candles[0], MA_volume_50_list[0], human_format(MA_volume_50_list[0]),
                   fontsize=7,color='blue',fontweight='bold',
                   bbox=dict(facecolor='lavender', edgecolor='k', pad=2.0,alpha=1))
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
# todo : Can this be done in an array
number_of_anchored_texts = 4
for i in range(number_of_anchored_texts):
  if (i == 0):
    location = 9
    my_text = price_eps_growth_str_textbox_loc_09
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
  print("json data for ", ticker, "does not exist in", configuration_json, "file")
else:
  if ("Plot_Annotate" in config_json[ticker]):
    print("The number of plot annotates requested by the user are", len(config_json[ticker]["Plot_Annotate"]))
    for i_idx in range(len(config_json[ticker]["Plot_Annotate"])):
      date_to_annotate = config_json[ticker]["Plot_Annotate"][i_idx]["Date"]
      date_to_annotate_datetime = dt.datetime.strptime(date_to_annotate, '%m/%d/%Y').date()
      annotate_text = config_json[ticker]["Plot_Annotate"][i_idx]["Text"]
      (x_coord,y_coord) =  config_json[ticker]["Plot_Annotate"][i_idx]["Line_Length"].split(":")

      match_date = min(date_list, key=lambda d: abs(d - date_to_annotate_datetime))
      print("The matching date is ", match_date, " at index ", date_list.index(match_date), " and the price is ",
            ticker_adj_close_list[date_list.index(match_date)])
      price_plt.annotate(annotate_text,
                         xy=(date_list[date_list.index(match_date)], ticker_adj_close_list[date_list.index(match_date)]),
                         xytext=(int(x_coord), int(y_coord)), textcoords='offset points', arrowprops=dict(facecolor='black', width=.25),
                         bbox=dict(facecolor='none', edgecolor='black', boxstyle='round,pad=1'))
                         # arrowprops=dict(facecolor='black', width=1))

# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Save the Chart with the date and time as prefix
# -----------------------------------------------------------------------------
# This works too instead of two line
# date_time =  dt.datetime.now().strftime("%Y_%m_%d_%H_%M")
now = dt.datetime.now()
date_time = now.strftime("%Y_%m_%d_%H_%M")
fig.savefig(chart_dir + "\\" + ticker + "_" + date_time + ".jpg", dpi=200)
plt.show()
# -----------------------------------------------------------------------------
