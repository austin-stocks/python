import csv
import openpyxl
from openpyxl.styles import PatternFill
import os
import xlrd
import sys
import math
import time
import pandas as pd
import datetime as dt
from yahoofinancials import YahooFinancials
import time
import logging
import xlsxwriter
import matplotlib.pyplot as plt


def color_negative_red(val):
  """
  Takes a scalar and returns a string with
  the css property `'color: red'` for negative
  strings, black otherwise.
  """
  color = 'red' if val < 10 else 'black'
  return 'color: %s' % color

def human_format(num, precision=2, suffixes=['', 'K', 'M', 'B', 'T', 'P']):
  m = sum([abs(num / 1000.0 ** x) >= 1 for x in range(1, len(suffixes))])
  return f'{num / 1000.0 ** m:.{precision}f} {suffixes[m]}'

# -----------------------------------------------------------------------------
def get_ratio(current, previous):
  if (previous == 0):
    # return "Div#0#"
    return 0
  # if both are negative and current is less than previous, then the growth rate has been negative
  elif ((previous < 0) and (current < 0) and (current < previous)):
    return round(-(current / previous), 2)
  else :
    return round((current/previous), 2)

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
def get_growth(current, previous):
  if (previous == 0):
    previous = 0.01
    # return "Div#0#"
    return 0
  elif current == previous:
    return 0
  if (previous > 0) and (current > 0):
    return round(((current - previous) / previous), 2)
  elif (previous > 0) and (current < 0):
    return round(((current - previous) / previous), 2)
  elif (previous < 0) and (current > 0):
    return round(((current - previous) / previous), 2)*(-1)
  elif (previous < 0) and (current < 0):
    return round(((current - previous) / previous), 2)*(-1)

# ---------------------------------------------------------------------------
# Define the directories and the paths
# ---------------------------------------------------------------------------
dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
historical_dir = "\\..\\" + "Historical"
earnings_dir = "\\..\\" + "Earnings"
dividend_dir = "\\..\\" + "Dividend"
log_dir = "\\..\\" + "Logs"
analysis_dir = "\\..\\" + "Analysis"
analysis_plot_dir = "\\..\\" + "Analysis_Plots"
analysis_plot_watchlist_dir = "\\..\\" + "Analysis_Watchlist"
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Set Logging
# critical, error, warning, info, debug
# set up logging to file - see previous section for more details
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename=dir_path + log_dir + "\\" + 'SC_Create_0Analysis_debug.txt',
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

# Disable and enable global level logging
logging.disable(sys.maxsize)
logging.disable(logging.NOTSET)
# ---------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Sundeep thoughts on what to do for 0_Analysis
# Institutional Shares Sold vs Institutional Shares Purchased - 5 quarters
# Insiders buying / selling?  (Net Insiders buy Insiders-net shares purchased or Net Insider Buys % Shares Out or Net Insider Buys % Shares Out.) - 5 quarters
# Get the projected Revenue and Diluted EPS growth rates -- Do we need it

# Key Statistics
# price to sales - Just this quarter
# PEG Ratio - how to find that out (May need to read the earnings and find TTM earning
#   and also to find out projected earnings (deal with the case if there are only 3 quarters
#   worth of future projected earnings data available -- maybe say not available). Find the PE from
#   TTM earnings and growth rate from projected earnings...(even though the projected earnings are not
#   always diluted earnings...but that is the best thing available right now

#
# todo : Maybe add a one row table at the top - with has
# Price, PB, PS, ROE, PEG, Current Ratio, Expected Growth, it can also list some past trends in one word - etc...think about more

# Print the date of latest price and what is the price (read the historical)
# -----------------------------------------------------------------------------
g_var_plot_en = 1
g_var_copy_ticker_plot_2_watchlist_dir_en = 1

# -----------------------------------------------------------------------------
# Set the various dirs and read the AAII file
# -----------------------------------------------------------------------------
master_tracklist_file = "Master_Tracklist.xlsm"
tracklist_file = "Tracklist.csv"
tracklist_file_full_path = dir_path + user_dir + "\\" + tracklist_file
configuration_file = "Configurations.csv"
configurations_file_full_path = dir_path + user_dir + "\\" + configuration_file

tracklist_df = pd.read_csv(tracklist_file_full_path)
master_tracklist_df = pd.read_excel(dir_path + user_dir + "\\" + master_tracklist_file, sheet_name="Main")
yahoo_comany_info_df = pd.read_excel(dir_path + user_dir + "\\" + 'Yahoo_Company_Info.xlsm', sheet_name="Company_Info")

master_tracklist_list = master_tracklist_df['Tickers'].tolist()
yahoo_comany_info_df.set_index('Ticker', inplace=True)
logging.debug("The master tracklist tickers are " + str(master_tracklist_list))


ticker_list_unclean = tracklist_df['Tickers'].tolist()
ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']

aaii_missing_tickers_list = [
'CBOE','CP','CRZO','GOOG','RACE','NTR','RGP','WCG','FOX','DISCK','BRK-B'
]
watchlist_0analysis_df = pd.DataFrame(columns=['Ticker','Rev_growth','EPS_growth','BVPS_growth','FCFPS_growth','Spacer_00','No_of_Years','In_Master','Spacer_01','Revs','EPS','BVPS','FCFPS'])
skipped_tickers_df = pd.DataFrame(columns=['Ticker','Reason'])
skipped_tickers_df.set_index('Ticker', inplace=True)

# #############################################################################
#                   MAIN LOOP FOR TICKERS
# #############################################################################
# ticker_list = ['AAPL','IBM','MED']
# ticker_list = ['CSCO','IBM']

i_idx = 1
total_number_of_ticker = len(ticker_list)
for ticker_raw in ticker_list:

  ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase
  if ((ticker in aaii_missing_tickers_list)) or  (ticker in ["QQQ"]):
    logging.warning(str(ticker) + " is NOT in AAII df or is QQQ (etf). Will skip inserting EPS Projections..")
    skipped_tickers_df.loc[ticker,'Reason'] = "Is_ETF_or_missing_in_AAII_Database"
    continue

  logging.info("========================================================")
  logging.info("Iteration no : " + str(i_idx) + ", Processing : " + ticker)
  logging.info("========================================================")

  ticker_datain_qtr_file = ticker +  "_qtr_data.csv"
  if (os.path.exists(dir_path + analysis_dir + "\\" + "Quarterly" + "\\" + ticker_datain_qtr_file) is True):
    ticker_datain_qtr_df = pd.read_csv(dir_path + analysis_dir + "\\" + "Quarterly" + "\\" + ticker_datain_qtr_file)
  else:
    logging.warning("The file : " + str(ticker_datain_qtr_file) + " does not exist....Skipping")
    skipped_tickers_df.loc[ticker,'Reason'] = "qtr_data.csv_file_does_not_exits_Check_AAII_parse_Download_script_output_for_reason_why_the_file_does_not_exist"
    continue

  ticker_datain_yr_file = ticker +  "_yr_data.csv"
  if (os.path.exists(dir_path + analysis_dir + "\\" + "Yearly" + "\\" + ticker_datain_yr_file) is True):
    ticker_datain_yr_df = pd.read_csv(dir_path + analysis_dir + "\\" + "Yearly" + "\\" + ticker_datain_yr_file)
  else:
    logging.warning("The file : " + str(ticker_datain_yr_file) + " does not exist....Skipping")
    skipped_tickers_df.loc[ticker, 'Reason'] = "yr_data.csv_file_does_not_exits_Check_AAII_parse_Download_script_output_for_reason_why_the_file_does_not_exist"
    continue

  ticker_datain_ks_file = ticker +  "_key_statistics_data.csv"
  if (os.path.exists(dir_path + analysis_dir + "\\" + "Key_Statistics" + "\\" + ticker_datain_ks_file) is True):
    ticker_datain_ks_df = pd.read_csv(dir_path + analysis_dir + "\\" + "Key_Statistics" + "\\" + ticker_datain_ks_file)
  else:
    logging.warning("The file : " + str(ticker_datain_ks_df) + " does not exist....Skipping")
    skipped_tickers_df.loc[ticker, 'Reason'] = "key_statistics_data.csv_file_does_not_exits_Check_AAII_parse_Download_script_output_for_reason_why_the_file_does_not_exist"
    continue

  # ---------------------------------------------------------------------------
  # Sanity check the data
  # ---------------------------------------------------------------------------
  ticker_datain_qtr_df.set_index("AAII_QTR_DATA",inplace=True)
  logging.debug("The QTR dataframe (datain_df) read from the AAII file is : \n" + ticker_datain_qtr_df.to_string())
  ticker_qtr_numbers_df = ticker_datain_qtr_df.copy()
  if ( (len(ticker_qtr_numbers_df.columns) == 0) or (len(ticker_qtr_numbers_df.index) == 0) ) :
    logging.warning("The QTR dataframe (datain_df) for ticker : " + str(ticker) + ", either has no rows or no columns. Skipping...")
    skipped_tickers_df.loc[ticker, 'Reason'] = "qtr_data.csv_file_either_has_no_rows_or_no_columns"
    continue
  qtr_date_list = ticker_qtr_numbers_df.columns.tolist()

  ticker_datain_yr_df.set_index("AAII_YR_DATA",inplace=True)
  logging.debug("The YR dataframe (datain_df) read from the AAII file is : \n" + ticker_datain_yr_df.to_string())
  ticker_yr_numbers_df = ticker_datain_yr_df.copy()
  if ( (len(ticker_yr_numbers_df.columns) == 0) or (len(ticker_yr_numbers_df.index) == 0) ) :
    logging.warning("The YR dataframe (datain_df) for ticker : " + str(ticker) + ", either has no rows or no columns. Skipping...")
    skipped_tickers_df.loc[ticker, 'Reason'] = "yr_data.csv_file_either_has_no_rows_or_no_columns"
    continue
  yr_date_list = ticker_yr_numbers_df.columns.tolist()

  ticker_datain_ks_df.set_index("AAII_KEY_STATISTICS_DATA",inplace=True)
  logging.debug("The Key Statistics dataframe (datain_df) read from the AAII file is : \n" + ticker_datain_ks_df.to_string())
  key_stats_datain_df = ticker_datain_ks_df.copy()
  ks_date_list = ticker_datain_ks_df.columns.tolist()
  # ---------------------------------------------------------------------------

  # ===========================================================================
  # Read the ticker AAII Key Statistics file
  # Some of the items from this file will be inserted
  # in the qtr and other in yr dataframe later.
  # The items to be inserted in qtr dataframe
  # Number of Institutions
  # Insider net purchase
  # Institutional Onwership
  # Insider Ownwership
  # The items to be inserted in yr dataframe
  # Number of Employess
  # ===========================================================================

  ks_date_list_dt = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in ks_date_list]

  logging.debug("The date list from QTR df " + str(qtr_date_list))
  logging.debug("The date list from YR df " + str(yr_date_list))
  logging.debug("The date list from Key Statistics df " + str(ks_date_list))

  # ===========================================================================
  # Process the QTR df
  # ===========================================================================

  # ---------------------------------------------------------------------------
  # Convert the numbers in the dataframe - that are in Millions/Thounsands to
  # raw numbers
  # ---------------------------------------------------------------------------
  logging.debug("\n\nQTR DF : Converting the numbers in Millions/thousands to raw numbers")
  col_list = ticker_qtr_numbers_df.columns.tolist()
  for col_idx in range(len(col_list)):
    col_val = col_list[col_idx]
    ticker_qtr_numbers_df.loc['Current_Assets', col_val] = 1000000 * (ticker_qtr_numbers_df.loc['Current_Assets', col_val])
    ticker_qtr_numbers_df.loc['Current_Liabilities', col_val] = 1000000 * (ticker_qtr_numbers_df.loc['Current_Liabilities', col_val])
    ticker_qtr_numbers_df.loc['Inventory', col_val] = 1000000 * (ticker_qtr_numbers_df.loc['Inventory', col_val])
    ticker_qtr_numbers_df.loc['LT_Debt', col_val] = 1000000 * (ticker_qtr_numbers_df.loc['LT_Debt', col_val])
    ticker_qtr_numbers_df.loc['Revenue', col_val] = 1000000 * (ticker_qtr_numbers_df.loc['Revenue', col_val])
    ticker_qtr_numbers_df.loc['Shares_Diluted', col_val] = 1000000 * (ticker_qtr_numbers_df.loc['Shares_Diluted', col_val])
    ticker_qtr_numbers_df.loc['Total_Assets', col_val] = 1000000 * (ticker_qtr_numbers_df.loc['Total_Assets', col_val])
    ticker_qtr_numbers_df.loc['Goodwill_Intangibles', col_val] = 1000000 * (ticker_qtr_numbers_df.loc['Goodwill_Intangibles', col_val])
    ticker_qtr_numbers_df.loc['Total_Liabilities', col_val] = 1000000 * (ticker_qtr_numbers_df.loc['Total_Liabilities', col_val])

  logging.debug("QTR DF : df after converting the numbers in Millions/Thousands to raw numbers \n" + ticker_qtr_numbers_df.to_string())
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Insert the dummy(NAN) rows. These rows will be populated later
  # ---------------------------------------------------------------------------
  logging.debug("\n\nQTR DF : Adding the rows that are needed to store calculated numbers")
  col_list = ticker_qtr_numbers_df.columns.tolist()
  dummy_list = []
  for col_idx in range(len(col_list)):
    dummy_list.append(float('nan'))

  ticker_qtr_numbers_df = ticker_qtr_numbers_df.append(pd.Series(dummy_list, index=ticker_qtr_numbers_df.columns, name='Current_Ratio'))
  ticker_qtr_numbers_df = ticker_qtr_numbers_df.append(pd.Series(dummy_list, index=ticker_qtr_numbers_df.columns, name='Equity'))
  ticker_qtr_numbers_df = ticker_qtr_numbers_df.append(pd.Series(dummy_list, index=ticker_qtr_numbers_df.columns, name='Net_Tangible_Assets'))
  ticker_qtr_numbers_df = ticker_qtr_numbers_df.append(pd.Series(dummy_list, index=ticker_qtr_numbers_df.columns, name='Debt_2_Equity'))
  ticker_qtr_numbers_df = ticker_qtr_numbers_df.append(pd.Series(dummy_list, index=ticker_qtr_numbers_df.columns, name='No_of_Institutions'))
  ticker_qtr_numbers_df = ticker_qtr_numbers_df.append(pd.Series(dummy_list, index=ticker_qtr_numbers_df.columns, name='Institutional_Ownership'))
  ticker_qtr_numbers_df = ticker_qtr_numbers_df.append(pd.Series(dummy_list, index=ticker_qtr_numbers_df.columns, name='Net_Insider_Purchases'))
  ticker_qtr_numbers_df = ticker_qtr_numbers_df.append(pd.Series(dummy_list, index=ticker_qtr_numbers_df.columns, name='Insider_Ownership'))
  ticker_qtr_numbers_df = ticker_qtr_numbers_df.append(pd.Series(dummy_list, index=ticker_qtr_numbers_df.columns, name='EPS_Growth'))
  ticker_qtr_numbers_df = ticker_qtr_numbers_df.append(pd.Series(dummy_list, index=ticker_qtr_numbers_df.columns, name='Revenue_Growth'))

  logging.debug("QTR DF : df after adding rows \n" + ticker_qtr_numbers_df.to_string())
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Calculate the numbers corresponding to various added rows and inserr the data
  # from Key Statistics df
  # ---------------------------------------------------------------------------
  # Watch out if the current Liabilites are 0
  logging.debug("\n\nQTR DF : 1. Calculating the various numbers and 2. Inserting the data from Key Statistics")
  logging.debug("The Key Statistics Date List is : " + str(ks_date_list))
  col_list = ticker_qtr_numbers_df.columns.tolist()
  for col_idx in range(len(col_list)):
    col_val = col_list[col_idx]
    # todo :The current ratio cannot be calcuated for companies that are in Financial Sector - Maybe put a comment in the chart
    ticker_qtr_numbers_df.loc['Current_Ratio', col_val] = ticker_qtr_numbers_df.loc['Current_Assets', col_val] / ticker_qtr_numbers_df.loc['Current_Liabilities', col_val]
    logging.debug("The Current ratio for : " + str(col_val) + ", is : " + str(ticker_qtr_numbers_df.loc['Current_Ratio', col_val]))
    ticker_qtr_numbers_df.loc['Equity', col_val] = ticker_qtr_numbers_df.loc['Total_Assets', col_val] - ticker_qtr_numbers_df.loc['Total_Liabilities', col_val]
    logging.debug("The Equity for : " + str(col_val) + ", is : " + str(ticker_qtr_numbers_df.loc['Equity', col_val]))
    ticker_qtr_numbers_df.loc['Net_Tangible_Assets', col_val] = ticker_qtr_numbers_df.loc['Total_Assets', col_val] - ticker_qtr_numbers_df.loc['Total_Liabilities', col_val] - ticker_qtr_numbers_df.loc['Goodwill_Intangibles', col_val]
    logging.debug("The Net Tangible Assets for : " + str(col_val) + ", is : " + str(ticker_qtr_numbers_df.loc['Net_Tangible_Assets', col_val]))
    ticker_qtr_numbers_df.loc['Debt_2_Equity', col_val] = 100*ticker_qtr_numbers_df.loc['LT_Debt', col_val] / ticker_qtr_numbers_df.loc['Equity', col_val]
    logging.debug("The Debt_2_Equity for : " + str(col_val) + ", is : " + str(ticker_qtr_numbers_df.loc['Debt_2_Equity', col_val]))
    # todo : test : Test if Key statistics have multiple columns
    # todo : test : Make sure that the dates from Key Statistics and qtr and yr dateframes match - this will ensure that
    # Sundeep ran the other macro right ....
    logging.debug("Checking for date : " + str(col_val) + " in the Key Statistics Date List")
    col_val_dt = dt.datetime.strptime(col_val, '%m/%d/%Y').date()
    if (col_val_dt in ks_date_list_dt):
      ks_col_val_idx = ks_date_list_dt.index(col_val_dt)
      ks_col_val = ks_date_list[ks_col_val_idx]
      logging.debug("Found " + str(col_val) + " in Key Statistics Dataframe")
      logging.debug("Inserting No_of_Institutions from Key Statistics in QTR DF")
      logging.debug("Inserting Institutional_Ownership from Key Statistics in QTR DF")
      logging.debug("Inserting Net_Insider_Purchases from Key Statistics in QTR DF")
      logging.debug("Inserting Insider_Ownership from Key Statistics in QTR DF")
      ticker_qtr_numbers_df.loc['No_of_Institutions', col_val] = key_stats_datain_df.loc['No_of_Institutions', ks_col_val]
      ticker_qtr_numbers_df.loc['Institutional_Ownership', col_val] = key_stats_datain_df.loc['Institutional_Ownership', ks_col_val]
      ticker_qtr_numbers_df.loc['Net_Insider_Purchases', col_val] = key_stats_datain_df.loc['Net_Insider_Purchases', ks_col_val]
      ticker_qtr_numbers_df.loc['Insider_Ownership', col_val] = key_stats_datain_df.loc['Insider_Ownership', ks_col_val]

  logging.debug("QTR DF : df after calculating inserted rows and inserting the data from Key Statistics DF\n" + ticker_qtr_numbers_df.to_string())

  # ---------------------------------------------------------------------------
  # Now calculate the EPS and sales grwoth and put them in just added rows
  # ---------------------------------------------------------------------------
  logging.debug("\n\nQTR DF : Calculating the Growth rates for Revenue and EPS")
  col_list = ticker_qtr_numbers_df.columns.tolist()
  # no_of_qts_to_calculate_growth_rate_for = 4
  no_of_qts_to_calculate_growth_rate_for = len(col_list) - 4
  for col_idx in range(0, no_of_qts_to_calculate_growth_rate_for):
    # Only calculate the qtrs for which the back data is available...this will get better are more date becomes available.
    if (col_idx+4 <= len(col_list)-1):
      col_val = col_list[col_idx]
      col_val_same_qtr_last_year = col_list[col_idx+4]
      logging.debug("The col_idx is " + str(col_idx) + " and the value is " + col_val)
      eps_this_qtr = ticker_qtr_numbers_df.loc['Diluted_EPS', col_val]
      eps_same_qtr_last_year = ticker_qtr_numbers_df.loc['Diluted_EPS', col_val_same_qtr_last_year]
      # if eps last year was negative then don't do anything as that grwoth rate cannot be calculated
      if (eps_same_qtr_last_year > 0):
        ticker_qtr_numbers_df.loc['EPS_Growth', col_val] = 100*((eps_this_qtr/eps_same_qtr_last_year)-1)

      ticker_qtr_numbers_df.loc['Revenue_Growth', col_val] = 100*((ticker_qtr_numbers_df.loc['Revenue', col_val]/ticker_qtr_numbers_df.loc['Revenue', col_val_same_qtr_last_year])-1)
  logging.debug("QTR DF : df after calculating growth rates for Revenue and EPS  \n" + ticker_qtr_numbers_df.to_string())
  # ---------------------------------------------------------------------------
  # ===========================================================================


  # ===========================================================================
  # Process the YR df
  # ===========================================================================
  logging.debug("=======================================")
  logging.info("Starting to process YR data")
  logging.debug("=======================================")
  ticker_datain_yr_file = ticker +  "_yr_data.csv"
  ticker_datain_yr_df = pd.read_csv(dir_path + analysis_dir + "\\" + "Yearly" + "\\" + ticker_datain_yr_file)
  ticker_datain_yr_df.set_index("AAII_YR_DATA",inplace=True)
  logging.debug("\n\nYR DF : df read from the AAII file is : \n" + ticker_datain_yr_df.to_string())

  # ---------------------------------------------------------------------------
  # Copy Yearly numbers dataframe (todo : Do we really need a copy?)
  # ---------------------------------------------------------------------------
  ticker_yr_numbers_df = ticker_datain_yr_df.copy()
  logging.debug("\n\nYR DF : df after copying over after reading from the ticker file copying over to yr_numbers_df (should be same as read from AAII file) \n" + ticker_yr_numbers_df.to_string())

  # These rows are not needed / Remove the unwanted rows (Not really needed but do it for now)
  # ticker_yr_numbers_df.drop(index= ['Current_Assets'], inplace=True)
  # ticker_yr_numbers_df.drop(index= ['Short_Term_Debt'], inplace=True)
  # The rearragne to row to your liking : This works
  # ticker_yr_numbers_df = ticker_yr_numbers_df.loc[['Revenue', 'Diluted_EPS', 'BV_Per_Share', 'LT_Debt'], :]

  # ---------------------------------------------------------------------------
  # Limit the number of columns to display - say 10 years...Make it user controlled
  # ---------------------------------------------------------------------------
  number_of_years_to_display = 10
  logging.debug("\n\nYR DF : Truncating the df to only have : " + str(number_of_years_to_display) + " years of data")
  tmp_df = ticker_yr_numbers_df.iloc[:, : number_of_years_to_display]
  ticker_yr_numbers_df = tmp_df.copy()
  tmp_df = pd.DataFrame()
  logging.debug("YR DF : df after being truncated to : " + str(number_of_years_to_display) + " is \n" + ticker_yr_numbers_df.to_string())
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Reverse the columns in dataframe - This makes the growth rate calculation loop simpler
  # ---------------------------------------------------------------------------
  logging.debug("\n\nYR DF : Reversing the df as this makes the growth rate calculation easier for YR")
  # This works : This reverses the dataframe by columns - Both of these work
  # tmp_df = ticker_yr_numbers_df[ticker_yr_numbers_df.columns[::-1]]
  tmp_df = ticker_yr_numbers_df.iloc[:, ::-1]
  ticker_yr_numbers_df = tmp_df.copy()
  logging.debug("YR DF :  df after being reversed is \n" + ticker_yr_numbers_df.to_string())
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Convert the numbers in the dataframe - that are in Millions/Thounsands to
  # raw numbers
  # ---------------------------------------------------------------------------
  logging.debug("\n\nYR DF : Converting the numbers in Millions/thousands to raw numbers")
  col_list = ticker_yr_numbers_df.columns.tolist()
  for col_idx in range(len(col_list)):
    col_val = col_list[col_idx]
    ticker_yr_numbers_df.loc['Capital_Expenditures', col_val] = 1000000 * (ticker_datain_yr_df.loc['Capital_Expenditures', col_val])
    ticker_yr_numbers_df.loc['Cash_from_Operations', col_val] = 1000000 * (ticker_datain_yr_df.loc['Cash_from_Operations', col_val])
    ticker_yr_numbers_df.loc['LT_Debt', col_val] = 1000000 * (ticker_datain_yr_df.loc['LT_Debt', col_val])
    ticker_yr_numbers_df.loc['Net_Income', col_val] = 1000000 * (ticker_datain_yr_df.loc['Net_Income', col_val])
    ticker_yr_numbers_df.loc['Revenue', col_val] = 1000000 * (ticker_datain_yr_df.loc['Revenue', col_val])
    ticker_yr_numbers_df.loc['Shares_Diluted', col_val] = 1000000 * (ticker_datain_yr_df.loc['Shares_Diluted', col_val])
    ticker_yr_numbers_df.loc['Total_Assets', col_val] = 1000000 * (ticker_datain_yr_df.loc['Total_Assets', col_val])
    ticker_yr_numbers_df.loc['Goodwill_Intangibles', col_val] = 1000000 * (ticker_datain_yr_df.loc['Goodwill_Intangibles', col_val])
    ticker_yr_numbers_df.loc['Total_Liabilities', col_val] = 1000000 * (ticker_datain_yr_df.loc['Total_Liabilities', col_val])

  logging.debug("The ticker yr dataframe after converting the numbers to raw numbers \n" + ticker_yr_numbers_df.to_string())
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Now add dummy (NaN) rows that are needed for the chart/table
  # ---------------------------------------------------------------------------
  logging.debug("\n\nYR DF : Adding dummy(NaN) rows that are needed to store calculated numbers")
  dummy_list =[]
  col_list = ticker_yr_numbers_df.columns.tolist()
  for col_idx in range(len(col_list)):
    col_val = col_list[col_idx]
    dummy_list.append(float('nan'))

  # Add the rows for -- These will be populated later
  ticker_yr_numbers_df = ticker_yr_numbers_df.append(pd.Series(dummy_list, index=ticker_yr_numbers_df.columns, name='BV_Per_Share'))
  ticker_yr_numbers_df = ticker_yr_numbers_df.append(pd.Series(dummy_list, index=ticker_yr_numbers_df.columns, name='NTA_Per_Share'))
  ticker_yr_numbers_df = ticker_yr_numbers_df.append(pd.Series(dummy_list, index=ticker_yr_numbers_df.columns, name='FCF_Per_Share'))
  ticker_yr_numbers_df = ticker_yr_numbers_df.append(pd.Series(dummy_list, index=ticker_yr_numbers_df.columns, name='ROE'))
  ticker_yr_numbers_df = ticker_yr_numbers_df.append(pd.Series(dummy_list, index=ticker_yr_numbers_df.columns, name='ROIC'))
  ticker_yr_numbers_df = ticker_yr_numbers_df.append(pd.Series(dummy_list, index=ticker_yr_numbers_df.columns, name='Revenue_Growth'))
  ticker_yr_numbers_df = ticker_yr_numbers_df.append(pd.Series(dummy_list, index=ticker_yr_numbers_df.columns, name='Diluted_EPS_Growth'))
  ticker_yr_numbers_df = ticker_yr_numbers_df.append(pd.Series(dummy_list, index=ticker_yr_numbers_df.columns, name='BV_Per_Share_Growth'))
  ticker_yr_numbers_df = ticker_yr_numbers_df.append(pd.Series(dummy_list, index=ticker_yr_numbers_df.columns, name='NTA_Per_Share_Growth'))
  ticker_yr_numbers_df = ticker_yr_numbers_df.append(pd.Series(dummy_list, index=ticker_yr_numbers_df.columns, name='FCF_Per_Share_Growth'))
  ticker_yr_numbers_df = ticker_yr_numbers_df.append(pd.Series(dummy_list, index=ticker_yr_numbers_df.columns, name='No_of_Employees'))
  logging.debug("YR DF : df after adding dummy(NaN) rows that are needed to store calculated numbers \n" + ticker_yr_numbers_df.to_string())
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Insert the base growth rate rows - These are use in the growth rate chart
  # ---------------------------------------------------------------------------
  logging.debug("\n\nYR DF : Inserting base growth Rate rows")
  # Create a bsee growth row
  base_growth_rate_percent_10 = .1
  base_growth_rate_percent_20 = .2
  base_growth_10_percent_list = []
  base_growth_20_percent_list = []
  col_list = ticker_yr_numbers_df.columns.tolist()
  for col_idx in range(len(col_list)):
    col_val = col_list[col_idx]
    base_growth_10_percent_list.append(float('nan'))
    base_growth_20_percent_list.append(float('nan'))
    if (col_idx == 0):
      base_growth_10_percent_list[col_idx] = 1
      base_growth_20_percent_list[col_idx] = 1
    else:
      base_growth_10_percent_list[col_idx] = base_growth_10_percent_list[col_idx-1]*(1+base_growth_rate_percent_10)
      base_growth_20_percent_list[col_idx] = base_growth_20_percent_list[col_idx-1]*(1+base_growth_rate_percent_20)

  # Thiw works - Reverse the list
  # base_growth_10_percent_list = base_growth_10_percent_list[::-1]
  logging.debug("The base growth 10% list is " + str(base_growth_10_percent_list))
  logging.debug("The base growth 20% list is " + str(base_growth_20_percent_list))
  ticker_yr_numbers_df = ticker_yr_numbers_df.append(pd.Series(base_growth_10_percent_list, index=ticker_yr_numbers_df.columns, name='Base_Growth_10'))
  ticker_yr_numbers_df = ticker_yr_numbers_df.append(pd.Series(base_growth_20_percent_list, index=ticker_yr_numbers_df.columns, name='Base_Growth_20'))

  logging.debug("YR DF : df after adding base growth rate rows needed for furthur calculations is: \n" + ticker_yr_numbers_df.to_string())
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Calculate various numbers and also insert the data from key Statistics df
  # Insert the growth rates for Revenue, Diluted_EPS, BVPS and FCFPS
  # ---------------------------------------------------------------------------
  logging.debug("\n\nYR DF : Calculating various numbers like BVPS, ROE, FCFPS etc and growth rates for Revenue, Diluted_EPS, NTAPS, BVPS and FCFS")
  col_list = ticker_yr_numbers_df.columns.tolist()
  for col_idx in range(len(col_list)):
    col_val = col_list[col_idx]
    ticker_yr_numbers_df.loc['BV_Per_Share', col_val] = (ticker_yr_numbers_df.loc['Total_Assets', col_val]-ticker_yr_numbers_df.loc['Total_Liabilities', col_val])/ticker_yr_numbers_df.loc['Shares_Diluted', col_val]
    ticker_yr_numbers_df.loc['NTA_Per_Share', col_val] = (ticker_yr_numbers_df.loc['Total_Assets', col_val]-ticker_yr_numbers_df.loc['Total_Liabilities', col_val]-ticker_yr_numbers_df.loc['Goodwill_Intangibles', col_val])/ticker_yr_numbers_df.loc['Shares_Diluted', col_val]
    ticker_yr_numbers_df.loc['FCF_Per_Share', col_val] = (ticker_yr_numbers_df.loc['Cash_from_Operations', col_val]-ticker_yr_numbers_df.loc['Capital_Expenditures', col_val])/ticker_yr_numbers_df.loc['Shares_Diluted', col_val]
    ticker_yr_numbers_df.loc['ROE', col_val] = 100*ticker_yr_numbers_df.loc['Net_Income', col_val]/(ticker_yr_numbers_df.loc['Total_Assets', col_val]-ticker_yr_numbers_df.loc['Total_Liabilities', col_val])
    ticker_yr_numbers_df.loc['ROIC', col_val] = 100*ticker_yr_numbers_df.loc['Net_Income', col_val]/(ticker_yr_numbers_df.loc['Total_Assets', col_val]-ticker_yr_numbers_df.loc['Total_Liabilities', col_val]+ticker_yr_numbers_df.loc['LT_Debt', col_val])
    if (col_idx == 0):
      ticker_yr_numbers_df.loc['Revenue_Growth', col_val] = 1
      ticker_yr_numbers_df.loc['Diluted_EPS_Growth', col_val] = 1
      ticker_yr_numbers_df.loc['BV_Per_Share_Growth', col_val] = 1
      ticker_yr_numbers_df.loc['NTA_Per_Share_Growth', col_val] = 1
      ticker_yr_numbers_df.loc['FCF_Per_Share_Growth', col_val] = 1
    else:
      # todo : What if the col_val_starting is NaN? That can happen as we add more stuff
      col_val_starting = col_list[0]
      if (str(ticker_yr_numbers_df.loc['NTA_Per_Share', col_val_starting]) == 'nan'):
        logging.error("Yearly Numbers : The NTA_Per_Share is NaN for date : " + str(col_val_starting))
        ticker_yr_numbers_df.loc['NTA_Per_Share', col_val_starting] = ticker_yr_numbers_df.loc['NTA_Per_Share', col_list[1]]
        # sys.exit(1)
      logging.debug("Calculating Revenue Growth")
      ticker_yr_numbers_df.loc['Revenue_Growth', col_val] = get_ratio(ticker_yr_numbers_df.loc['Revenue', col_val],ticker_yr_numbers_df.loc['Revenue', col_val_starting])
      logging.debug("Calculating EPS Growth")
      ticker_yr_numbers_df.loc['Diluted_EPS_Growth', col_val] = get_ratio(ticker_yr_numbers_df.loc['Diluted_EPS', col_val],ticker_yr_numbers_df.loc['Diluted_EPS', col_val_starting])
      logging.debug("Calculating NTA_Per_Share Growth")
      ticker_yr_numbers_df.loc['NTA_Per_Share_Growth', col_val] = get_ratio(ticker_yr_numbers_df.loc['NTA_Per_Share', col_val],ticker_yr_numbers_df.loc['NTA_Per_Share', col_val_starting])
      logging.debug("Calculating BV_Per_Share Growth")
      ticker_yr_numbers_df.loc['BV_Per_Share_Growth', col_val] = get_ratio(ticker_yr_numbers_df.loc['BV_Per_Share', col_val],ticker_yr_numbers_df.loc['BV_Per_Share', col_val_starting])
      logging.debug("Calculating FCF_Per_Share Growth")
      ticker_yr_numbers_df.loc['FCF_Per_Share_Growth', col_val] = get_ratio(ticker_yr_numbers_df.loc['FCF_Per_Share', col_val],ticker_yr_numbers_df.loc['FCF_Per_Share', col_val_starting])

    col_val_dt = dt.datetime.strptime(col_val, '%m/%d/%Y').date()
    if (col_val_dt in ks_date_list_dt):
      ks_col_val_idx = ks_date_list_dt.index(col_val_dt)
      ks_col_val = ks_date_list[ks_col_val_idx]
      logging.debug("Found " + str(col_val) + " in Key Statistics Dataframe")
      logging.debug("Inserting No_of_Employees from Key Statistics in YR DF")
      ticker_yr_numbers_df.loc['No_of_Employees', col_val] = key_stats_datain_df.loc['No_of_Employees', ks_col_val]

  # ---------------------------------------------------------------------------
  # Check the growth numbers for Revenue and Diluted EPS and see if both fo them
  # are greater than 10% per annum growth and if so, then add it to the dataframe
  # that lists the eligible growth
  # ---------------------------------------------------------------------------
  col_list = ticker_yr_numbers_df.columns.tolist()
  number_of_years_data_available = len(col_list)
  last_col_val = col_list[len(col_list)-1]
  rev_growth_cummulative =  ticker_yr_numbers_df.loc['Revenue_Growth', last_col_val]
  eps_growth_cummulative =  ticker_yr_numbers_df.loc['Diluted_EPS_Growth', last_col_val]
  bvps_growth_cummulative =  ticker_yr_numbers_df.loc['BV_Per_Share_Growth', last_col_val]
  fcfps_growth_cummulative =  ticker_yr_numbers_df.loc['FCF_Per_Share_Growth', last_col_val]
  base_growth_cummulative = ticker_yr_numbers_df.loc['Base_Growth_10', last_col_val]

  rev_last_col_val = ticker_yr_numbers_df.loc['Revenue', last_col_val]
  eps_last_col_val = ticker_yr_numbers_df.loc['Diluted_EPS', last_col_val]
  bvps_last_col_val = ticker_yr_numbers_df.loc['BV_Per_Share', last_col_val]
  fcfps_last_col_val = ticker_yr_numbers_df.loc['FCF_Per_Share', last_col_val]

  logging.debug("The Cummulative Revenue growth has been : " + str(rev_growth_cummulative))
  logging.debug("The Cummulative EPS     growth has been : " + str(eps_growth_cummulative))
  logging.debug("The Cummulative BVPS    growth has been : " + str(bvps_growth_cummulative))
  logging.debug("The Cummulative FCFPS   growth has been : " + str(fcfps_growth_cummulative))
  logging.debug("The Cummulative Base    growth has been : " + str(base_growth_cummulative))

  if ((rev_growth_cummulative >= 1) and
      (eps_growth_cummulative >= 1) and
      (bvps_growth_cummulative >= 1) and
      (fcfps_growth_cummulative >= 1)):
    are_all_growths_numbers_positive = 1
  else:
    are_all_growths_numbers_positive = 0

  # All the 4 numbers last year are positive
  if ((rev_last_col_val >= 0) and
      (eps_last_col_val >= 0) and
      (bvps_last_col_val >= 0) and
      (fcfps_last_col_val >= 0)):
    all_4_numbers_last_col_non_negative = 1
  else:
    all_4_numbers_last_col_non_negative = 0

  if (ticker in master_tracklist_list):
    ticker_in_master_tracklist = 'Y'
  else:
    ticker_in_master_tracklist = 'N'

  is_rev_growth_gt_base = False
  is_eps_growth_gt_base = False
  is_bvps_growth_gt_base = False
  is_fcfps_growth_gt_base = False

  is_rev_growth_gt_base = (rev_growth_cummulative >= base_growth_cummulative)
  is_eps_growth_gt_base = (eps_growth_cummulative >= base_growth_cummulative)
  is_bvps_growth_gt_base = (bvps_growth_cummulative >= base_growth_cummulative)
  is_fcfps_growth_gt_base = (fcfps_growth_cummulative >= base_growth_cummulative)

  logging.debug("")
  logging.debug("Is Cummulative Revenue growth greater than Base growth : " + str(is_rev_growth_gt_base))
  logging.debug("Is Cummulative EPS     growth greater than Base growth : " + str(is_eps_growth_gt_base))
  logging.debug("Is Cummulative BVPS    growth greater than Base growth : " + str(is_bvps_growth_gt_base))
  logging.debug("Is Cummulative FCFPS   growth greater than Base growth : " + str(is_fcfps_growth_gt_base))

  is_rev_growth_gt_base = int(is_rev_growth_gt_base)
  is_eps_growth_gt_base = int(is_eps_growth_gt_base)
  is_bvps_growth_gt_base = int(is_bvps_growth_gt_base)
  is_fcfps_growth_gt_base = int(is_fcfps_growth_gt_base)


  no_of_growth_rates_gt_base_growth = is_rev_growth_gt_base + is_eps_growth_gt_base + is_bvps_growth_gt_base + is_fcfps_growth_gt_base
  # If all the growth rates are positive and greater than one (which means that the respective metric is growting) and
  # If atleast two growth reates are greater than base growth and
  # both the first and last numbers are either positive
  this_ticker_qualifies_in_watchlist = 0
  if ((number_of_years_data_available >= 3) and (all_4_numbers_last_col_non_negative == 1) and (are_all_growths_numbers_positive == 1) and (no_of_growth_rates_gt_base_growth >= 2)):
    logging.debug("Ticker : " + str(ticker) + ", has YR data available for : " + str(number_of_years_data_available))
    logging.debug("Ticker : " + str(ticker) + ", has all 4 numbers gt 0")
    logging.debug("Ticker : " + str(ticker) + ", has all growth numbers gt 1")
    logging.debug("Ticker : " + str(ticker) + ", has atleast 2 growth rates greater than base growth rate")
    watchlist_0analysis_df.loc[ticker,'Rev_growth'] = rev_growth_cummulative
    watchlist_0analysis_df.loc[ticker, 'EPS_growth'] = eps_growth_cummulative
    watchlist_0analysis_df.loc[ticker, 'BVPS_growth'] = bvps_growth_cummulative
    watchlist_0analysis_df.loc[ticker, 'FCFPS_growth'] = fcfps_growth_cummulative
    watchlist_0analysis_df.loc[ticker, 'No_of_Years'] = number_of_years_data_available
    watchlist_0analysis_df.loc[ticker, 'In_Master'] = ticker_in_master_tracklist
    watchlist_0analysis_df.loc[ticker, 'Revs'] = human_format(rev_last_col_val)
    watchlist_0analysis_df.loc[ticker, 'EPS'] = round(eps_last_col_val,2)
    watchlist_0analysis_df.loc[ticker, 'BVPS'] = round(bvps_last_col_val,2)
    watchlist_0analysis_df.loc[ticker, 'FCFPS'] = round(fcfps_last_col_val,2)
    this_ticker_qualifies_in_watchlist = 1
  # ---------------------------------------------------------------------------

  logging.debug("YR Dataframe after calculating numbers for various rows and inserting the data from Key Statistics DF and after adding actual growth rates for Revenue, Diluted_EPS, BVPS and FCFS is\n" + ticker_yr_numbers_df.to_string())
  # ---------------------------------------------------------------------------
  # This works - if you want to rearrange the rows of the dataframe in certain order
  # ticker_yr_numbers_df = ticker_yr_numbers_df.loc[['Base_Growth_10', 'Base_Growth_10','Revenue_Growth', 'Diluted_EPS_Growth', 'BV_Per_Share_Growth'], :]
  # ===========================================================================

  # ===========================================================================
  # Prepare the Key Statistics Dataframe
  # Right now all the information for Key Stats comes from qtr df
  # ===========================================================================
  logging.debug("=======================================")
  logging.info("Staring to work on Key Statistics df")
  logging.debug("=======================================")
  key_stats_01_df = pd.DataFrame(columns=['key_stats_01_df'])
  key_stats_01_df.set_index("key_stats_01_df",inplace=True)
  col_list = ticker_qtr_numbers_df.columns.tolist()
  no_of_cols_to_put_in_key_stats = 5
  # If there are fewer than 5 cols in the qtr df -
  #   then copy the data from all all the cols into key stats df
  #   otherwise copy the data from only first 5 cols
  if (len(col_list) < no_of_cols_to_put_in_key_stats):
    no_of_cols_to_put_in_key_stats = len(col_list)
  logging.debug("\n\nKey Stats 01 DF : Populate Keys Statistics numbers from qtr df cols : " + str(col_list))
  # todo : What if the number of cols are less than 8
  for col_idx in range(no_of_cols_to_put_in_key_stats):
    col_val = col_list[col_idx]
    key_stats_01_df.loc['Curr. Ratio',col_val] = ticker_qtr_numbers_df.loc['Current_Ratio',col_val]
    key_stats_01_df.loc['Inventory',col_val] = ticker_qtr_numbers_df.loc['Inventory',col_val]
    key_stats_01_df.loc['LT_Debt',col_val] = ticker_qtr_numbers_df.loc['LT_Debt',col_val]
    key_stats_01_df.loc['Equity',col_val] = ticker_qtr_numbers_df.loc['Equity',col_val]
    key_stats_01_df.loc['Debt/Equity',col_val] = ticker_qtr_numbers_df.loc['Debt_2_Equity',col_val]
    key_stats_01_df.loc['# of Shares',col_val] = ticker_qtr_numbers_df.loc['Shares_Diluted',col_val]
    key_stats_01_df.loc['Institutions',col_val] =ticker_qtr_numbers_df.loc['No_of_Institutions',col_val]

  logging.debug("Key Stats 01 DF : df after inserting from qtr dataframe \n" + key_stats_01_df.to_string())
  # ---------------------------------------------------------------------------
  # ===========================================================================



  # ===========================================================================
  # Price  -- Done
  # most_recent_quarter -- Done
  # mrq_quick_ratio (Cash and liabilities in Q)
  # mrq_current_ratio (Current Assets and Liabilities in Q)
  # mrq_current_liabilities (in Q)
  # mrq_equity (Total Assets and Liabilites in Q)
  # mrq_lt_debt (LT debt in Q)
  # mrq_lt_debt_over_equity
  # mrq_shares_outstanding (Shares Diluted in Q)
  # expected_growth (next 3 years/ 5 years) [Maybe in Misc Tab in AAII]
  # TTM Sales (to generate P/S) -- Do we need this
  # TTM Book  (to generate P/B)

  # Extract the numbers that are needed for Key Statistics
  # Current Ratio
  # Debt to Equity

  # Read the historical to get the latest Price -
  # todo - Can get the latest price from the yahoo financials as well
  # historical_df = pd.read_csv(dir_path + "\\" + historical_dir + "\\" + ticker + "_historical.csv")
  # ticker_adj_close_list = historical_df.Adj_Close.tolist()
  # date_str_list = historical_df.Date.tolist()
  # date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in date_str_list]
  # ticker_curr_price = next(x for x in ticker_adj_close_list if not math.isnan(x))
  # ticker_curr_date = date_list[ticker_adj_close_list.index(ticker_curr_price)]
  # # Now round the ticker_curr_price to 2 decimal places
  # round(ticker_curr_price, 2)
  # logging.debug("The most recent price for " + str(ticker) + " is : " + str(ticker_curr_price) + " for date " + str(ticker_curr_date))
  #
  # Get the most recent quarter date
  ticker_company_name = "#NA#"
  ticker_sector = "#NA#"
  ticker_industry = "#NA#"
  chart_update_date_str = "#NA#"
  if (yahoo_comany_info_df.index.isin([(ticker)]).any()):
    # This works - get the value in the column corresponding to the index
    ticker_company_name = yahoo_comany_info_df.loc[ticker, 'Company_Name']
    ticker_sector = yahoo_comany_info_df.loc[ticker, 'Sector']
    ticker_industry = yahoo_comany_info_df.loc[ticker, 'Industry']

  # ===========================================================================




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
  if (g_var_plot_en == 1):
    logging.debug("=========================================================")
    logging.info("Starting to plot the data now...")
    logging.debug("=========================================================")
    fig = plt.figure()
    fig.set_size_inches(14.431, 7.639)  # Length x height
    # This sets the background color of the whole figure
    fig.patch.set_facecolor('#E0E0E0')
    fig.patch.set_alpha(0.7)

    qtr_table_plt = plt.subplot2grid((6, 6), (0, 0), rowspan=2,colspan=3)
    yr_growth_plt = plt.subplot2grid((6, 6), (0, 3), rowspan=4,colspan=3)
    key_numbers_plt = plt.subplot2grid((6, 6), (2, 0), rowspan=2, colspan=3)
    yr_table_plt = plt.subplot2grid((6, 6), (4, 0), rowspan=2, colspan=6)
    plt.subplots_adjust(hspace=.1, wspace=.15)
    # fig.suptitle(ticker_company_name + "(" + ticker + ")")
    plt.text(x=0.6, y=0.95, s=ticker_company_name + "(" + ticker + ")", fontsize=14, fontweight='bold', ha="left",transform=fig.transFigure)
    plt.text(x=0.6, y=0.93, s=ticker_sector + " - " + ticker_industry  , fontsize=11, fontweight='bold', ha="left",fontstyle='italic', transform=fig.transFigure)
    # ===========================================================================


    # ===========================================================================
    # Plot the Quarterly Table
    # ===========================================================================
    qtr_table_plt.title.set_text("Quarterly Numbers")
    qtr_table_plt.set_yticks([])
    qtr_table_plt.set_xticks([])

    # Extract the desired rows out of the dataframe in tmp_df
    tmp_df  = pd.DataFrame()
    desired_indices = ['Revenue','Revenue_Growth','Diluted_EPS','EPS_Growth']
    tmp_df = ticker_qtr_numbers_df.loc[desired_indices]
    logging.debug("The QTR df with only desired indices extracted out : \n" + tmp_df.to_string())

    # Now keep only the first 4 columns of the dataframe as these are the date that we want to display - this can get
    # exteneded if user desires later on..
    tmp_df_1 = tmp_df.iloc[:, : 8]
    logging.debug("The QTR df with only first 4 quarters of data  \n" + tmp_df_1.to_string())

    # Now reverse the dataframe - so that the older dates are first in the column
    tmp_df_2 = tmp_df_1.iloc[:, ::-1]
    logging.debug("The QTR df with only first 4 quarters of data now reversed  \n" + tmp_df_2.to_string())
    # Finally transpose  the  dataframe so that it can be displayed vertically
    tmp_df = tmp_df_2.transpose().copy()
    logging.debug("The QTR df with only first 4 quarters of data reversed and now transposed \n" + tmp_df.to_string())

    # Now plot the dataframe
    # qtr_table_plt_inst = qtr_table_plt.table(cellText=tmp_df.values, rowLabels=tmp_df.index,colWidths=[0.1] * len(tmp_df.columns),colLabels=tmp_df.columns,loc="upper center")
    qtr_table_plt_inst = qtr_table_plt.table(cellText=tmp_df.values, rowLabels=tmp_df.index,colLabels=tmp_df.columns,loc="upper center")

    # iterate through the table and set the fonts etc to desired values
    logging.debug("Iterating through the QTR table to reformat for the text etc...")
    eps_col_idx = tmp_df.columns.get_loc("Diluted_EPS")
    eps_growth_col_idx = tmp_df.columns.get_loc("EPS_Growth")
    revenue_col_idx = tmp_df.columns.get_loc("Revenue")
    revenue_growth_col_idx = tmp_df.columns.get_loc("Revenue_Growth")
    logging.debug("The column index for EPS_Growth is " + str(eps_growth_col_idx))
    logging.debug("The column index for Revenue_Growth is " + str(revenue_growth_col_idx))
    # The column header starts with (0, 0)...(0, n - 1).The row header starts with (1, -1)...(n, -1)
    for key, cell in qtr_table_plt_inst.get_celld().items():
      row_idx = key[0]
      col_idx = key[1]
      cell_val = cell.get_text().get_text()
      logging.debug("Row idx " + str(row_idx) + " Col idx " + str(col_idx) + " Value " + str(cell_val))

      # -----------------------------------------------------
      # Set the row headers and columns to bold
      # -----------------------------------------------------
      if ((row_idx == 0) or (col_idx < 0)):
        cell.get_text().set_fontweight('bold')
      # -----------------------------------------------------

      # -----------------------------------------------------
      # Set the colors every alternating rows
      # -----------------------------------------------------
      if (row_idx % 2 == 0):
        qtr_table_plt_inst[(row_idx, col_idx)].set_facecolor('seashell')
      else:
        qtr_table_plt_inst[(row_idx, col_idx)].set_facecolor('azure')
      # -----------------------------------------------------

      # -----------------------------------------------------
      # Change the Date format to be shorter
      # -----------------------------------------------------
      if (col_idx == -1):
        x_date = dt.datetime.strptime(cell_val,'%m/%d/%Y').date()
        x = dt.datetime.strftime(x_date, '%b-%y')
        logging.debug("The date is " + str(x))
        cell.get_text().set_text(x)
      # -----------------------------------------------------

      # -----------------------------------------------------
      # Change the heading of the various row according to the liking of the user
      # -----------------------------------------------------
      if (row_idx == 0):
        if (col_idx == revenue_col_idx):
          x = "Rev #"
        if (col_idx == revenue_growth_col_idx):
          x = "Rev %"
        if (col_idx == eps_col_idx):
          x = "EPS #"
          cell.get_text().set_text(x)
        if (col_idx == eps_growth_col_idx):
          x = "EPS %"
        cell.get_text().set_text(x)
      # -----------------------------------------------------

      # -----------------------------------------------------
      # Append "%" to the EPS and revenue change numbers
      # -----------------------------------------------------
      if (((col_idx == eps_growth_col_idx) or (col_idx == revenue_growth_col_idx)) and (row_idx > 0)):
        if (cell_val == 'nan'):
          x = "-"
          cell.get_text().set_text(x)
        else:
          if float(cell_val) < 0:
            cell.get_text().set_color('Red')
            cell.get_text().set_fontstyle('italic')
            qtr_table_plt_inst[(row_idx, col_idx)].set_facecolor('lightpink')
          x =  f'{float(cell.get_text().get_text()):.1f}'
          x = x + "%"
          cell.get_text().set_text(x)
        # if (row_idx == current_assets_row_idx):
        #   x = f'{int(float(cell_val)):,}'
          # This works - for now comment out as I try to think whether to have % here or not
          # if (row_idx == revenue_row_idx):
            # x = x + "%"
      # -----------------------------------------------------

      # -----------------------------------------------------
      # -----------------------------------------------------
      # -----------------------------------------------------
      if ((col_idx == revenue_col_idx) and (row_idx > 0 ) and (col_idx > -1)):
        if (cell_val == 'nan'):
          x = "-"
          cell.get_text().set_text(x)
        else:
          x_int = int(float(cell_val))
          x = human_format(x_int)
          cell.get_text().set_text(x)
      if ((col_idx == eps_col_idx) and (row_idx > 0 ) and (col_idx > -1)):
        if (cell_val == 'nan'):
          x = "-"
          cell.get_text().set_text(x)
        else:
          if float(cell_val) < 0:
            cell.get_text().set_color('Red')
            cell.get_text().set_fontstyle('italic')
            qtr_table_plt_inst[(row_idx, col_idx)].set_facecolor('lightpink')
          x =  f'{float(cell.get_text().get_text()):.2f}'
          cell.get_text().set_text(x)
          cell.get_text().set_text(x)
        # -----------------------------------------------------
        # else:
        #   x =  f'{float(cell.get_text().get_text()):.2f}'
    qtr_table_plt.axis('off')
    logging.info("Done with plotting QTR table...")
    # ===========================================================================


    # ===========================================================================
    # Plot the Key Numbers table
    # ===========================================================================
    logging.debug("Starting to plot Key Statistics Table 01")
    logging.debug("\n\nKey Stats 01 DF : Reversing the Key Stats df")
    tmp_df = key_stats_01_df.iloc[:, ::-1]
    key_stats_01_df = tmp_df.copy()
    logging.debug("\n\nKey Stats 01 DF : Key Stats df after reversing is \n" + key_stats_01_df.to_string())
    key_numbers_plt.title.set_text("Key Numbers")
    key_numbers_plt.set_facecolor("lightgrey")
    key_numbers_plt.set_yticks([])
    key_numbers_plt.set_xticks([])
    # key_numbers_plt_inst = key_numbers_plt.table(cellText=[[1,5,9], [2,4,8]], rowLabels=['row1', 'row2'], colLabels=['col1', 'col2','col3'],loc="upper center")
    key_numbers_plt_inst = key_numbers_plt.table(cellText=key_stats_01_df.values, rowLabels=key_stats_01_df.index,colLabels=key_stats_01_df.columns,loc="upper center")
    key_numbers_plt_inst[(1,0)].set_facecolor("#56b5fd")
    key_numbers_plt.axis('off')

    # Get the row numbers for various row headings (indices).
    # These can be used later to format the data in the respective rows
    curr_ratio_row_idx =  key_stats_01_df.index.get_loc('Curr. Ratio') + 1
    inventory_row_idx =  key_stats_01_df.index.get_loc('Inventory') + 1
    lt_debt_row_idx =  key_stats_01_df.index.get_loc('LT_Debt') + 1
    equity_row_idx =  key_stats_01_df.index.get_loc('Equity') + 1
    shares_outstanding_row_idx =  key_stats_01_df.index.get_loc('# of Shares') + 1
    debt_2_equity_row_idx =  key_stats_01_df.index.get_loc('Debt/Equity') + 1
    institutions_row_idx = key_stats_01_df.index.get_loc('Institutions') + 1
    # The column header starts with (0, 0)...(0, n - 1).The row header starts with (1, -1)...(n, -1)
    for key, cell in key_numbers_plt_inst.get_celld().items():
      row_idx = key[0]
      col_idx = key[1]
      cell_val = cell.get_text().get_text()
      logging.debug("Row idx " + str(row_idx) + " Col idx " + str(col_idx) + " Value " + str(cell_val))

      # Alternate the colors on the rows
      if (row_idx % 2 == 0):
        key_numbers_plt_inst[(row_idx, col_idx)].set_facecolor('seashell')
      else:
        key_numbers_plt_inst[(row_idx, col_idx)].set_facecolor('azure')

      # Change the Date format to be shorter
      if (row_idx == 0):
        x_date = dt.datetime.strptime(cell_val,'%m/%d/%Y').date()
        x = dt.datetime.strftime(x_date, '%b-%y')
        logging.debug("The date is " + str(x))
        cell.get_text().set_text(x)
      # -----------------------------------------------------
      # Set bold the header row and index column
      if ((row_idx == 0) or (col_idx < 0)):
        cell.get_text().set_fontweight('bold')
      elif (cell_val == 'nan'):
        x = "-"
        cell.get_text().set_text(x)
      else:
        if float(cell_val) < 0:
          cell.get_text().set_color('Red')
          cell.get_text().set_fontstyle('italic')
          key_numbers_plt_inst[(row_idx, col_idx)].set_facecolor('lightpink')

        if ((row_idx == inventory_row_idx) or (row_idx == lt_debt_row_idx) or (row_idx == equity_row_idx) or (row_idx == shares_outstanding_row_idx)):
          x_int = int(float(cell_val))
          x = human_format(x_int)
        elif (row_idx == institutions_row_idx):
          x = int(float(cell_val))
        elif (row_idx == debt_2_equity_row_idx):
          x =  f'{float(cell.get_text().get_text()):.2f}'
          x = x + "%"
        else:
          x =  f'{float(cell.get_text().get_text()):.2f}'

        cell.get_text().set_text(x)


    key_numbers_plt.axis('off')
    logging.info("Done with plotting Key Statistics table 01...")
    # ===========================================================================


    # ===========================================================================
    # Plot the Yearly Growth Chart
    # ===========================================================================
    # todo : Get the ticklines (both x axis and y axis)
    # todo : Print the values on Blue line, if you want

    logging.debug("-------------------------------------------")
    logging.debug("Starting to plot the Yearly Growth Chart")
    logging.debug("-------------------------------------------")
    logging.debug("The YR DF is \n" + ticker_yr_numbers_df.to_string())
    # Get only last 10 years to plot
    col_list = ticker_yr_numbers_df.columns.tolist()
    if (len(col_list)) > 10:
      logging.debug("The yearly dataframe has more than 10 cols.")


    # yr_growth_plt.title.set_text("Yearly Growth Chart")
    yr_growth_plt.set_facecolor("lightgrey")

    yr_growth_plt_lim_lower = 0
    yr_growth_plt_lim_upper = 3.5
    # Extract the various growth numbers and set the upper limit, if greater than
    #  3.5 (set by default up - based on 20% grwoth rate for 8 years)

    all_numbers = all(isinstance(item, (int, float)) for item in ticker_yr_numbers_df.loc["Diluted_EPS_Growth"])
    all_numbers = True
    if (all_numbers is True):
      tmp_max = max(ticker_yr_numbers_df.loc["Diluted_EPS_Growth"])
      logging.debug("The max value in Diluted EPS Growth List is "  + str(tmp_max))
      if (tmp_max > yr_growth_plt_lim_upper):
        yr_growth_plt_lim_upper = int(round(tmp_max))+.5

    all_numbers = all(isinstance(item, (int, float)) for item in ticker_yr_numbers_df.loc["Revenue_Growth"])
    all_numbers = True
    if (all_numbers is True):
      tmp_max = max(ticker_yr_numbers_df.loc["Revenue_Growth"])
      logging.debug("The max value in  Revenue Growth List is " + str(tmp_max))
      if (tmp_max > yr_growth_plt_lim_upper):
        yr_growth_plt_lim_upper = int(round(tmp_max))+.5

    all_numbers = all(isinstance(item, (int, float)) for item in ticker_yr_numbers_df.loc["BV_Per_Share_Growth"])
    all_numbers = True
    if (all_numbers is True):
      tmp_max = max(ticker_yr_numbers_df.loc["BV_Per_Share_Growth"])
      logging.debug("The max value in BVPS Growth List is " + str(tmp_max))
      if (tmp_max > yr_growth_plt_lim_upper):
        yr_growth_plt_lim_upper = int(round(tmp_max))+.5

    all_numbers = all(isinstance(item, (int, float)) for item in ticker_yr_numbers_df.loc["FCF_Per_Share_Growth"])
    all_numbers = True
    if (all_numbers is True):
      tmp_max = max(ticker_yr_numbers_df.loc["FCF_Per_Share_Growth"])
      logging.debug("The max value in FCFPS Growth List is " + str(tmp_max))
      if (tmp_max > yr_growth_plt_lim_upper):
        yr_growth_plt_lim_upper = int(round(tmp_max)) + .5

    logging.debug("The upper limit for the Growth Plot is calculate to be : " + str(yr_growth_plt_lim_upper))
    if (yr_growth_plt_lim_upper > 10):
      yr_growth_plt_lim_upper = 10
      logging.debug("The upper limit for the Growth Plot was calcualated to be very high. Resetting it to : " + str(yr_growth_plt_lim_upper))

    yr_growth_plt.set_ylim(yr_growth_plt_lim_lower, yr_growth_plt_lim_upper)
    yr_growth_plt.tick_params(axis="y", direction="in", pad=-22)
    yr_growth_plt.tick_params(axis="x", direction="in",pad=-12)

    # Choose which indices need to be plotted for the growth chart and plot them
    yr_growth_plt_inst_00 = yr_growth_plt.plot(ticker_yr_numbers_df.columns.tolist(), base_growth_10_percent_list, label='10%', linestyle='--',color='blue',marker="*",markersize='12')
    yr_growth_plt_inst_01 = yr_growth_plt.plot(ticker_yr_numbers_df.columns.tolist(), base_growth_20_percent_list, label='20%', linestyle='--',color='blue',marker="*",markersize='12')
    yr_growth_plt_inst_02 = yr_growth_plt.plot(ticker_yr_numbers_df.columns.tolist(), ticker_yr_numbers_df.loc["Revenue_Growth"], label='Rev', color="green", marker='.', markersize='10')
    yr_growth_plt_inst_03 = yr_growth_plt.plot(ticker_yr_numbers_df.columns.tolist(), ticker_yr_numbers_df.loc["Diluted_EPS_Growth"], label='EPS', color="deeppink", marker='.', markersize='10')
    yr_growth_plt_inst_04 = yr_growth_plt.plot(ticker_yr_numbers_df.columns.tolist(), ticker_yr_numbers_df.loc["NTA_Per_Share_Growth"], label='NTAPS', color="tomato", marker='.', markersize='10')
    yr_growth_plt_inst_05 = yr_growth_plt.plot(ticker_yr_numbers_df.columns.tolist(), ticker_yr_numbers_df.loc["BV_Per_Share_Growth"], label='BVPS', color="brown", marker='.', markersize='10')
    yr_growth_plt_inst_06 = yr_growth_plt.plot(ticker_yr_numbers_df.columns.tolist(), ticker_yr_numbers_df.loc["FCF_Per_Share_Growth"], label='FCFPS', color="yellow", marker='.', markersize='10')

    yr_growth_plt_date_list = ticker_yr_numbers_df.columns.tolist()
    fiscal_yr_dates = []
    for x in yr_growth_plt_date_list:
      logging.debug("The original Yearly Date is : " + str(x))
      x_date = dt.datetime.strptime(x,'%m/%d/%Y').date()
      fiscal_yr_dates.append(x_date.strftime('%b-%y'))
    yr_growth_plt.set_xticklabels(fiscal_yr_dates, rotation=0, fontsize=10, minor=False, fontstyle='italic')

    # Print the labels in the plot...This needs to adjust if the plot gets
    # moved/resized as the position of the lables is hardcoded in the legend
    # statement below
    lns = yr_growth_plt_inst_00+yr_growth_plt_inst_01+yr_growth_plt_inst_02+yr_growth_plt_inst_03+yr_growth_plt_inst_04+yr_growth_plt_inst_05+yr_growth_plt_inst_06
    labs = [l.get_label() for l in lns]
    logging.debug("The Labels are" + str(labs))
    yr_growth_plt.legend(lns, labs, bbox_to_anchor=(.2, 1.02), loc="upper right", borderaxespad=2, fontsize='x-small')
    # ===========================================================================

    # ===========================================================================
    # Plot the Yearly Numbers table
    # ===========================================================================
    # yr_table_plt.set_title("Yearly Table",color='black', loc='center')
    yr_table_plt.set_facecolor("black")
    yr_table_plt.set_yticks([])
    yr_table_plt.set_xticks([])

    # Create a new dataframe - ticker_yr_table_df - that only has the indices that we want to display in the table
    desired_indices = ['Revenue','Diluted_EPS','NTA_Per_Share','BV_Per_Share','FCF_Per_Share','LT_Debt','Shares_Diluted','ROE','ROIC','No_of_Employees']
    ticker_yr_table_df = ticker_yr_numbers_df.loc[desired_indices]
    logging.debug("Inside the plotting area : The ticker yr df with only the desired rows \n" + ticker_yr_table_df.to_string())

    yr_table_plt_inst = yr_table_plt.table(cellText=ticker_yr_table_df.values, rowLabels=ticker_yr_table_df.index,colWidths=[0.1] * len(ticker_yr_table_df.columns),colLabels=ticker_yr_table_df.columns,loc="upper center")

    logging.debug("")
    logging.debug("Will now set the appropriate cell colors in the dataframe")

    # Get the row numbers for various row headings (indices).
    # These can be used later to format the data in the respective rows
    lt_debt_row_idx =  ticker_yr_table_df.index.get_loc('LT_Debt') + 1
    revenue_row_idx =  ticker_yr_table_df.index.get_loc('Revenue') + 1
    shares_outstanding_row_idx =  ticker_yr_table_df.index.get_loc('Shares_Diluted') + 1
    no_of_employees_row_idx =  ticker_yr_table_df.index.get_loc('No_of_Employees') + 1
    roe_row_idx =  ticker_yr_table_df.index.get_loc('ROE') + 1
    roic_row_idx =  ticker_yr_table_df.index.get_loc('ROIC') + 1
    # The column header starts with (0, 0)...(0, n - 1).The row header starts with (1, -1)...(n, -1)
    for key, cell in yr_table_plt_inst.get_celld().items():
      row_idx = key[0]
      col_idx = key[1]
      cell_val = cell.get_text().get_text()
      logging.debug("Row idx " + str(row_idx) + " Col idx " + str(col_idx) + " Value " + str(cell_val))

      # Alternate the colors on the rows
      if (row_idx % 2 == 0):
        yr_table_plt_inst[(row_idx, col_idx)].set_facecolor('seashell')
      else:
        yr_table_plt_inst[(row_idx, col_idx)].set_facecolor('azure')

      # Change the Date format to be shorter
      if (row_idx == 0):
        x_date = dt.datetime.strptime(cell_val,'%m/%d/%Y').date()
        x = dt.datetime.strftime(x_date, '%b-%y')
        logging.debug("The date is " + str(x))
        cell.get_text().set_text(x)

      # Set bold the header row and index column
      if ((row_idx == 0) or (col_idx < 0)):
        cell.get_text().set_fontweight('bold')
      elif (cell_val == 'nan'):
        x = "-"
        cell.get_text().set_text(x)
      else:
        if float(cell_val) < 0:
          cell.get_text().set_color('Red')
          cell.get_text().set_fontstyle('italic')
          yr_table_plt_inst[(row_idx, col_idx)].set_facecolor('lightpink')

        if ((row_idx == revenue_row_idx) or (row_idx == lt_debt_row_idx) or (row_idx == shares_outstanding_row_idx)):
          x_int = int(float(cell_val))
          x = human_format(x_int)
        elif (row_idx == no_of_employees_row_idx):
          x = int(float(cell_val))
        elif ((row_idx == roe_row_idx) or (row_idx == roic_row_idx)):
          x =  f'{float(cell.get_text().get_text()):.2f}'
          x = x + "%"
        else:
          x =  f'{float(cell.get_text().get_text()):.2f}'

        cell.get_text().set_text(x)


    yr_table_plt.axis('off')
    logging.info("Done with plotting YR table...")
    # ===========================================================================


    # Save the plot
    now = dt.datetime.now()
    # date_time = now.strftime("%Y_%m_%d_%H_%M")
    date_time = now.strftime("%Y_%m_%d")

    # fig.savefig(dir_path + analysis_plot_dir + "\\" + ticker + "_Analysis_" + date_time + ".jpg",dpi=200, bbox_inches='tight',facecolor='#E0E0E0')
    fig.savefig(dir_path + analysis_plot_dir + "\\" + ticker + "_Analysis" + ".jpg",dpi=200, bbox_inches='tight',facecolor='#E0E0E0')
    if (g_var_copy_ticker_plot_2_watchlist_dir_en == 1) and (this_ticker_qualifies_in_watchlist == 1):
      if (ticker_in_master_tracklist == 'Y'):
        fig.savefig(dir_path + analysis_plot_watchlist_dir +  "\\" + "Wheat" +  "\\" + ticker + "_Analysis" + ".jpg", dpi=200,bbox_inches='tight', facecolor='#E0E0E0')
      else:
        fig.savefig(dir_path + analysis_plot_watchlist_dir +  "\\" + "Not_Wheat" +  "\\" + ticker + "_Analysis" + ".jpg", dpi=200,bbox_inches='tight', facecolor='#E0E0E0')

    # Only show the plot if we are making only one chart
    if (len(ticker_list) == 1):
      plt.show()
    else:
      plt.close(fig)

    # if g_var_plot_en statement
  i_idx += 1
  # Outer loop ends here


logging.info("")
logging.info("Total Number of tickers in the list : " + str(total_number_of_ticker))
logging.info("Made Plots for                      : " + str(i_idx-1))
logging.info("Did not make Plot for               : " + str(len(skipped_tickers_df.index.tolist())))
logging.info("List of Tickers that did not plot   : " + str(skipped_tickers_df.index.tolist()))
skipped_tickers_logfile="SC_Create_0Analysis_skipped_tickers.txt"
logging.info("Created : " + str(skipped_tickers_logfile) + " <-- Sorted by Ticker - Lists all the tickers that were not plotted along with a reason")
skipped_tickers_df.sort_values(by=['Ticker'], ascending=[True]).to_csv(dir_path + log_dir + "\\" + skipped_tickers_logfile,sep=' ', index=True, header=True)

logging.info("")
watchlist_0analysis_logfile="SC_Create_0Analysis_watchlist.csv"
logging.info("No.  of tickers that matched the growth criteria : " + str(len(watchlist_0analysis_df.index.tolist())))
logging.info("List of Tickers that matched to growth criteria  : " + str(watchlist_0analysis_df.index.tolist()))
logging.info("Created : " + str(watchlist_0analysis_logfile) + " <-- Sorted by Ticker - Lists all the tickers that could be intersting to add to watchlist")
watchlist_0analysis_df.sort_values(by=['Ticker'], ascending=[True]).to_csv(dir_path + log_dir + "\\" + watchlist_0analysis_logfile,sep=',', index=True, header=True)


logging.info("")
logging.info("All Done")

# table_props = yr_table_plt_inst.properties()
  # logging.debug("The dictionary of table properties is \n" + str(table_props))
  # table_cells = table_props['child_artists']
  # for cell in table_cells:
  #   cell_val = cell.get_text()
  #   logging.debug("The cell is " + str(cell) + " and the value is " + str(cell_value) + " and the color is " + str(cell_val.get_color()))
  #   # cell_val.set_color('green')
  #   cell_val.set_text("HAHA")
  #   logging.debug("The cell is " + str(cell) + " and the value is " + str(cell_val) + " and the color is " + str(cell_val.get_color()))
  #   # logging.debug("Now the color is " + str(cell_val.get_color()))


  # for row_idx in range(len(ticker_yr_table_df.values)):
  #   logging.debug("\nThe row idx is " + str(row_idx) + " and the row value is " + str(ticker_yr_table_df.index[row_idx]))
  #   row_val_list = ticker_yr_table_df.iloc[row_idx]
  #   logging.debug("The columns corresponding to the row idx " + str(row_idx) + " are\n" + str(row_val_list))
  #   for col_idx in range(len(row_val_list)):
  #     logging.debug("The col idx is " + str(col_idx) + " and the value is " + str(row_val_list[col_idx]))
  #     if (row_val_list[col_idx] < 0):
  #       yr_table_plt_inst[(row_idx+1, col_idx)].set_facecolor('grey')


  # https://pandas.pydata.org/pandas-docs/stable/user_guide/visualization.html
  # https://stackoverflow.com/questions/32137396/how-do-i-plot-only-a-table-in-matplotlib
  # https: // stackoverflow.com / questions / 28681782 / create - table - in -subplot
  # https://stackoverflow.com/questions/41151165/how-to-add-a-table-that-only-contains-strings-to-a-matplotlib-graph
  # https://stackoverflow.com/questions/11623056/matplotlib-using-a-colormap-to-color-table-cell-background
  # https://matplotlib.org/api/_as_gen/matplotlib.pyplot.table.html

  # dc = pd.DataFrame({'A': [1, 2, 3, 4], 'B': [4, 3, 2, 1], 'C': [3, 4, 2, 2]})
  #
  # plt.plot(dc)
  # plt.legend(dc.columns)
  # dcsummary = pd.DataFrame([dc.mean(), dc.sum()], index=['Mean', 'Total'])
  #
  # plt.table(cellText=ticker_yr_table_df.values, rowLabels=ticker_yr_table_df.index,colWidths=[0.25] * len(ticker_yr_table_df.columns),
  #           colLabels=ticker_yr_table_df.columns,
  #           cellLoc='center', rowLoc='center',
  #           loc='bottom')
  #
  #
  # fig = plt.gcf()
  #
  # plt.show()
  # logging.info("\nDone " + str(ticker))
  #

