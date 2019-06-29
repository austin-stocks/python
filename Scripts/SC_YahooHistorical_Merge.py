import pandas as pd
import datetime as dt
import numpy as np
import os

# This program reads the
# 1. Calendar file
# 2. Yahoo Historical Downloaded file
# 3. Configurations file (in the loop)

# =============================================================================
# Define the various filenames and Directory Paths to be used
# =============================================================================
dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
tracklist_file = "Tracklist.csv"
calendar_file = "Calendar.csv"
configuration_file = "Configurations.csv"
tracklist_file_full_path = dir_path + user_dir + "\\" + tracklist_file
calendar_file_full_path = dir_path + user_dir + "\\" + calendar_file
configurations_file_full_path = dir_path + user_dir + "\\" + configuration_file
yahoo_hist_in_dir = dir_path + "\\..\\Download\YahooHistorical"
yahoo_hist_out_dir = dir_path + "\\..\\Historical"
# =============================================================================


# =============================================================================
# Read the Calendar and
# Configurations csv - set the index for config_df as Ticker column rather
# than the default
# =============================================================================
calendar_df = pd.read_csv(calendar_file_full_path)
config_df = pd.read_csv(configurations_file_full_path)
config_df.set_index('Ticker', inplace=True)
print ("The configuration df", config_df)
# =============================================================================

# =============================================================================
# Get the years in the Calendar and concatenate them. This will generate a list
# that is from say year 2024 to 2020 (or whatever years the calendar has dates for)
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

get_sp_holdings = 1
if (get_sp_holdings == 1):
  tracklist_df = pd.read_excel(dir_path + user_dir + "\\" + 'SPY_All_Holdings.xlsx', sheet_name="SPY")
  ticker_list_unclean = tracklist_df['Identifier'].tolist()
  ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']
else:
  # Read the trracklist and convert the read tickers into a list
  tracklist_df = pd.read_csv(tracklist_file_full_path)
  # print ("The Tracklist df is", tracklist_df)
  ticker_list_unclean = tracklist_df['Tickers'].tolist()
  ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']

# main Loop for Tickers
for ticker_raw in ticker_list:
  ticker = ticker_raw.replace(" ", "").upper()  # Remove all spaces from ticker_raw and convert to uppercase
  print("Creating Historical Data for ", ticker)

  if (ticker == "BRK.B"):
    ticker = "BRK-B"
  elif (ticker == "BF.B"):
    ticker = "BF-B"

  if ticker in config_df.index:
    ticker_config_series = config_df.loc[ticker]
    print("Then configurations for ", ticker, " is\n", ticker_config_series)
  else:
    # Todo : Create a default series at the start of the program
    print ("Configuration Entry for ", ticker , " not found...continuing with default values")
    continue


  # ===========================================================================
  # Read the input Yahoo Historical csv and clean it up the dataframe
  # ===========================================================================
  in_historical_csv = yahoo_hist_in_dir + "\\" + ticker + "_yahoo_historical.csv"
  historical_df = pd.read_csv(in_historical_csv)
  # Drop any row that has nan values in ALL the columns
  historical_df.dropna(how='all',inplace=True)
  # Drop ONLY the rows now that do not have Date
  historical_df_tmp = historical_df[pd.notnull(historical_df['Date'])]
  historical_df = historical_df_tmp
  # Since we are guaranteed to have dates now for all the rows, now
  # interpolate the values on the columns that have missing data (price, volume)
  historical_df.interpolate(inplace=True)
  # print("Historical Dataframe ", historical_df)
  # ===========================================================================

  # ===========================================================================
  # Insert Moving averages
  # ===========================================================================
  # For some reason Empty_col_H cannot just have a "," which would have truly
  #   inserted a blank column. Maybe there is way but my solution below does not
  #   break anything
  # historical_df.loc[:, 'Empty_col_H'] = ',' Does not work
  # historical_df.loc[:, 'Empty_col_H'] = ' ' Inserting space does not work either to get
  #   an empty column

  # So - now - Inserting a non-threatening character
  historical_df.loc[:, 'Empty_col_H'] =  '-'
  # Add the moving averages - They are added as columns after Empty Columns
  historical_df['200_day_Price_MA'] = historical_df.rolling(window=200)['Adj_Close'].mean().shift(-199)
  historical_df['50_day_Price_MA'] = historical_df.rolling(window=50)['Adj_Close'].mean().shift(-49)
  historical_df['20_day_Price_MA'] = historical_df.rolling(window=20)['Adj_Close'].mean().shift(-19)
  historical_df['10_day_Price_MA'] = historical_df.rolling(window=10)['Adj_Close'].mean().shift(-9)
  historical_df['50_day_Volume_MA'] = historical_df.rolling(window=50)['Volume'].mean().shift(-49)
  # ===========================================================================

  historical_date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in historical_df.iloc[:, 0]]
  historical_col_str = ','.join(historical_df.columns.tolist())
  # print("The Historical Columns are", historical_col_str)

  # Match the first/latest date from historical date list to the dates in calendar.
  # This will become the ending index for extracting the dates from calendar_date_list
  cal_match_date_with_historical = min(calendar_date_list, key=lambda d: abs(d - historical_date_list[0]))
  cal_match_date_with_historical_index = calendar_date_list.index(cal_match_date_with_historical)
  print("The latest historical date is : ", historical_date_list[0], ". Closest Matching date in Calendar is :", cal_match_date_with_historical, " at index : ", cal_match_date_with_historical_index)

  # ===========================================================================
  # User specifies what date he/she wants the historical data to start from. The user specifies it as:
  # 1. Either as a date. If so - then get the index of the data from the calendar date list
  # 2. If the date is not specified then a future number of quarters are specified.
  # 3. If that is not specified then the script assumes 8 more quarters
  # This will become lead to calculating the starting index for extracting the dates from calendar_date_list
  # ===========================================================================
  calendar_future_date_str = ticker_config_series['Calendar_Future_Date']
  print ("User Specified Calendar Future Date is : ", calendar_future_date_str)
  if (str(calendar_future_date_str) != 'nan'):
    calendar_future_date = dt.datetime.strptime(calendar_future_date_str, '%m/%d/%Y').date()
    calendar_future_match_date = min(calendar_date_list, key=lambda d: abs(d - calendar_future_date))
    calendar_future_date_index = calendar_date_list.index(calendar_future_match_date)
    print ("The nearest matching date (for user specified date : ", calendar_future_date, ") in calendar date list is : ", calendar_future_match_date, ", at calendar index : ", calendar_future_date_index)
  else:
    print("Found nan for Calendar Future End date. Will now look for Future Calendar Quarters")
    future_cal_quarter = ticker_config_series['Future_Calendar_Quarters']
    print ("Future Calendar Quarters is : ", future_cal_quarter)
    if (str(future_cal_quarter) == 'nan'):
      print ("Found nan for Future Calendar Quarters. Will assume user wants 8 future quarters")
      future_cal_quarter = 8
    calendar_future_date_index = cal_match_date_with_historical_index - int(future_cal_quarter*64)
  # ===========================================================================


  print ("Will use the Calendar date list from index : ", calendar_future_date_index, " to index : ",cal_match_date_with_historical_index)
  calendar_date_list_mod = calendar_date_list[calendar_future_date_index:cal_match_date_with_historical_index]
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

  # Now calculate the 200, 50, 20 and 10 day ma for adj close and 20 day for volume
  # Then write the historical Data
  x = historical_df.to_string(header=False, index=False, index_names=False).split('\n')
  row_list = [','.join(ele.split()) for ele in x]
  for x in row_list:
    fout.write(x + '\n')

  fout.close()
  # =============================================================================
