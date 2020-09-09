
import csv
import openpyxl
from openpyxl.styles import PatternFill
import os
import xlrd
import sys
import time
import pandas as pd
import datetime as dt
from yahoofinancials import YahooFinancials
import time
import logging
import xlsxwriter


#
# Define the directories and the paths
dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
chart_dir = "..\\" + "Charts"
historical_dir = "\\..\\" + "Historical"
earnings_dir = "\\..\\" + "Earnings"
dividend_dir = "\\..\\" + "Dividend"
log_dir = "\\..\\" + "Logs"
analysis_dir = "\\..\\" + "Analysis"
# ---------------------------------------------------------------------------
# Set Logging
# critical, error, warning, info, debug
# set up logging to file - see previous section for more details
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename=dir_path + log_dir + "\\" + 'SC_Parese_AAII_Download_debug.txt',
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


# -----------------------------------------------------------------------------
# Set the various dirs and read the AAII file
# -----------------------------------------------------------------------------
tracklist_file = "Tracklist.csv"
tracklist_file_full_path = dir_path + user_dir + "\\" + tracklist_file
configuration_file = "Configurations.csv"
configurations_file_full_path = dir_path + user_dir + "\\" + configuration_file
tracklist_df = pd.read_csv(tracklist_file_full_path)

qtr_str_list =['Q1', 'Q2','Q3','Q4','Q5','Q6','Q7','Q8']
yr_str_list =['Y1', 'Y2','Y3','Y4','Y5','Y6','Y7']


# ---------------------------------------------------------
# Read the AAII file
# Declare the dataframes that will be used
# Set the columns and index
# ---------------------------------------------------------
# This takes around 21 sec
start = time.process_time()
aaii_xls_file = '2020_09_04_AAII_Analysis.xlsx'
aaii_xls = pd.ExcelFile(aaii_xls_file)
print(time.process_time() - start)

aaii_misc_00_df = pd.read_excel(aaii_xls, '0_Analysis_Misc_00')
aaii_financials_qtr_df = pd.read_excel(aaii_xls, '0_Analysis_QTR')
aaii_financials_yr_df = pd.read_excel(aaii_xls, '0_Analysis_YR')

aaii_misc_00_df.set_index('Ticker', inplace=True)
aaii_financials_qtr_df.set_index('Ticker', inplace=True)
aaii_financials_yr_df.set_index('Ticker', inplace=True)
# ---------------------------------------------------------

# -----------------------------------------------------------------------------

# RGP is RECN old --- need to handle
aaii_missing_tickers_list = [
'CBOE','CP','CRZO','GOOG','RACE','NTR','RGP','WCG'
]

ticker_list_unclean = tracklist_df['Tickers'].tolist()
ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']

# #############################################################################
#                   MAIN LOOP FOR TICKERS
# Part 1 : Get the various fields from those series that we need for Key Statistics
# and financial qtr/yr dataframes
# Those fields are used to create the respective dataframes :
# 1. aaii_key_statistics_df --> Contains Key Statistics data
# 2. aaii_qtr_df            --> Contains Financial qtr data
# 3. aaii_qtr_df            --> Contains  Financial yr data
# Part 2 : Those dataframe are merge into existing data from the ticker csv
# If the corresponding ticker csv does not exist, then one is created
# #############################################################################
ticker_list = ['MA','AAPL','IBM']
# ticker_list = ['IBM','AAPL', 'AUDC','MED']
i_idx = 1
for ticker_raw in ticker_list:

  ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase
  if ((ticker in aaii_missing_tickers_list)) or  (ticker in ["QQQ"]):
    logging.debug(str(ticker) + " is NOT in AAII df or is QQQ (etf). Will skip inserting EPS Projections..")
    continue

  logging.info("========================================================")
  logging.info("Iteration no : " + str(i_idx) + ", Processing : " + ticker)
  logging.info("========================================================")
  i_idx += 1

  # Get the ticker information in series from the various AAII df
  aaii_date_and_misc_series = aaii_misc_00_df.loc[ticker]
  aaii_financials_qtr_series = aaii_financials_qtr_df.loc[ticker]
  aaii_financials_yr_series = aaii_financials_yr_df.loc[ticker]
  logging.debug("-------------------------------------")
  logging.debug("The date and period series is : ")
  logging.debug("-------------------------------------")
  logging.debug(str(aaii_date_and_misc_series))

  logging.debug("-------------------------------------")
  logging.debug("The Financials QTR series is : ")
  logging.debug("-------------------------------------")
  logging.debug(str(aaii_financials_qtr_series))

  logging.debug("-------------------------------------")
  logging.debug("The Financials YR series is : ")
  logging.debug("-------------------------------------")
  logging.debug(str(aaii_financials_yr_series))

  logging.debug("-------------------------------------")

  # ===========================================================================
  #                PART 1 - Process the various series that have been read in
  #                         to prepare the dataframes for Key Statistics,
  #                         financial qtrand financial yr data
  # These dataframes are them merged with the alread existing data in PART 2 later
  # ===========================================================================
  # ---------------------------------------------------------------------------
  # Prepare the dataframe for Key Statistics
  # ---------------------------------------------------------------------------
  logging.debug("")
  logging.debug("=======================================")
  logging.debug("Starting to Read Key Statistics Data ")
  logging.debug("=======================================")
  aaii_key_statistics_df = pd.DataFrame(columns=['AAII_KEY_STATISTICS_DATA'])
  aaii_key_statistics_df.set_index(['AAII_KEY_STATISTICS_DATA'], inplace=True)
  qtr_idx = qtr_str_list[0]
  most_recent_qtr_date_str = aaii_date_and_misc_series['Ending date ' + str(qtr_idx)]
  most_recent_qtr_date_dt = dt.datetime.strptime(str(most_recent_qtr_date_str), '%Y-%m-%d %H:%M:%S').date()
  most_recent_qtr_date_str = most_recent_qtr_date_dt.strftime('%m/%d/%Y')
  logging.debug("The most recent qtr date is : " + str(most_recent_qtr_date_str))
  aaii_key_statistics_df.assign(most_recent_qtr_date_str = "")
  aaii_key_statistics_df.loc['No_of_Employees', most_recent_qtr_date_str] = aaii_date_and_misc_series['Number of employees']
  aaii_key_statistics_df.loc['No_of_Institutions', most_recent_qtr_date_str] = aaii_date_and_misc_series['Institutional shareholders']
  aaii_key_statistics_df.loc['Net_Insider_Purchases', most_recent_qtr_date_str] = aaii_date_and_misc_series['Insiders--net shares purchased']
  aaii_key_statistics_df.loc['Institutional_Ownership', most_recent_qtr_date_str] = aaii_date_and_misc_series['Institutional Ownership %']
  aaii_key_statistics_df.loc['Insider_Ownership', most_recent_qtr_date_str] = aaii_date_and_misc_series['Insider Ownership %']

  logging.debug("\n\nThe Key Statistics DF Prepared from AAII Data is \n" + aaii_key_statistics_df.to_string() + "\n")
  logging.info("Read in Key Statistics data from AAII file")
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Prepare the dataframe for Financials qtr
  # ---------------------------------------------------------------------------
  logging.debug("")
  logging.debug("=======================================")
  logging.debug("Starting to Read QTR Data ")
  logging.debug("=======================================")
  aaii_qtr_df = pd.DataFrame(columns=['AAII_QTR_DATA'])
  aaii_qtr_df.set_index(['AAII_QTR_DATA'], inplace=True)
  for qtr_idx in qtr_str_list:
    # Handle the case when the date is NA in the AAII file
    aaii_qtr_date_str = aaii_date_and_misc_series['Ending date ' + str(qtr_idx)]
    logging.debug("Getting Quarterly data from AAII file for : " + str(qtr_idx) + ", which corresponds to date : " + str(aaii_qtr_date_str))
    if not ((str(aaii_qtr_date_str) == 'NaT') or (len(str(aaii_qtr_date_str)) == 0)):
      tmp_val_dt =  dt.datetime.strptime(str(aaii_qtr_date_str),'%Y-%m-%d %H:%M:%S').date()
      tmp_val =  tmp_val_dt.strftime('%m/%d/%Y')
      # This add a new column corresponding to the qtr date
      aaii_qtr_df.assign(tmp_val = "")
      # These add rows/index for the corresponding dates (which are in columns)
      aaii_qtr_df.loc['Revenue', tmp_val] = aaii_financials_qtr_series['Sales '+str(qtr_idx)]
      aaii_qtr_df.loc['Inventory', tmp_val] = aaii_financials_qtr_series['Inventory '+str(qtr_idx)]
      aaii_qtr_df.loc['Diluted_EPS', tmp_val] = aaii_financials_qtr_series['EPS-Diluted '+str(qtr_idx)]
      aaii_qtr_df.loc['Shares_Diluted', tmp_val] = aaii_financials_qtr_series['Shares Diluted '+str(qtr_idx)]
      aaii_qtr_df.loc['Current_Assets', tmp_val] = aaii_financials_qtr_series['Current assets '+str(qtr_idx)]
      aaii_qtr_df.loc['Current_Liabilities', tmp_val] = aaii_financials_qtr_series['Current liabilities '+str(qtr_idx)]
      aaii_qtr_df.loc['Total_Assets', tmp_val] = aaii_financials_qtr_series['Total assets '+str(qtr_idx)]
      aaii_qtr_df.loc['Total_Liabilities', tmp_val] = aaii_financials_qtr_series['Total liabilities '+str(qtr_idx)]
      aaii_qtr_df.loc['LT_Debt', tmp_val] = aaii_financials_qtr_series['Long-term debt '+str(qtr_idx)]
    else:
      logging.error("The date string from the AAII file for " + str(qtr_idx) + " was either NaT or empty. Please check the AAII Data. Exiting...")
      sys.exit(1)

  logging.debug("\n\nThe QTR DF Prepared from AAII Data is \n" + aaii_qtr_df.to_string() + "\n")
  logging.info("Read in QTR data from AAII file")
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Prepare the dataframe for Financials qtr
  # ---------------------------------------------------------------------------
  logging.debug("")
  logging.debug("=======================================")
  logging.debug("Starting to Read YR Data ")
  logging.debug("=======================================")
  aaii_yr_df = pd.DataFrame(columns=['AAII_YR_DATA'])
  aaii_yr_df.set_index(['AAII_YR_DATA'], inplace=True)
  for yr_idx in yr_str_list:
    aaii_yr_date_str = aaii_date_and_misc_series['Ending date ' + str(yr_idx)]
    logging.debug("Getting Yearly data from AAII file for : " + str(yr_idx) + ", which corresponds to date : " + str(aaii_yr_date_str))
    if not ((str(aaii_yr_date_str) == 'NaT') or (len(str(aaii_yr_date_str)) == 0)):
      tmp_val_dt = dt.datetime.strptime(str(aaii_yr_date_str),'%Y-%m-%d %H:%M:%S').date()
      tmp_val =  tmp_val_dt.strftime('%m/%d/%Y')
      # This add a new column corresponding to the yr date str
      aaii_yr_df.assign(tmp_val = "")
      # These add rows/index for the corresponding dates (which are in columns)
      aaii_yr_df.loc['Revenue', tmp_val] = aaii_financials_yr_series['Sales '+str(yr_idx)]
      aaii_yr_df.loc['Net_Income', tmp_val] = aaii_financials_yr_series['Net income '+str(yr_idx)]
      aaii_yr_df.loc['Diluted_EPS', tmp_val] = aaii_financials_yr_series['EPS-Diluted '+str(yr_idx)]
      aaii_yr_df.loc['Cash_from_Operations', tmp_val] = aaii_financials_yr_series['Cash from operations '+str(yr_idx)]
      aaii_yr_df.loc['Capital_Expenditures', tmp_val] = aaii_financials_yr_series['Capital expenditures '+str(yr_idx)]
      aaii_yr_df.loc['Shares_Diluted', tmp_val] = aaii_financials_yr_series['Shares Diluted '+str(yr_idx)]
      aaii_yr_df.loc['LT_Debt', tmp_val] = aaii_financials_yr_series['Long-term debt '+str(yr_idx)]
      aaii_yr_df.loc['Total_Assets', tmp_val] = aaii_financials_yr_series['Total assets '+str(yr_idx)]
      aaii_yr_df.loc['Total_Liabilities', tmp_val] = aaii_financials_yr_series['Total liabilities '+str(yr_idx)]
    else:
      logging.error("The date string from the AAII file for " + str(yr_idx) + " was either NaT or empty. Please check the AAII Data. Exiting...")
      sys.exit(1)

  logging.debug("\n\nThe YR DF Prepared from AAII Data is \n" + aaii_yr_df.to_string() + "\n")
  logging.info("Read in YR data from AAII file")
  # ---------------------------------------------------------------------------

  # ===========================================================================
  #                PART 2 - Read the alreay existing Analysis Data
  #                   and merge it with created AAII Analysis Data
  # ===========================================================================
  # todo : Check if the data merges alright
  #   ticker csv has less cols
  #   ticker csv has more cols
  #   ticker csv has equal cols
  #   ticker csv has less rows
  #   ticker csv has more rows
  #   ticker csv has equal rows
  #   Ensure that date does not give a problem.

  logging.debug("")
  logging.debug("==============================================================================================================")
  logging.info("Now merging/creating(if the data does not exist) the Key Statistics, QTR and YR data into already existing data")
  logging.debug("==============================================================================================================")

  for qtr_yr_idx in ['key_statistics','qtr','yr']:
    logging.debug("")
    logging.debug("=======================================")
    logging.debug("Staring the merge/create for " + str(qtr_yr_idx).upper())
    logging.debug("=======================================")
    ticker_csv_exists = 0
    ticker_csv_filename = ticker + "_" + qtr_yr_idx + "_data.csv"
    if qtr_yr_idx == 'key_statistics':
      ticker_csv_filepath = dir_path + analysis_dir + "\\" + "Key_Statistics"
      aaii_df = aaii_key_statistics_df.copy()
    elif qtr_yr_idx == 'yr':
      ticker_csv_filepath = dir_path + analysis_dir + "\\" + "Yearly"
      aaii_df = aaii_yr_df.copy()
    else:
      ticker_csv_filepath = dir_path + analysis_dir + "\\" + "Quarterly"
      aaii_df = aaii_qtr_df.copy()

    # aaii_datelist_dt =  [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in list(aaii_df)]
    # logging.debug("The aaii df datelist is " + str(aaii_datelist_dt))

    if (os.path.exists(ticker_csv_filepath + "\\" + ticker_csv_filename) is True):
      ticker_csv_df = data = pd.read_csv(ticker_csv_filepath + "\\" + ticker_csv_filename)
      logging.info("File "  + str(ticker_csv_filename) + " exists. Will read-in and merge the latest AAII data into it")
      ticker_csv_exists = 1


    # If the ticker csv exits, then read it and merge the aaii data with it 
    if (ticker_csv_exists == 1):
      ticker_csv_df.set_index("AAII_" + str(qtr_yr_idx).upper() + "_DATA", inplace=True)
      logging.debug("\n\nThe Ticker df is \n" + ticker_csv_df.to_string() + "\n")
      logging.debug("Will now check for all the rows and column in aaii df and see if they exist in ticker df")
      logging.debug("If the are present in both, then will replace that data with AAII data - assumption being that AAII might have updated data meanwhile - company restated etc...")
      logging.debug("If they are present only in AAII, then will insert them in the ticker df because ticker df is lacking those rows/columns b/c AAII has the latest data (from 2020 while ticker df only has data till 2019 etc")
      logging.debug("If they are present only in ticker df, then that data will be left as is. The most common reason for this is that ticker df has 2012 data while AAII start from 2013")
      logging.debug("")

      # -----------------------------------------------------------------------
      # Start the process of comparing aaii df rows and columns with
      # ticker csv df rows and columns respectively
      # -----------------------------------------------------------------------
      ticker_csv_df_cols = ticker_csv_df.columns.tolist()
      ticker_csv_df_rows = ticker_csv_df.index.tolist()
      aaii_df_cols = aaii_df.columns.tolist()
      aaii_df_rows = aaii_df.index.tolist()
      common_rows = []
      common_cols = []
      different_rows = []
      different_cols = []

      # -----------------------------------------------------------------------
      # Iterate through the rows for aaii_df and ticker csv
      # to find out if there are row(s) in aaii_df that are not in ticker csv.
      # If so then that rows(s) gets appended to ticker csv df row list
      # -----------------------------------------------------------------------
      logging.debug("Checking for rows...")
      logging.debug("The rows in aaii df " + str(aaii_df_rows))
      logging.debug("The rows in ticker df " + str(ticker_csv_df_rows))
      for rows_idx in aaii_df_rows:
        if rows_idx in ticker_csv_df_rows:
          logging.debug("Row --> " + str(rows_idx) + " <-- is present in both AAII df and ticker df. Will replace that row in ticker df with latest data from AAII df...")
          common_rows.append(rows_idx)
        else:
          logging.debug("Row --> " + str(rows_idx) + " <-- is present only in AAII df. Will insert that row in ticker df with latest data from AAII df...")
          ticker_csv_df_rows.append(rows_idx)
          different_rows.append(rows_idx)
      # -----------------------------------------------------------------------

      # -----------------------------------------------------------------------
      # Iterate through the columns for aaii_df and ticker csv
      # to find out if there are column(s) in aaii_df that are not in ticker csv.
      # If so then that column(s) gets appended to ticker csv df column list
      # -----------------------------------------------------------------------
      logging.debug("")
      logging.debug("Checking for columns...")
      logging.debug("The columns in aaii df " + str(list(aaii_df)))
      logging.debug("The columns in ticker df " + str(ticker_csv_df_cols))
      # todo : Make sure that dates here do not give trouble...
      #  otherwise need to do a datetime conversion and then compare???
      for cols_idx in aaii_df_cols:
        if cols_idx in ticker_csv_df_cols:
          logging.debug("Column --> " + str(cols_idx) + " <-- is present in both AAII df and ticker df. Will replace that column in ticker df with latest data from AAII df...")
          common_cols.append(cols_idx)
        else:
          logging.debug("Column --> " + str(cols_idx) + " <-- is present only in AAII df. Will insert that column in ticker df with latest data from AAII df...")
          ticker_csv_df_cols.append(cols_idx)
          different_cols.append(cols_idx)
      # -----------------------------------------------------------------------

      logging.debug("")
      logging.debug("The common rows b/w the ticker and aaii df are " + str(common_rows))
      logging.debug("The common cols b/w the ticker and aaii df are " + str(common_cols))
      logging.debug("")
      logging.debug("The different rows b/w the ticker and aaii df are " + str(different_rows))
      logging.debug("The different cols b/w the ticker and aaii df are " + str(different_cols))
      # -----------------------------------------------------------------------

      # -----------------------------------------------------------------------
      # Reindex the ticker_csv_df based on any new rows/columns added after
      # comparing it with aaii_df and add aaii data to the added columns (the row
      # date get automatically added when the column data gets added
      # -----------------------------------------------------------------------
      tmp_df = ticker_csv_df.reindex(index=ticker_csv_df_rows)
      ticker_csv_df = tmp_df.reindex(columns=ticker_csv_df_cols)
      logging.debug("\n\nThe Ticker df after adding missing rows and cols, if any : \n" + ticker_csv_df.to_string() + "\n")

      # How to deal with the case when aaii has fewer rows than ticker df - what will happen in that case?
      for cols_idx in aaii_df_cols:
        ticker_csv_df[cols_idx] = aaii_df[cols_idx]
      logging.debug("\n\nThe Ticker df after copying the latest (and missing data, if there were lesser number of rows/columns in the ticker csv) : \n" + ticker_csv_df.to_string() + "\n")
      # -----------------------------------------------------------------------

      # -----------------------------------------------------------------------
      # Now sort the ticker columns decscening based on dates and write it to csv
      # -----------------------------------------------------------------------
      # Don't understand how this works...but it works
      ticker_csv_df = ticker_csv_df.iloc[:, pd.to_datetime(ticker_csv_df.columns, format='%m/%d/%Y').argsort()[::-1]].reset_index()
      ticker_csv_df.set_index("AAII_" + str(qtr_yr_idx).upper() + "_DATA", inplace=True)
      ticker_csv_df.sort_index(ascending=True,inplace=True)
      logging.debug("\n\nThe Ticker df after sorting by rows (ascending) column dates (descending)  \n" + ticker_csv_df.to_string() + "\n")
      ticker_csv_df.to_csv(ticker_csv_filepath + "\\" + ticker_csv_filename, sep=',', index=True, header=True)
      logging.debug("Done with merging ticker and aaii df for : " + str(qtr_yr_idx).upper())
      logging.debug("")
    else:
      logging.info("File "  + str(ticker_csv_filename) + " does not exist. Will create anew and write the latest AAII data - with rows sorted in ascending order - into it")
      aaii_df.sort_index(ascending=True,inplace=True)
      aaii_df.to_csv(ticker_csv_filepath + "\\" + ticker_csv_filename, sep=',', index=True, header=True)
      # -----------------------------------------------------------------------

    # This works
    # Try access the dataframe element by element - this can be used later
    # ticker_csv_df_cols = ticker_csv_df.columns.tolist()
    # ticker_csv_df_rows = ticker_csv_df.index.tolist()
    # for rows_idx in ticker_csv_df_rows:
    #   for  cols_idx in ticker_csv_df_cols:
    #     logging.debug("Row : " + str(rows_idx) + ", Column : " + str(cols_idx) + ", Value : " + str(ticker_csv_df.loc[rows_idx,cols_idx]))

logging.info("")
logging.info("All Done...")
