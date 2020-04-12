
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



tracklist_file = "Tracklist.csv"
tracklist_file_full_path = dir_path + user_dir + "\\" + tracklist_file
configuration_file = "Configurations.csv"
configurations_file_full_path = dir_path + user_dir + "\\" + configuration_file
tracklist_df = pd.read_csv(tracklist_file_full_path)





# -----------------------------------------------------------------------------
# Read the AAII file
# -----------------------------------------------------------------------------
# This takes around 21 sec
start = time.process_time()
aaii_xls = pd.ExcelFile('2020_04_01_AAII_Analysis.xlsx')
print(time.process_time() - start)

qtr_str_list =['Q1', 'Q2','Q3','Q4','Q5','Q6','Q7','Q8']
yr_str_list =['Y1', 'Y2','Y3','Y4','Y5','Y6','Y7']

aaii_dateandperiod_df = pd.read_excel(aaii_xls, 'Dates')
aaii_bs_qtr_df = pd.read_excel(aaii_xls, 'Balance_QTR')
aaii_pnl_qtr_df  = pd.read_excel(aaii_xls, 'Income_QTR')
aaii_bs_yr_df = pd.read_excel(aaii_xls, 'Balance_YR')
aaii_pnl_yr_df  = pd.read_excel(aaii_xls, 'Income_YR')

# Set the Ticker col and index
aaii_dateandperiod_df.set_index('Ticker', inplace=True)
aaii_bs_qtr_df.set_index('Ticker', inplace=True)
aaii_pnl_qtr_df.set_index('Ticker', inplace=True)
aaii_bs_yr_df.set_index('Ticker', inplace=True)
aaii_pnl_yr_df.set_index('Ticker', inplace=True)
# -----------------------------------------------------------------------------


ticker_list_unclean = tracklist_df['Tickers'].tolist()
ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']

# #############################################################################
#                   MAIN LOOP FOR TICKERS
# #############################################################################
# ticker_list = ['AAPL', 'AUDC','MED']
for ticker_raw in ticker_list:

  ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase
  logging.info("========================================================")
  logging.info("Processing for " + ticker)
  logging.info("========================================================")

  # Get the various ticker information from the various dfs
  aaii_dateandperioed_series = aaii_dateandperiod_df.loc[ticker]

  aaii_bs_qtr_series = aaii_bs_qtr_df.loc[ticker]
  aaii_pnl_qtr_series = aaii_pnl_qtr_df.loc[ticker]

  aaii_bs_yr_series = aaii_bs_yr_df.loc[ticker]
  aaii_pnl_yr_series = aaii_pnl_yr_df.loc[ticker]

  # logging.debug("The date and period series is : " + str(aaii_dateandperioed_series))
  # logging.debug("The Balance Sheet YR series is : " + str(aaii_bs_yr_series))
  # logging.debug("The Balance Sheet QTR series is : " + str(aaii_bs_qtr_series))


  # ---------------------------------------------------------------------------
  # Get the various fields that we need for Analysis and prepare the analysis df
  # ---------------------------------------------------------------------------
  aaii_qtr_dates_dict_dt = {}
  aaii_qtr_dates_dict_str = {}
  aaii_yr_dates_dict_dt = {}
  aaii_yr_dates_dict_str = {}

  for qtr_idx in qtr_str_list:
    logging.debug("Getting the Quarterly data from AAII for " + str(qtr_idx))
    aaii_qtr_dates_dict_dt[qtr_idx] =  dt.datetime.strptime(str(aaii_dateandperioed_series['Ending date ' + str(qtr_idx)]),'%Y-%m-%d %H:%M:%S').date()
    aaii_qtr_dates_dict_str[qtr_idx] =  aaii_qtr_dates_dict_dt[qtr_idx].strftime('%m/%d/%Y')

  aaii_yr_df = pd.DataFrame(columns=['AAII_YR_DATA'])
  aaii_yr_df.set_index(['AAII_YR_DATA'], inplace=True)
  for yr_idx in yr_str_list:
    logging.debug("Getting the Yearly data from AAII for " + str(yr_idx))
    aaii_yr_dates_dict_dt[yr_idx] = dt.datetime.strptime(str(aaii_dateandperioed_series['Ending date ' + str(yr_idx)]),'%Y-%m-%d %H:%M:%S').date()
    aaii_yr_dates_dict_str[yr_idx] =  aaii_yr_dates_dict_dt[yr_idx].strftime('%m/%d/%Y')
    tmp_val = aaii_yr_dates_dict_str[yr_idx]
    aaii_yr_df.assign(tmp_val = "")
    aaii_yr_df.loc['Revenue', tmp_val] = aaii_pnl_yr_series['Sales '+str(yr_idx)]
    aaii_yr_df.loc['Dividend', tmp_val] = aaii_pnl_yr_series['Dividend '+str(yr_idx)]
    aaii_yr_df.loc['Diluted_EPS', tmp_val] = aaii_pnl_yr_series['EPS-Diluted Continuing '+str(yr_idx)]
    aaii_yr_df.loc['LT_Debt', tmp_val] = aaii_bs_yr_series['Long-term debt '+str(yr_idx)]
    aaii_yr_df.loc['BV_Per_Share', tmp_val] = aaii_bs_yr_series['Book value/share '+str(yr_idx)]
    aaii_yr_df.loc['Current_Assets', tmp_val] = aaii_bs_yr_series['Current assets '+str(yr_idx)]


  logging.debug("\n\nThe YR DF Prepared from AAII Data is \n" + aaii_yr_df.to_string() + "\n")
  # aaii_yr_df_col_list = aaii_yr_df.columns.tolist()
  # logging.debug("The column list for AAII YR DF is " + str(aaii_yr_df_col_list))
  # aaii_yr_date_list_dt = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in aaii_yr_df_col_list]
  # logging.debug("\n\nThe AAII YR DF Datelist is " + str(aaii_yr_date_list_dt) + " and the number of elements is " + str(len(aaii_yr_date_list_dt)))
  # ---------------------------------------------------------------------------

  # ###########################################################################
  #                PART 2 - Read the alreay existing Analysis Data
  #                   and merge it with created AAII Analysis Data
  # ###########################################################################
  for qtr_yr_idx in ['yr']:
    ticker_csv_exists = 0
    ticker_csv_filename = ticker + "_" + qtr_yr_idx + "_data.csv"
    if qtr_yr_idx == 'yr':
      ticker_csv_filepath = dir_path + analysis_dir + "\\" + "Yearly"
      aaii_df = aaii_yr_df.copy()
    else:
      ticker_csv_filepath = dir_path + analysis_dir + "\\" + "Quarterly"
      # aaii_df = aaii_qtr_df.copy()

    aaii_datelist_dt =  [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in list(aaii_df)]
    logging.debug("The datelist dt for aaii df is " + str(aaii_datelist_dt))

    if (os.path.exists(ticker_csv_filepath + "\\" + ticker_csv_filename) is True):
      logging.debug("The file " + str(ticker_csv_filename) + " exist...will read and merge the data")
      ticker_csv_df = data = pd.read_csv(ticker_csv_filepath + "\\" + ticker_csv_filename)
      ticker_csv_exists = 1


    # If the Analysis file exits for the ticker then merge that date - for each analysis style with the created data
    if (ticker_csv_exists == 1):
      ticker_csv_df.set_index("AAII_" + str(qtr_yr_idx).upper() + "_DATA", inplace=True)
      logging.debug("\n\nThe Ticker df is \n" + ticker_csv_df.to_string() + "\n")


      logging.debug("\n\nThe AAII YR DF Datelist is " + str(type(aaii_datelist_dt)) + " \nand the number of elements is " + str(len(aaii_datelist_dt)))
      # for date_dt_idx in aaii_datelist_dt:
      #   if (date_dt_idx in ticker_csv_datelist_dt):
      #     logging.debug(str(date_dt_idx) + " in AAII df is present in ticker df. Will need to replace...")
      #   else:
      #     logging.debug(str(date_dt_idx) + " in AAII df is not present in ticker df. Will need to insert...")

      ticker_csv_columns = ticker_csv_df.columns.tolist()
      ticker_csv_rows = ticker_csv_df.index.tolist()
      aaii_df_rows = aaii_df.index.tolist()
      common_rows = []
      common_cols = []
      different_rows = []
      different_cols = []
      logging.debug("The rows in ticker df " + str(ticker_csv_rows))
      for rows_idx in  aaii_df.index.tolist():
        if rows_idx in ticker_csv_rows:
          logging.debug(str(rows_idx) + " in AAII df is present in ticker df. Will need to replace...")
          common_rows.append(rows_idx)
        else:
          logging.debug(str(rows_idx) + " in AAII df is not present in ticker df. Will need to insert...")
          ticker_csv_rows.append(rows_idx)
          different_rows.append(rows_idx)

      logging.debug("The columns in ticker df " + str(ticker_csv_columns))
      for cols_idx in list(aaii_df):
        if (cols_idx in list(ticker_csv_df)):
          logging.debug(str(cols_idx) + " in AAII df is present in ticker df. Will need to replace...")
          common_cols.append(cols_idx)
        else:
          logging.debug(str(cols_idx) + " in AAII df is not present in ticker df. Will need to insert...")
          ticker_csv_columns.append(cols_idx)
          different_cols.append(cols_idx)

      logging.debug("The common rows b/w the two df are " + str(common_rows))
      logging.debug("The common cols b/w the two df are " + str(common_cols))
      logging.debug("The different rows b/w the two df are " + str(different_rows))
      logging.debug("The different cols b/w the two df are " + str(different_cols))

      logging.debug("The columns in ticker df " + str(ticker_csv_columns))
      tmp_df = ticker_csv_df.reindex(index=ticker_csv_rows)
      ticker_csv_df = tmp_df.reindex(columns=ticker_csv_columns)
      logging.debug("\n\nThe Ticker df after adding missing rows and cols  \n" + ticker_csv_df.to_string() + "\n")

      # How to deal with the case when aaii has fewer rows than ticker df - what will happen in that case?
      for cols_idx in list(aaii_df):
        ticker_csv_df[cols_idx] = aaii_df[cols_idx]
      logging.debug("\n\nThe Ticker df after copying data from aaii df cols  \n" + ticker_csv_df.to_string() + "\n")

      # Don't understand how this works...but it works
      ticker_csv_df = ticker_csv_df.iloc[:, pd.to_datetime(ticker_csv_df.columns, format='%m/%d/%Y').argsort()[::-1]].reset_index()
      ticker_csv_df.set_index("AAII_" + str(qtr_yr_idx).upper() + "_DATA", inplace=True)
      logging.debug("\n\nThe Ticker df after sorting by column dates  \n" + ticker_csv_df.to_string() + "\n")
      ticker_csv_df.to_csv(ticker_csv_filepath + "\\" + ticker_csv_filename, sep=',', index=True, header=True)


    else:
      logging.debug("The file " + str(ticker_csv_filename) + " does not exist...Will write the data")
      aaii_yr_df.to_csv(ticker_csv_filepath + "\\" + ticker_csv_filename, sep=',', index=True, header=True)


  logging.debug("All Done")
