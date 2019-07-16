import pandas as pd
import matplotlib
import os
import math
import json
import sys
import datetime as dt
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.offsetbox import AnchoredText
from SC_logger import my_print as my_print

from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()
# =============================================================================
# User defined function
# This function takes in a list that has nan in between numeric values and
# replaces the nan in the middle with a step so that the 'markers' can be
#  converted to a line while plotting
# # =============================================================================
def smooth_list (l):

  i_int = 0
  l_mod = l.copy()
  l_clean = []
  l_indices = []

  while (i_int < len(l) - 1):
    if (str(l_mod[i_int]) != 'nan'):
      l_clean.append(l[i_int])
      l_indices.append(i_int)

    i_int += 1

  print ("The original List is ", l)
  print("The clean List is ", l_clean)
  print("The indices of non non values is ", l_indices)

  i_int = 0
  while (i_int < len(l_clean) - 1):
    print("Clean List index:", i_int, ", Clean List value:", l_clean[i_int], ", Corresponding List index:", l_indices[i_int])
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
earnings_dir= "\\..\\" + "Earnings"
dividend_dir= "\\..\\" + "Dividend"
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
ticker = "WIRE"

# Open the Log file in write mode
logfile = dir_path + log_dir + "\\" + ticker + "_log.txt"
debug_fh = open(logfile, "w+")

# =============================================================================
# Read the Earnings file for the ticker
# =============================================================================
qtr_eps_df = pd.read_csv(dir_path + "\\" + earnings_dir + "\\" + ticker + "_earnings.csv")
log_lvl = "error"
debug_str = "The Earnings df is \n" + qtr_eps_df.to_string()
stdout = 0; my_print (debug_fh,debug_str,stdout,log_lvl.upper())

# print ("The Earnings df is \n", qtr_eps_df)
# todo : Error out if any elements in the date_list are nan except the trailing (this includes
# todo : leading nan and any nan in the list itself
qtr_eps_date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in qtr_eps_df.Date.dropna().tolist()]
qtr_eps_list = qtr_eps_df.Q_EPS_Diluted.tolist()
print ("The date list for qtr_eps is ", qtr_eps_date_list, "\nand the number of elements are", len(qtr_eps_date_list))
print ("The Earnings list for qtr_eps is ", qtr_eps_list)

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
  print ("The date list for Dividends is ", dividend_date_list, "\nand the number of elements are", len(dividend_date_list))
  print ("The Amounts for dividends is ", dividend_list)
# =============================================================================


# =============================================================================
# Handle splits before proceeding as splits can change the qtr_eps
# =============================================================================
# todo : Test out various cases of splits so that the code is robust
split_dates = list()
split_multiplier = list()
print ("Tickers in json data: ",config_json.keys())
if (ticker not in config_json.keys()):
  print ("json data for ",ticker, "does not exist in",configuration_json, "file")
else :
  if ("Splits" in config_json[ticker]):
    # if the length of the keys is > 0
    if (len(config_json[ticker]["Splits"].keys()) > 0 ):
      split_keys = config_json[ticker]["Splits"].keys()
      print ("Split Date list is: ", split_keys)
      for i_key in split_keys:
        print ("Split Date :", i_key, "Split Factor :", config_json[ticker]["Splits"][i_key])
        try:
         split_dates.append(dt.datetime.strptime(str(i_key),"%m/%d/%Y").date())
        except (ValueError):
         print ("\n***** Error : The split Date: ",i_key,"does not seem to be right. Should be in the format %m/%d/%Y...please check *****")
         sys.exit(1)
        try:
          (numerator, denominator) = config_json[ticker]["Splits"][i_key].split(":")
          split_multiplier.append(float(denominator)/float(numerator))
        except (ValueError):
          print ("\n***** Error : The split factor: ",config_json[ticker]["Splits"][i_key],"for split date :", i_key , "does not seem to have right format [x:y]...please check *****")
          sys.exit(1)
      for i in range(len(split_dates)):
        qtr_eps_list_mod = qtr_eps_list.copy()
        print("Split Date :", split_dates[i], " Multiplier : ", split_multiplier[i])
        for j in range(len(qtr_eps_date_list)):
          if (split_dates[i] > qtr_eps_date_list[j]):
            qtr_eps_list_mod[j] = round(qtr_eps_list[j] * split_multiplier[i], 4)
            print("Earnings date ", qtr_eps_date_list[j], " is older than split date. Changed ", qtr_eps_list[j], " to ",
                  qtr_eps_list_mod[j])
        qtr_eps_list = qtr_eps_list_mod.copy()
    else:
      print("\"Splits\" exits but seems empty for ", ticker)
  else:
    print ("\"Splits\" does not exist for ", ticker)
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
print ("The Earnings list for qtr_eps is ", qtr_eps_list)

# Check if now the qtr_eps_list still has any undefined elements...flag an error and exit
# This will indicate any empty cells are either the beginning or in the middle of the eps
# column in the csv
if (sum(math.isnan(x) for x in qtr_eps_list) > 0):
  print ("ERROR : There are some undefined EPS numbers in the Earnings file, Please correct and rerun")
  exit()
# ============================================================================

# So - if we are successful till this point - we have made sure that
# 1. There are no nan in the date list
# 2. There are no nan in the eps list
# 3. Number of elements in the qtr_eps_date_list are equal to the number of
#    element in the qtr_eps_list
# =============================================================================
# Todo : Reading and plotting the index should be inside a if statement
# Read the spy or dji or ixic file for comparison
spy_df = pd.read_csv(dir_path + "\\" + historical_dir + "\\" + "^GSPC_historical.csv")
dji_df = pd.read_csv(dir_path + "\\" + historical_dir + "\\" + "^DJI_historical.csv")
nasdaq_df = pd.read_csv(dir_path + "\\" + historical_dir + "\\" + "^IXIC_historical.csv")



# =============================================================================
# Read the Historical file for the ticker
# =============================================================================
historical_df = pd.read_csv(dir_path + "\\" + historical_dir + "\\" + ticker + "_historical.csv")
print ("The Historical df is \n", historical_df)
ticker_adj_close_list = historical_df.Adj_Close.tolist()
date_str_list = historical_df.Date.tolist()
print ("The date list from historical df is ", date_str_list)
date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in date_str_list]
print ("The date list for historical is ", date_list, "\nit has ", len(date_list), " entries")
# =============================================================================

# ===================================================================================================
# Create the Annual EPS list from the Quarter EPS list.
# The last 3 elemnts of the annual EPS are going to be blank because the last annual EPS corresponds
# the the last but 4th Quarter EPS
# ===================================================================================================
i_int = 0
yr_eps_list = list()
while (i_int < (len(qtr_eps_list)-3)):
  annual_average_eps = (qtr_eps_list[i_int] +     \
                        qtr_eps_list[i_int + 1] + \
                        qtr_eps_list[i_int + 2] + \
                        qtr_eps_list[i_int + 3])/4

  print ("Iteration #, ", i_int, " Quartely EPS, Annual EPS", \
                                                  qtr_eps_list[i_int], \
                                                  qtr_eps_list[i_int+1],\
                                                  qtr_eps_list[i_int+2],\
                                                  qtr_eps_list[i_int+3], \
                                                  annual_average_eps)
  yr_eps_list.append(annual_average_eps)
  i_int += 1
print ("Annual EPS List ", yr_eps_list, "\nand the number of elements are", len(yr_eps_list))

# I am not sure why I wanted this but seems like a good thing to be able to make
# a dataframe from lists. This is not used anywhere in the code ahead...so commented
# out for now
# yr_eps_list_tmp = yr_eps_list
# yr_eps_list_tmp.append('Not_calculated')
# yr_eps_list_tmp.append('Not_calculated')
# yr_eps_list_tmp.append('Not_calculated')
# earnings_df = pd.DataFrame(np.column_stack([qtr_eps_date_list, qtr_eps_list, yr_eps_list_tmp]),
#                                columns=['Date', 'Q EPS', 'Annual EPS'])
# print ("The Earnings DF is ", earnings_df)
# ===================================================================================================


# =============================================================================
# Create a qtr_eps_expanded and dividend_expanded list
# We are here trying to create the list that has the same number of elements
# as the historical date_list and only the elements that have the Quarter EPS
# have valid values, other values in the expanded list are nan..so the
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
  print ("Looking for ", qtr_eps_date)
  match_date = min(date_list, key=lambda d: abs(d - qtr_eps_date))
  print ("The matching date for QTR EPS Date: ",qtr_eps_date, "is ", match_date, " at index ",date_list.index(match_date))
  qtr_eps_expanded_list[date_list.index(match_date)] = qtr_eps_list[curr_index]

print ("The expanded qtr eps list is ", qtr_eps_expanded_list, "\nand the number of elements are", len(qtr_eps_expanded_list))

if (pays_dividend == 1):
  for dividend_date in dividend_date_list:
    curr_index = dividend_date_list.index(dividend_date)
    print ("Looking for ", dividend_date)
    match_date = min(date_list, key=lambda d: abs(d - dividend_date))
    print ("The matching date for QTR EPS Date: ",dividend_date, "is ", match_date, " at index ",date_list.index(match_date))
    dividend_expanded_list[date_list.index(match_date)] = dividend_list[curr_index]

  print ("The expanded Dividend list is ", dividend_expanded_list, "\nand the number of elements are", len(dividend_expanded_list))
# =============================================================================

# =============================================================================
# Create annual eps date list and then create
# Expanded annual EPS list just like the expanded Quarter EPS list was created
# However the expanded Annual EPS list is really three lists...to create a different
# series in the plot/graph later
# yr_eps_expanded_list
# annual_past_eps_expanded_list - contains only the yr eps that is older than the
#   current date - This will end up as black diamonds in the chart
# annual_projected_eps_expanded_list - contains only the yr epx that is newer
#   than the current date - This will end up as white diamonds in the chart
# =============================================================================
# Remove the last 3 dates from the qtr_eps_date_list to create yr_eps_date_list
yr_eps_date_list = qtr_eps_date_list[0:len(qtr_eps_date_list)-3]

yr_eps_expanded_list = []
annual_past_eps_expanded_list = []
annual_projected_eps_expanded_list = []
for i in range(len(date_list)):
  yr_eps_expanded_list.append(float('nan'))
  annual_past_eps_expanded_list.append(float('nan'))
  annual_projected_eps_expanded_list.append(float('nan'))

for yr_eps_date in yr_eps_date_list:
  curr_index = yr_eps_date_list.index(yr_eps_date)
  print ("Looking for ", yr_eps_date)
  match_date = min(date_list, key=lambda d: abs(d - yr_eps_date))
  print ("The matching date is ", match_date, " at index ",date_list.index(match_date))
  yr_eps_expanded_list[date_list.index(match_date)] = yr_eps_list[curr_index]
  # Check if the matching data is in the past or in the future
  if (match_date < dt.date.today()):
    print ("The matching date is in the past")
    annual_past_eps_expanded_list[date_list.index(match_date)] = yr_eps_list[curr_index]
  else:
    print ("The matching date is in the future")
    annual_projected_eps_expanded_list[date_list.index(match_date)] = yr_eps_list[curr_index]
print ("The Expanded Annual EPS List is: ", yr_eps_expanded_list)
# =============================================================================

number_of_growth_proj = 0
start_date_for_yr_eps_growth_proj_list = []
stop_date_for_yr_eps_growth_proj_list = []
if (ticker not in config_json.keys()):
  print ("json data for ",ticker, "does not exist in",configuration_json, "file")
else :
  if ("Earnings_Projection_Lines" in config_json[ticker]):
    number_of_growth_proj = len(config_json[ticker]["Earnings_Projection_Lines"])
    for i in range(number_of_growth_proj):
      i_start_date = config_json[ticker]["Earnings_Projection_Lines"][i]["Start_Date"]
      i_stop_date = config_json[ticker]["Earnings_Projection_Lines"][i]["Stop_Date"]
      try:
        start_date_for_yr_eps_growth_proj_list.append(dt.datetime.strptime(i_start_date, "%m/%d/%Y").date())
        stop_date_for_yr_eps_growth_proj_list.append(dt.datetime.strptime(i_stop_date, "%m/%d/%Y").date())
      except (ValueError):
        print("\n***** Error : Either the Start/Stop Dates for Growth projection lines are not in proper format for in Configuration json file.\n"
              "***** Error : The Start_Date should be in the format %m/%d/%Y and the Stop_Date should be in the format: %m/%d/%Y or Next or Last\n"
              "***** Error : Found somewhere in :", i_start_date, i_stop_date)
        sys.exit(1)

yr_eps_02_5_growth_expanded_list =  [[] for _ in range(number_of_growth_proj)]
yr_eps_05_0_growth_expanded_list =  [[] for _ in range(number_of_growth_proj)]
yr_eps_10_0_growth_expanded_list =  [[] for _ in range(number_of_growth_proj)]
yr_eps_20_0_growth_expanded_list =  [[] for _ in range(number_of_growth_proj)]

for i_idx in range(number_of_growth_proj):
  start_date_for_yr_eps_growth_proj = start_date_for_yr_eps_growth_proj_list[i_idx]
  stop_date_for_yr_eps_growth_proj =stop_date_for_yr_eps_growth_proj_list[i_idx]

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

  # The first entry for the list comes from the yr_eps_list
  yr_eps_02_5_growth_list[growth_proj_start_index] = yr_eps_list[growth_proj_start_index]
  yr_eps_05_0_growth_list[growth_proj_start_index] = yr_eps_list[growth_proj_start_index]
  yr_eps_10_0_growth_list[growth_proj_start_index] = yr_eps_list[growth_proj_start_index]
  yr_eps_20_0_growth_list[growth_proj_start_index] = yr_eps_list[growth_proj_start_index]

  # Then grow the growth list from the start point to the end point by multiplying
  # with the grwoth factor
  for i in reversed(range(growth_proj_stop_index, growth_proj_start_index)):
    print ("Updating for index", i)
    yr_eps_02_5_growth_list[i] = 1.025*float(yr_eps_02_5_growth_list[i+1])
    yr_eps_05_0_growth_list[i] = 1.05*float(yr_eps_05_0_growth_list[i+1])
    yr_eps_10_0_growth_list[i] = 1.10*float(yr_eps_10_0_growth_list[i+1])
    yr_eps_20_0_growth_list[i] = 1.20*float(yr_eps_20_0_growth_list[i+1])

  print ("The Annual eps list", yr_eps_list)
  print ("The 2.5% growth rate eps list", yr_eps_02_5_growth_list)
  print ("The   5% growth rate eps list", yr_eps_05_0_growth_list)
  print ("The  10% growth rate eps list", yr_eps_10_0_growth_list)
  print ("The  20% growth rate eps list", yr_eps_20_0_growth_list)

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
    print ("Looking for ", yr_eps_date)
    match_date = min(date_list, key=lambda d: abs(d - yr_eps_date))
    print ("The matching date is ", match_date, " at index ",date_list.index(match_date))
    yr_eps_02_5_growth_expanded_list_unsmooth[date_list.index(match_date)] = yr_eps_02_5_growth_list[curr_index]
    yr_eps_05_0_growth_expanded_list_unsmooth[date_list.index(match_date)] = yr_eps_05_0_growth_list[curr_index]
    yr_eps_10_0_growth_expanded_list_unsmooth[date_list.index(match_date)] = yr_eps_10_0_growth_list[curr_index]
    yr_eps_20_0_growth_expanded_list_unsmooth[date_list.index(match_date)] = yr_eps_20_0_growth_list[curr_index]

  yr_eps_02_5_growth_expanded_list[i_idx] = smooth_list(yr_eps_02_5_growth_expanded_list_unsmooth)
  yr_eps_05_0_growth_expanded_list[i_idx] = smooth_list(yr_eps_05_0_growth_expanded_list_unsmooth)
  yr_eps_10_0_growth_expanded_list[i_idx] = smooth_list(yr_eps_10_0_growth_expanded_list_unsmooth)
  yr_eps_20_0_growth_expanded_list[i_idx] = smooth_list(yr_eps_20_0_growth_expanded_list_unsmooth)




# =============================================================================
# Read the config file and decide all the parms that are needed for plot
# =============================================================================
config_df.set_index('Ticker', inplace=True)
print ("The configuration df", config_df)
if ticker in config_df.index:
  ticker_config_series = config_df.loc[ticker]
  print("Then configurations for ", ticker, " is ", ticker_config_series)
else:
  # Todo : Create a default series with all nan so that it can be cleaned up in the next step
  print("Configuration Entry for ", ticker, " not found...continuing with default values")

# ---------------------------------------------------------
# Find out how many years need to be plotted
# ---------------------------------------------------------
# todo : what if someone puts a string like "Max" in there?
# Maybe support a date there?
if (math.isnan(ticker_config_series['Linear Chart Years'])):
  plot_period_int = 252 * 10
  print("Will Plot the Chart for 10 years")
else:
  print("Will Plot the Chart for ", int(ticker_config_series['Linear Chart Years']), " years")
  plot_period_int = 252*int(ticker_config_series['Linear Chart Years'])
# ---------------------------------------------------------


# Get the index factor
# Get the spy for the plot_period_int and then normalize it
# to stock price from that date onwards
spy_adj_close_list = spy_df.Adj_Close.tolist()
# find the length of adk_close_list
if (len(ticker_adj_close_list) < plot_period_int):
  spy_adjust_factor = spy_adj_close_list[len(ticker_adj_close_list)]/ticker_adj_close_list[len(ticker_adj_close_list)]
else:
  spy_adjust_factor = spy_adj_close_list[plot_period_int]/ticker_adj_close_list[plot_period_int]

spy_adj_close_list[:] = [x / spy_adjust_factor for x in spy_adj_close_list]

# ---------------------------------------------------------
# Get the upper and lower guide lines separation from the annual EPS
# ---------------------------------------------------------
# todo : what if the eps is negative then the multiplication makes it more negative
if (math.isnan(ticker_config_series['Upper Price Channel'])):
  upper_price_channel_list_unsmooth = [float(eps)+ .5*float(eps) for eps in yr_eps_expanded_list]
else:
  upper_price_channel_separation = float(ticker_config_series['Upper Price Channel'])
  upper_price_channel_list_unsmooth = [float(eps)+ upper_price_channel_separation for eps in yr_eps_expanded_list]

if (math.isnan(ticker_config_series['Lower Price Channel'])):
  lower_price_channel_list_unsmooth = [float(eps) - .5*float(eps) for eps in yr_eps_expanded_list]
else:
  lower_price_channel_separation = float(ticker_config_series['Lower Price Channel'])
  lower_price_channel_list_unsmooth = [float(eps)- lower_price_channel_separation for eps in yr_eps_expanded_list]

print ("The upper channel unsmooth list is : ", upper_price_channel_list_unsmooth)
upper_price_channel_list = smooth_list(upper_price_channel_list_unsmooth)
lower_price_channel_list = smooth_list(lower_price_channel_list_unsmooth)
print ("The upper Guide is ", upper_price_channel_list, "\nand the number of element is ", len(upper_price_channel_list))
print ("The upper Guide is ", lower_price_channel_list, "\nand the number of element is ", len(lower_price_channel_list))

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
  print ("json data for ",ticker, "does not exist in",configuration_json, "file")
else :
  if ("Upper_Price_Channel_Adj" in config_json[ticker]):
    len_upper_price_channel_adj = len(config_json[ticker]["Upper_Price_Channel_Adj"])
    print ("The number of Upper channel adjustments specified", len_upper_price_channel_adj)
    for i in range(len_upper_price_channel_adj):
      i_start_date = config_json[ticker]["Upper_Price_Channel_Adj"][i]["Start_Date"]
      i_stop_date = config_json[ticker]["Upper_Price_Channel_Adj"][i]["Stop_Date"]
      i_adj_amount = config_json[ticker]["Upper_Price_Channel_Adj"][i]["Adj_Amount"]
      try:
        upper_price_channel_adj_start_date_list.append(dt.datetime.strptime(i_start_date, "%m/%d/%Y").date())
        upper_price_channel_adj_stop_date_list.append(dt.datetime.strptime(i_stop_date, "%m/%d/%Y").date())
        upper_price_channel_adj_amount_list.append(float(i_adj_amount))
      except (ValueError):
        print("\n***** Error : Either the Start/Stop Dates or the Adjust Amount are not in proper format for Upper_Price_Channel_Adj in Configuration json file.\n"
              "***** Error : The Dates should be in the format %m/%d/%Y and the Adjust Amount should be a int/float\n"
              "***** Error : Found somewhere in :", i_start_date, i_stop_date, i_adj_amount)
        sys.exit(1)

print ("The Upper Channel Start Date List", upper_price_channel_adj_start_date_list)
print ("The Upper Channel Stop Date List", upper_price_channel_adj_stop_date_list)
print ("The Upper Channel Adjust List", upper_price_channel_adj_amount_list)


if (ticker not in config_json.keys()):
  print("json data for ", ticker, "does not exist in", configuration_json, "file")
else:
  if ("Lower_Price_Channel_Adj" in config_json[ticker]):
    len_lower_price_channel_adj = len(config_json[ticker]["Lower_Price_Channel_Adj"])
    print ("The number of Lower channel adjustments specified", len_lower_price_channel_adj)
    for i in range(len_lower_price_channel_adj):
      i_start_date = config_json[ticker]["Lower_Price_Channel_Adj"][i]["Start_Date"]
      i_stop_date = config_json[ticker]["Lower_Price_Channel_Adj"][i]["Stop_Date"]
      i_adj_amount = config_json[ticker]["Lower_Price_Channel_Adj"][i]["Adj_Amount"]
      try:
        lower_price_channel_adj_start_date_list.append(dt.datetime.strptime(i_start_date, "%m/%d/%Y").date())
        lower_price_channel_adj_stop_date_list.append(dt.datetime.strptime(i_stop_date, "%m/%d/%Y").date())
        lower_price_channel_adj_amount_list.append(float(i_adj_amount))
      except (ValueError):
        print("\n***** Error : Either the Start/Stop Dates or the Adjust Amount are not in proper format for Lower_Price_Channel_Adj in Configuration json file.\n"
              "***** Error : The Dates should be in the format %m/%d/%Y and the Adjust Amount should be a int/float\n"
              "***** Error : Found somewhere in :", i_start_date, i_stop_date, i_adj_amount)
        sys.exit(1)
print ("The Lower Channel Start Date List", lower_price_channel_adj_start_date_list)
print ("The Lower Channel Stop Date List", lower_price_channel_adj_stop_date_list)
print ("The Lower Channel Adjust List", lower_price_channel_adj_amount_list)

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
      upper_price_channel_list[i_index - days_in_2_qtrs] = upper_price_channel_list[i_index - days_in_2_qtrs] + upper_price_channel_adj_amount

for i_idx in range(len_lower_price_channel_adj):
  lower_price_channel_adj_start_date = lower_price_channel_adj_start_date_list[i_idx]
  lower_price_channel_adj_stop_date = lower_price_channel_adj_stop_date_list[i_idx]
  lower_price_channel_adj_amount = lower_price_channel_adj_amount_list[i_idx]
  for i_date in date_list:
    if (lower_price_channel_adj_start_date <= i_date <= lower_price_channel_adj_stop_date):
      i_index = date_list.index(i_date)
      print ("Date ", i_date, "lies between start Date", lower_price_channel_adj_start_date, "and stop Date",lower_price_channel_adj_stop_date, "at index ", i_index )
      lower_price_channel_list[i_index-days_in_2_qtrs] = lower_price_channel_list[i_index-days_in_2_qtrs] +  lower_price_channel_adj_amount
# =============================================================================

# Now shift the price channels by two quarters
# Approximately 6 months = 126 business days by inserting 126 nan at location 0
nan_list = []
for i in range(days_in_2_qtrs):
  upper_price_channel_list.insert(0,float('nan'))
  lower_price_channel_list.insert(0,float('nan'))

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
fig, main_plt = plt.subplots()
fig.set_size_inches(16,10)  # Length x height
fig.subplots_adjust(right=0.90)
fig.autofmt_xdate()
main_plt.set_facecolor("lightgrey")
main_plt.set_title("Stock Chart for " + ticker)


# Various plots that share the same x axis(date)
price_plt = main_plt.twinx()
spy_plt = main_plt.twinx()
annual_past_eps_plt = main_plt.twinx()
annual_projected_eps_plt = main_plt.twinx()
upper_channel_plt = main_plt.twinx()
lower_channel_plt = main_plt.twinx()
yr_eps_02_5_plt = main_plt.twinx()
yr_eps_05_0_plt = main_plt.twinx()
yr_eps_10_0_plt = main_plt.twinx()
yr_eps_20_0_plt = main_plt.twinx()
# yr_eps_02_5_plt[0] = main_plt.twinx()

if (pays_dividend == 1):
  dividend_plt = main_plt.twinx()

print ("Type of fig ", type(fig), \
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
main_plt.set_ylabel('Q EPS')
main_plt.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
main_plt_inst = main_plt.plot(date_list[0:plot_period_int],qtr_eps_expanded_list[0:plot_period_int],label = 'Q EPS',color="deeppink",marker='.')
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Historical Price Plot
# -----------------------------------------------------------------------------
price_plt.set_ylabel('Price', color='k')
price_plt.set_ylim(price_lim_lower,price_lim_upper)
price_plt.set_yscale(chart_type)
price_plt_inst = price_plt.plot(date_list[0:plot_period_int], ticker_adj_close_list[0:plot_period_int], label = 'Adj Close',color="brown",linestyle='-')
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Historical Price Plot
# -----------------------------------------------------------------------------
# spy_plt.set_ylabel('S&P', color='k')
spy_plt.set_ylim(price_lim_lower,price_lim_upper)
spy_plt_inst = spy_plt.plot(date_list[0:plot_period_int], spy_adj_close_list[0:plot_period_int], label = 'S&P',color="green",linestyle='-')
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Average Annual EPS Plot
# -----------------------------------------------------------------------------
# Find the eps points that fall in the plot range
annual_past_eps_plt.set_ylim(qtr_eps_lim_lower,qtr_eps_lim_upper)
annual_past_eps_plt.set_yticks([])
annual_past_eps_plt_inst = annual_past_eps_plt.plot(date_list[0:plot_period_int], annual_past_eps_expanded_list[0:plot_period_int], label = '4 qtrs/4',color="black",marker='D',markersize='4')
# todo : maybe change this to only have the value printed out at the year ends
for i in range(len(yr_eps_date_list)):
  print ("The Date is ", yr_eps_date_list[i], " Corresponding EPS ", yr_eps_list[i])
  # check if the date is in the plot range
  if (date_list[plot_period_int] <= yr_eps_date_list[i] <= date_list[0]):
    x = float("{0:.2f}".format(yr_eps_list[i]))
    main_plt.text(yr_eps_date_list[i],yr_eps_list[i],x, fontsize=11, horizontalalignment='center',verticalalignment='bottom')
    # main_plt.text(yr_eps_date_list[i],yr_eps_list[i],x, bbox={'facecolor':'white'})

annual_projected_eps_plt.set_ylim(qtr_eps_lim_lower,qtr_eps_lim_upper)
annual_projected_eps_plt.set_yticks([])
annual_projected_eps_plt_inst = annual_projected_eps_plt.plot(date_list[0:plot_period_int], annual_projected_eps_expanded_list[0:plot_period_int], label = '4 qtrs/4',color="White",marker='D',markersize='4')
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Dividend plot
# -----------------------------------------------------------------------------
if (pays_dividend == 1):
  dividend_plt.set_ylim(qtr_eps_lim_lower,qtr_eps_lim_upper)
  dividend_plt.set_yticks([])
  dividend_plt_inst = dividend_plt.plot(date_list[0:plot_period_int], dividend_expanded_list[0:plot_period_int], label = 'Dividend',color="Orange",marker='x',markersize='6')
  for i in range(len(dividend_date_list)):
    if (date_list[plot_period_int] <= dividend_date_list[i] <= date_list[0]):
      x = float("{0:.2f}".format(dividend_list[i]))
      main_plt.text(dividend_date_list[i],dividend_list[i],x, fontsize=6, horizontalalignment='center',verticalalignment='bottom')
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Price channels
# -----------------------------------------------------------------------------
for i_idx in range(number_of_growth_proj):

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
    yr_eps_02_5_plt_0.set_ylim(qtr_eps_lim_lower,qtr_eps_lim_upper)
    yr_eps_02_5_plt_0.set_yticks([])
    yr_eps_02_5_plt_inst_0 = yr_eps_02_5_plt_0.plot(date_list[0:plot_period_int],
                                                    yr_eps_02_5_growth_expanded_list[i_idx][0:plot_period_int],
                                                    label='Q 2.5%',color="Cyan", linestyle='-', linewidth=1)

    yr_eps_05_0_plt_0 = main_plt.twinx()
    yr_eps_05_0_plt_0.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
    yr_eps_05_0_plt_0.set_yticks([])
    yr_eps_05_0_plt_inst_0 = yr_eps_05_0_plt_0.plot(date_list[0:plot_period_int],
                                                    yr_eps_05_0_growth_expanded_list[i_idx][0:plot_period_int],
                                                    label='Q 2.5%', color="Yellow", linestyle='-', linewidth=1)

    yr_eps_10_0_plt_0 = main_plt.twinx()
    yr_eps_10_0_plt_0.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
    yr_eps_10_0_plt_0.set_yticks([])
    yr_eps_10_0_plt_inst_0 = yr_eps_10_0_plt_0.plot(date_list[0:plot_period_int],
                                                    yr_eps_10_0_growth_expanded_list[i_idx][0:plot_period_int],
                                                    label='Q 2.5%', color="Cyan", linestyle='-', linewidth=1)

    yr_eps_20_0_plt_0 = main_plt.twinx()
    yr_eps_20_0_plt_0.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
    yr_eps_20_0_plt_0.set_yticks([])
    yr_eps_20_0_plt_inst_0 = yr_eps_20_0_plt_0.plot(date_list[0:plot_period_int],
                                                    yr_eps_20_0_growth_expanded_list[i_idx][0:plot_period_int],
                                                    label='Q 2.5%', color="Yellow", linestyle='-', linewidth=1)

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
                                                    label='Q 2.5%', color="Yellow", linestyle='-', linewidth=1)

    yr_eps_10_0_plt_1 = main_plt.twinx()
    yr_eps_10_0_plt_1.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
    yr_eps_10_0_plt_1.set_yticks([])
    yr_eps_10_0_plt_inst_1 = yr_eps_10_0_plt_1.plot(date_list[0:plot_period_int],
                                                    yr_eps_10_0_growth_expanded_list[i_idx][0:plot_period_int],
                                                    label='Q 2.5%', color="Cyan", linestyle='-', linewidth=1)

    yr_eps_20_0_plt_1 = main_plt.twinx()
    yr_eps_20_0_plt_1.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
    yr_eps_20_0_plt_1.set_yticks([])
    yr_eps_20_0_plt_inst_1 = yr_eps_20_0_plt_1.plot(date_list[0:plot_period_int],
                                                    yr_eps_20_0_growth_expanded_list[i_idx][0:plot_period_int],
                                                    label='Q 2.5%', color="Yellow", linestyle='-', linewidth=1)

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
upper_channel_plt.set_ylim(qtr_eps_lim_lower,qtr_eps_lim_upper)
upper_channel_plt.set_yticks([])
upper_channel_plt_inst = upper_channel_plt.plot(date_list[0:plot_period_int], upper_price_channel_list[0:plot_period_int],label= 'top', color="blue",linestyle = '-')
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Lower Price Channel Plot
# -----------------------------------------------------------------------------
# upper_channel_plt.set_ylabel('Upper_guide', color = 'b')
# upper_channel_plt.spines["right"].set_position(("axes", 1.2))
lower_channel_plt.set_ylim(qtr_eps_lim_lower,qtr_eps_lim_upper)
lower_channel_plt.set_yticks([])
lower_channel_plt_inst = lower_channel_plt.plot(date_list[0:plot_period_int], lower_price_channel_list[0:plot_period_int],label= 'bot', color="blue",linestyle = '-')
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Collect the labels for the subplots and then create the legends
# -----------------------------------------------------------------------------
# lns = main_plt_inst + \
#       yr_eps_20_0_plt_inst + yr_eps_10_0_plt_inst + \
#       yr_eps_05_0_plt_inst + yr_eps_02_5_plt_inst + \
#       annual_past_eps_plt_inst + upper_channel_plt_inst + \
#       lower_channel_plt_inst + price_plt_inst + spy_plt_inst
lns = main_plt_inst + \
      annual_past_eps_plt_inst + upper_channel_plt_inst + \
      lower_channel_plt_inst + price_plt_inst + spy_plt_inst
labs = [l.get_label() for l in lns]
# This works - puts the legend in upper-left
# main_plt.legend(lns, labs, loc="upper left", fontsize = 'x-small')
main_plt.legend(lns, labs,bbox_to_anchor=(1.005,-0.13), loc="lower left", borderaxespad=2,fontsize = 'x-small')
# Thw works perfectly well as well
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
    my_text = "This is a dummy comment for text box #0 \nAnything can be put here"
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
  a_text=AnchoredText(my_text, loc=location)
  main_plt.add_artist(a_text)
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Annonate at a particular price on the chart
# -----------------------------------------------------------------------------
# This works but needs more research
# Date to annotate
date_to_annotate = "2017-03-29"
date_to_annotate_datetime = dt.datetime.strptime(date_to_annotate, '%Y-%m-%d').date()
# date_to_annoate_num = matplotlib.dates.date2num(date_to_annotate)
match_date = min(date_list, key=lambda d: abs(d - date_to_annotate_datetime))
print("The matching date is ", match_date, " at index ", date_list.index(match_date), " and the price is " ,ticker_adj_close_list[date_list.index(match_date)])

price_plt.annotate('UK Referendom for Brexit',xy= (date_list[date_list.index(match_date)],ticker_adj_close_list[date_list.index(match_date)]),
                   arrowprops=dict(facecolor='black', width=1))
# xytext=(50, 30),textcoords='offset points', arrowprops=dict(facecolor='black', width=1))
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Set the gridlines
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

yr_dates = pd.date_range(date_list[plot_period_int], date_list[0], freq='Y')
qtr_dates = pd.date_range(date_list[plot_period_int], date_list[0], freq='Q')
print ("Yearly Dates are ", yr_dates)
print ("Quarterly Dates are ", type(qtr_dates))

qtr_dates_tmp = []
yr_dates_tmp = []
for x in qtr_dates:
  print ("The original Quarterly Date is :", x)
  if (x.is_year_end is True):
    print("This quarter is also year end date. Removing ", type(x))
  if (x in yr_dates):
    print ("This quarter is also year end date. Removing ",type(x))
  else:
    qtr_dates_tmp.append(x.date().strftime('%m/%d/%Y'))

for x in yr_dates:
  print ("The original Yearly Date is :", x)
  yr_dates_tmp.append(x.date().strftime('%m/%d/%Y'))


print ("The modified qtr dates list is: ", qtr_dates)
print ("The modified qtr dates list is: ", qtr_dates_tmp)
print ("The modified yr dates list is: ", yr_dates_tmp)

main_plt.set_xticks(yr_dates_tmp,minor=False)
main_plt.set_xticks(qtr_dates_tmp, minor=True)
main_plt.xaxis.set_tick_params(width=5)
main_plt.set_xticklabels(yr_dates_tmp, rotation = 90,  fontsize=8,color='blue',minor=False, fontstyle='italic')
main_plt.set_xticklabels(qtr_dates_tmp, rotation = 90,  fontsize=7,minor=True)
main_plt.grid(which='major', axis='x',linestyle='-',color='black',linewidth=1.5)
main_plt.grid(which='minor', linestyle='--',color='blue')
main_plt.grid(which='major', axis='y',linestyle='--',color='green',linewidth=1)


# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Save the Chart with the date and time as prefix
# -----------------------------------------------------------------------------
# This works too instead of two line
# date_time =  dt.datetime.now().strftime("%Y_%m_%d_%H_%M")
now = dt.datetime.now()
date_time = now.strftime("%Y_%m_%d_%H_%M")
fig.savefig(chart_dir + "\\" + ticker + "_" + date_time + ".jpg",dpi=200)
plt.show()
# -----------------------------------------------------------------------------


