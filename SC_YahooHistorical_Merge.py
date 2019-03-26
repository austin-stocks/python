import pandas as pd
import matplotlib
import datetime as dt
import numpy as np
import matplotlib.pyplot as plt
import os

# This program reads the
# 1. Calendar file
# 2. Yahoo Historical Downloaded file
# 3. Configurations file (in the loop)

# =============================================================================
# Define the various filenames and Directory Paths to be used
# =============================================================================
dir_path = os.getcwd()
user_dir = "User Files"
tracklist_file = "Tracklist.csv"
tracklist_file_full_path = dir_path + "\\" + user_dir + "\\" + tracklist_file
yahoo_hist_in_dir = dir_path + "\\Download\YahooHistorical"
yahoo_hist_out_dir = dir_path + "\\Historical"
# =============================================================================


# =============================================================================
# Read the Calendar and
# Configurations csv - set the index for config_df as Ticker column rather
# than the default
# =============================================================================
calendar_df = pd.read_csv(user_dir + "\\Calendar.csv")
config_df = pd.read_csv(user_dir + "\\Configurations.csv")
config_df.set_index('Ticker', inplace=True)
print ("The configuration df", config_df)
# =============================================================================

# =============================================================================
# Get the years in the Calendar and concatenate them. This will generate a list
# that is from say year 2024 to 2020 (or whatever years the calendar has)
# =============================================================================
# print("The Calendar is", calendar_df)
col_list = calendar_df.columns.tolist()
print("The years are ", col_list)
calendar_date_list_raw = []
for col in col_list:
  tmp_list = calendar_df[col].dropna().tolist()
  print("The date in col", col, " are ", tmp_list)
  calendar_date_list_raw.extend(tmp_list)

print("The concatenated Calendar list is ", calendar_date_list_raw)
# calendar_date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in calendar_df.iloc[:, 0]]
calendar_date_list = [dt.datetime.strptime(str(date), '%m/%d/%y').date() for date in calendar_date_list_raw]
print("The Calendar Date list is", calendar_date_list, "\nand it has", len(calendar_date_list), " elements")
# =============================================================================


# =============================================================================
# For each ticker in the ticker list from tracklist
# Open the Downloaded Yahoo Historical
# =============================================================================
tracklist_df = pd.read_csv(tracklist_file_full_path)
ticker_list_unclean = tracklist_df['Tickers'].tolist()
ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']
print ("The ticker list is", ticker_list)

for ticker_raw in ticker_list:
  ticker = ticker_raw.replace(" ", "").upper()  # Remove all spaces from ticker_raw
  print("Creating Historical Data for ", ticker)

  if ticker in config_df.index:
    ticker_config_series = config_df.loc[ticker]
    print("Then configurations for ", ticker, " is\n", ticker_config_series)
  else:
    # Todo : Create a default series at the start of the program
    print ("Configuration Entry for ", ticker , " not found...continuing with default values")
    continue

  # Get how many  future Quarters should be left in the final csv
  future_cal_quarter = ticker_config_series['Future Calendar Quarters']


  # Read the input Yahoo Historical csv
  in_historical_csv = yahoo_hist_in_dir + "\\" + ticker + "_yahoo_historical.csv"
  historical_df = pd.read_csv(in_historical_csv)
   # Drop any row that has nan values
  historical_df.dropna(inplace=True)
  # print("Historical Dataframe ", historical_df)
  historical_date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in historical_df.iloc[:, 0]]
  historical_col_str = ','.join(historical_df.columns.tolist())
  # print("The Historical Columns are", historical_col_str)

  # Match the first date in historical to the dates in calendar
  match_date = min(calendar_date_list, key=lambda d: abs(d - historical_date_list[0]))
  print("The matching date is ", match_date, " at index ", calendar_date_list.index(match_date))

  # Now snip the calendar_date_list so that it starts at future_cal_quarter before match_date and
  # ends at match date
  # Delete everything after - and including - the match index
  calendar_date_start_index = calendar_date_list.index(match_date) - int(future_cal_quarter*64)
  # print ("Will Start the Calendar from index", calendar_date_start_index)
  calendar_date_list_mod = calendar_date_list[calendar_date_start_index:calendar_date_list.index(match_date)]
  # print("The modified Calendar list is ", calendar_date_list_mod, "and it has \n", len(calendar_date_list_mod), "elements")

  # ===========================================================================
  # Now write the Data in csv
  # ===========================================================================
  out_histrocal_csv = yahoo_hist_out_dir + "\\" + ticker + "_historical.csv"
  fout = open(out_histrocal_csv, "w")
  # First write the Columns
  fout.write(str(historical_col_str + '\n'))

  # Then write the modified list of Calendar
  for x in calendar_date_list_mod:
    fout.write(x.strftime('%m/%d/%Y') + '\n')

  # Then write the historical Data
  x = historical_df.to_string(header=False, index=False, index_names=False).split('\n')
  row_list = [','.join(ele.split()) for ele in x]
  for x in row_list:
    fout.write(x + '\n')

  fout.close()
  # =============================================================================
