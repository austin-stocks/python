import pandas as pd
import datetime as dt
import numpy as np
import os
import sys
import logging
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
log_dir = "\\..\\" + "Logs"
# =============================================================================

# ---------------------------------------------------------------------------
# Set Logging
# critical, error, warning, info, debug
# set up logging to file - see previous section for more details
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename=dir_path + log_dir + "\\" + 'SC_YahooHistorical_merge_debug.txt',
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


# There are a few  stocks that change names (RECN -> RGP) and Yahoo stops historical
# data fro RECN and start for RGP. However RGP only has historical data from the
# date the name change became effective. So, in essence, we are left with two
# pieces of data for RECN(Now RGP). One till the date RECN was RECN and one after
# RECN became RGP. This scipt needs to stitch those two pieces together.
tickers_historical_data_to_merge_dict = {
  'RGP' : 'RECN'
}


# =============================================================================
# Read the Calendar and
# Configurations csv - set the index for config_df as Ticker column rather
# than the default
# =============================================================================
calendar_df = pd.read_csv(calendar_file_full_path)
config_df = pd.read_csv(configurations_file_full_path)
config_df.set_index('Ticker', inplace=True)
# logging.debug("The configuration df \n" + config_df.to_string())
# =============================================================================

# =============================================================================
# Get the years in the Calendar and concatenate them. This will generate a list
# that is from say year 2024 to 2020 (or whatever years the calendar has dates for)
# =============================================================================
# print("The Calendar is", calendar_df)
col_list = calendar_df.columns.tolist()
logging.debug("The years in the Calendar file are : " + str(col_list))
calendar_date_list_raw = []
for col in col_list:
  tmp_list = calendar_df[col].dropna().tolist()
  logging.debug("The date in col" + str(col) + " are " + str(tmp_list))
  calendar_date_list_raw.extend(tmp_list)

# for date_str in calendar_date_list_raw:
#   date_dt = dt.datetime.strptime(date_str, '%m/%d/%Y').date()
#   print("The string is ", date_str, " and the converted is ", date_dt)
# sys.exit(1)
# print("The concatenated Calendar list is ", calendar_date_list_raw)
# calendar_date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in calendar_df.iloc[:, 0]]
calendar_date_list = [dt.datetime.strptime(str(date), '%m/%d/%Y').date() for date in calendar_date_list_raw]
# print("The Calendar Date list is", calendar_date_list, "\nand it has", len(calendar_date_list), " elements")
# =============================================================================


# =============================================================================
# For each ticker in the ticker list from tracklist
# Open the Downloaded Yahoo Historical
# =============================================================================

get_sp_holdings = 0
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
i_idx = 1
for ticker_raw in ticker_list:
  ticker = ticker_raw.replace(" ", "").upper()  # Remove all spaces from ticker_raw and convert to uppercase
  logging.debug("Merging Historical Data with Calendar for : " +str(ticker))

  if (ticker == "BRK.B"):
    ticker = "BRK-B"
  elif (ticker == "BF.B"):
    ticker = "BF-B"

  if ticker in config_df.index:
    ticker_config_series = config_df.loc[ticker]
    logging.debug("The configurations fields for " +str(ticker) + " \n" +str(ticker_config_series))
  else:
    logging.error("**********                                  ERROR                              **********")
    logging.error("**********     Entry for " + str(ticker).center(10) + " not found in the configurations file     **********")
    logging.error("**********     Please create one and then run the script again                 **********")
    sys.exit(1)


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
  # ===========================================================================

  if ticker in tickers_historical_data_to_merge_dict:
    ticker_with_older_historical_data = tickers_historical_data_to_merge_dict[ticker]
    # Read the older historical data
    older_historical_df =  pd.read_csv(yahoo_hist_out_dir + "\\" + ticker_with_older_historical_data + "_historical.csv")
    # logging.debug("The historical df for (new) ticker \n" + historical_df.to_string())
    # logging.debug("The historical df for the already existing (older) ticker " + str(ticker_with_older_historical_data) + " is \n" + older_historical_df.head().to_string())

    historical_date_list_dt = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in historical_df.Date.tolist()]
    older_historical_date_list_dt = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in older_historical_df.Date.tolist()]
    # Steps followed:
    # 1. Find the last date for which the historical data is available for old ticker
    # 2. match it with the date_list from the current ticker historical data and convert it to an index
    # 3. Then delete all the data from that index down in the current ticker historical data
    #   (as the downloaded data just has all the dates columns but nothing the the prices/volume columns)
    # 4. Finally append the new and old dataframe together
    last_older_historical_date_dt = older_historical_date_list_dt[0]
    match_date = min(historical_date_list_dt, key=lambda d: abs(d - last_older_historical_date_dt))
    match_date_index = historical_date_list_dt.index(match_date)
    logging.info("Iteration no : " + str(i_idx) + ", " + str(ticker) + " needs to be merged with " + str(ticker_with_older_historical_data))
    logging.info("Iteration no : " + str(i_idx) + ", " + "Will use " + str(ticker) + " data(new) till " + str(match_date) + " and then " + str(ticker_with_older_historical_data) +  " data(older) onwards to create the historical data")
    logging.info("Iteration no : " + str(i_idx) + ", " + "Please check the historical file or final chart to make sure that merging happened correctly")
    logging.debug("Matched date " + str(match_date) + " at index " + str(match_date_index))
    historical_df_tmp = historical_df.iloc[:match_date_index]
    logging.debug("The historical df after cleaninn up is \n" + historical_df_tmp.to_string())
    # Now append the two historical df together and then remove the duplicates in date, if they exist
    historical_df = historical_df_tmp.append(older_historical_df, ignore_index=True)
    logging.debug("The historical df after merging two df together is \n" + historical_df.to_string())
  # sys.exit(1)

  # ===========================================================================
  # Insert Moving averages
  # ===========================================================================
  # For some reason Empty_col_H cannot just have a "," which would have truly
  #   inserted a blank column. Maybe there is way but my solution below does not
  #   break anything
  # historical_df.loc[:, 'Empty_col_H'] = ',' Does not work
  # historical_df.loc[:, 'Empty_col_H'] = ' ' Inserting space does not work either to get
  #   an empty column

  # Since we are guaranteed to have dates now for all the rows, now
  # interpolate the values on the columns that have missing data (price, volume)
  historical_df.interpolate(inplace=True)
  # print("Historical Dataframe ", historical_df)


  # So - now - Inserting a non-threatening character
  historical_df.loc[:, 'Empty_col_H'] =  '-'
  # Add the moving averages - They are added as columns after Empty Columns
  historical_df['MA_Price_200_day'] = historical_df.rolling(window=200)['Adj_Close'].mean().shift(-199)
  historical_df['MA_Price_50_day'] = historical_df.rolling(window=50)['Adj_Close'].mean().shift(-49)
  historical_df['MA_Price_20_day'] = historical_df.rolling(window=20)['Adj_Close'].mean().shift(-19)
  historical_df['MA_Price_10_day'] = historical_df.rolling(window=10)['Adj_Close'].mean().shift(-9)
  historical_df['MA_Volume_50_day'] = historical_df.rolling(window=50)['Volume'].mean().shift(-49)
  # ===========================================================================

  historical_date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in historical_df.iloc[:, 0]]
  historical_col_str = ','.join(historical_df.columns.tolist())
  # print("The Historical Columns are", historical_col_str)

  # Match the first/latest date from historical date list to the dates in calendar.
  # This will become the ending index for extracting the dates from calendar_date_list
  cal_match_date_with_historical = min(calendar_date_list, key=lambda d: abs(d - historical_date_list[0]))
  cal_match_date_with_historical_index = calendar_date_list.index(cal_match_date_with_historical)
  logging.debug("The latest historical date is : "  + str(historical_date_list[0]) +  ". Closest Matching date in Calendar is : " + str(cal_match_date_with_historical) + " at index : " + str(cal_match_date_with_historical_index))

  # ===========================================================================
  # User specifies what date he/she wants the historical data to start from. The user specifies it as:
  # 1. Either as a date. If so - then get the index of the data from the calendar date list
  # 2. If the date is not specified then a future number of quarters are specified.
  # 3. If that is not specified then the script assumes 8 more quarters
  # This will become lead to calculating the starting index for extracting the dates from calendar_date_list
  # ===========================================================================
  calendar_future_date_str = ticker_config_series['Calendar_Future_Date']
  logging.debug("User Specified Calendar Future Date from the config file : "  + str(calendar_future_date_str))
  if (str(calendar_future_date_str) != 'nan'):
    calendar_future_date = dt.datetime.strptime(calendar_future_date_str, '%m/%d/%Y').date()
    calendar_future_match_date = min(calendar_date_list, key=lambda d: abs(d - calendar_future_date))
    calendar_future_date_index = calendar_date_list.index(calendar_future_match_date)
    logging.debug("The nearest matching date (for user specified date : " + str(calendar_future_date) +  ") in calendar date list is : " + str(calendar_future_match_date) + ", at calendar index : " + str(calendar_future_date_index))
  else:
    # print("Found nan for Calendar Future End date. Will now look for Future Calendar Quarters")
    future_cal_quarter = ticker_config_series['Future_Calendar_Quarters']
    # print ("Future Calendar Quarters is : ", future_cal_quarter)
    if (str(future_cal_quarter) == 'nan'):
      # print ("Found nan for Future Calendar Quarters. Will assume user wants 8 future quarters")
      future_cal_quarter = 8
    calendar_future_date_index = cal_match_date_with_historical_index - int(future_cal_quarter*64)
  # ===========================================================================

  fiscal_year_ends = ticker_config_series['Fiscal_Year']
  if (str(fiscal_year_ends) == 'nan'):
    fiscal_year_ends = "Dec"

  month_list = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  if (fiscal_year_ends not in month_list):
    print ("**********                                  ERROR                                 **********")
    print ("**********     Fiscal Year ==>(", fiscal_year_ends, ")<== for ", str(ticker).center(10) , " is not a valid month    **********")
    print ("**********     Please correct the fiscal Year and then run the script again       **********")
    sys.exit(1)
  logging.debug("Will use the Calendar date list from index : " + str(calendar_future_date_index) + " to index : " + str(cal_match_date_with_historical_index))
  calendar_date_list_mod = calendar_date_list[calendar_future_date_index:cal_match_date_with_historical_index]
  logging.info("Iteration no : " + str(i_idx) + ", Ticker : " + str(ticker) + " : Fiscal Year ends in " + str(fiscal_year_ends) + " : Merging Historical Data with Calendar until the future date : " + str(calendar_date_list[calendar_future_date_index]))
  logging.debug("The modified Calendar list is " + str(calendar_date_list_mod) + " and it has \n" + str(len(calendar_date_list_mod)) +  " elements")

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
  i_idx += 1

  # =============================================================================
