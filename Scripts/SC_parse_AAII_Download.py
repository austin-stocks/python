
import csv
import openpyxl
from openpyxl.styles import PatternFill
import os
import xlrd
import sys
import re
import time
import pandas as pd
import datetime as dt
from yahoofinancials import YahooFinancials
import time
import logging
import xlsxwriter
from SC_Global_functions import aaii_missing_tickers_list
# from SC_Global_functions import aaii_qtr_or_yr_report_dates_too_far_apart

#
# Define the directories and the paths
dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
log_dir = "\\..\\" + "Logs"
analysis_dir = "\\..\\" + "Analysis"
aaii_data_dir  = "\\..\\" + "Downloaded_from_AAII_for_Analysis"
# ---------------------------------------------------------------------------
# Set Logging
# critical, error, warning, info, debug
# set up logging to file - see previous section for more details
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename=dir_path + log_dir + "\\" + 'SC_Parse_AAII_Download_debug.txt',
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


# -----------------------------------------------------------------------------
# Read the AAII file
# Declare the dataframes that will be used for the read in data and set the index
# -----------------------------------------------------------------------------
# This takes around 21 sec
start = time.process_time()
# aaii_xls_file = '2020_09_04_AAII_Analysis.xlsx'
aaii_xls_file = '2023_05_25_AAII_Analysis.xlsx'

aaii_xls = pd.ExcelFile(dir_path + aaii_data_dir + "\\" + aaii_xls_file)

# ---------------------------------------------------------
# Read in the various tabs from the AAII file
# ---------------------------------------------------------
aaii_misc_00_df = pd.read_excel(aaii_xls, '0_Analysis_Misc_00')
aaii_financials_qtr_df = pd.read_excel(aaii_xls, '0_Analysis_QTR')
aaii_financials_yr_df = pd.read_excel(aaii_xls, '0_Analysis_YR')
logging.info("")
logging.info("Read in the tabs : 1. 0_Analysis_Misc_00  2. 0_Analysis_QTR and 3. 0_Analysis_YR")
logging.info("from the workbook " + str(aaii_xls_file))
logging.info("Reading the AAII workbook took : " + str(time.process_time() - start) + " seconds")
logging.info("Will now start processing the individual tickers")
# ---------------------------------------------------------

use_tickers_from_aaii_file = 1
if (use_tickers_from_aaii_file):
  ticker_list_unclean = aaii_misc_00_df['Ticker'].tolist()
else:
  ticker_list_unclean = tracklist_df['Tickers'].tolist()

aaii_misc_00_df.set_index('Ticker', inplace=True)
aaii_financials_qtr_df.set_index('Ticker', inplace=True)
aaii_financials_yr_df.set_index('Ticker', inplace=True)
# -----------------------------------------------------------------------------

# ---------------------------------------------------------
# Declare the df that will be used to write to the logfiles
# ---------------------------------------------------------
skipped_tickers_df = pd.DataFrame(columns=['Ticker','Reason'])
tickers_with_irregular_report_dates_df  = pd.DataFrame(columns=['Ticker','Reason'])
new_csv_file_created_df  = pd.DataFrame(columns=['Ticker','Reason'])

ticker_qtr_updated_with_new_dates_from_aaii_df = pd.DataFrame(columns=['Ticker','Updated_Data_Type','Reason'])
ticker_yr_updated_with_new_dates_from_aaii_df = pd.DataFrame(columns=['Ticker','Updated_Data_Type','Reason'])

ticker_qtr_NOT_updated_with_new_dates_from_aaii_df = pd.DataFrame(columns=['Ticker','Updated_Data_Type','Reason'])
ticker_yr_NOT_updated_with_new_dates_from_aaii_df = pd.DataFrame(columns=['Ticker','Updated_Data_Type','Reason'])

skipped_tickers_df.set_index('Ticker', inplace=True)
tickers_with_irregular_report_dates_df.set_index('Ticker', inplace=True)
new_csv_file_created_df.set_index('Ticker', inplace=True)

ticker_qtr_updated_with_new_dates_from_aaii_df.set_index('Ticker', inplace=True)
ticker_yr_updated_with_new_dates_from_aaii_df.set_index('Ticker', inplace=True)

ticker_qtr_NOT_updated_with_new_dates_from_aaii_df.set_index('Ticker', inplace=True)
ticker_yr_NOT_updated_with_new_dates_from_aaii_df.set_index('Ticker', inplace=True)
# ---------------------------------------------------------

ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']

# #############################################################################
#                   MAIN LOOP FOR TICKERS
# Part 1 : Get the various fields from those series that we need for Key Statistics
# and financial qtr/yr dataframes
# Those fields are used to create the respective dataframes :
# 1. aaii_key_statistics_df --> Contains Key Statistics data
# 2. aaii_qtr_df            --> Contains Financial qtr data
# 3. aaii_yr_df             --> Contains  Financial yr data
# Part 2 : Those dataframe are merged into existing data from the ticker csv
#          from the Analysis directory.
#          If the corresponding ticker csv does not exist, then one is created
# #############################################################################
# ticker_list = ['IBM']

i_idx = 1
total_number_of_ticker = len(ticker_list)

for ticker_raw in ticker_list:

  # ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase
  ticker = ticker_raw.upper()

  logging.debug("")
  logging.debug("")
  logging.info("========================================================")
  logging.info("Iteration no : " + str(i_idx) + ", Processing : " + ticker)
  logging.info("========================================================")

  if ((ticker in aaii_missing_tickers_list)) or (ticker in ["QQQ"]):
    logging.debug(str(ticker) + " is NOT in AAII df or is QQQ (etf). Will skip inserting EPS Projections. Skipping...")
    skipped_tickers_df.loc[ticker, 'Reason'] = "The_ticker_is_not_in_AAII_df_or_is_ETF"
    continue

  # Some tickers in the AAII tickerlist have spaces...Skip processsing those tickers for now
  # todo : (Not sure if they are useful stocks to process anyway...but keep on thinking)
  if (len(re.findall('\s', ticker)) > 0):
    if (use_tickers_from_aaii_file == 1):
      logging.warning("The ticker : " + str(ticker) + ", has spaces in the aaii ticker list, Will skip processing this ticker. Skipping...")
      skipped_tickers_df.loc[ticker, 'Reason'] = "The_ticker_name_has_spaces"
      continue
    else:
      logging.error("The ticker : " + str(ticker) + ", has spaces. Please correct and rerun")
      sys.exit(1)

  # ---------------------------------------------------------
  # Get the ticker information in series from the various AAII df
  # ---------------------------------------------------------
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
  # ---------------------------------------------------------

  # ===========================================================================
  #                        PART 1
  #  Process the various series that have been read in to prepare the dataframes
  #  for Key Statistics,financial qtr and financial yr data
  #
  # In PART 2 : These dataframes are then merged with the alread existing data
  #             in the respective ticker csv file
  # ===========================================================================
  # ---------------------------------------------------------------------------
  # Prepare the dataframe for Key Statistics
  # ---------------------------------------------------------------------------
  logging.debug("")
  logging.debug("=======================================")
  logging.debug("Preparing Key Statistics Data ")
  logging.debug("=======================================")
  aaii_key_statistics_df = pd.DataFrame(columns=['AAII_KEY_STATISTICS_DATA'])
  aaii_key_statistics_df.set_index(['AAII_KEY_STATISTICS_DATA'], inplace=True)
  qtr_idx = qtr_str_list[0] # this should always translate to Q1
  most_recent_qtr_date_str = aaii_date_and_misc_series['Ending date ' + str(qtr_idx)]
  try:
    dt.datetime.strptime(str(most_recent_qtr_date_str), '%Y-%m-%d %H:%M:%S').date()
  # except:
  except ValueError:
    logging.warning("Ticker : " + str(ticker) + ", has date for : " + str(qtr_idx) + ", as : " + str(most_recent_qtr_date_str) + ", which does not follow the format %Y-%m-%d %H:%M:%S")
    logging.warning("Will skip processing " + str(ticker) + "  and move on to the next one. Skipping...")
    skipped_tickers_df.loc[ticker, 'Reason'] = "The_ticker_date_" + str(qtr_idx) + "_which_is_" + str(most_recent_qtr_date_str) + "_does_not_follow_the_format_%Y-%m-%d %H:%M:%S"
    continue

  most_recent_qtr_date_dt = dt.datetime.strptime(str(most_recent_qtr_date_str), '%Y-%m-%d %H:%M:%S').date()
  most_recent_qtr_date_str = most_recent_qtr_date_dt.strftime('%m/%d/%Y')
  logging.debug("The most recent qtr date is : " + str(most_recent_qtr_date_str))
  aaii_key_statistics_df.assign(most_recent_qtr_date_str = "")
  aaii_key_statistics_df.loc['No_of_Employees', most_recent_qtr_date_str] = aaii_date_and_misc_series['Number of employees']
  aaii_key_statistics_df.loc['No_of_Institutions', most_recent_qtr_date_str] = aaii_date_and_misc_series['Institutional shareholders']
  aaii_key_statistics_df.loc['Net_Insider_Purchases', most_recent_qtr_date_str] = aaii_date_and_misc_series['Insiders--net shares purchased']
  aaii_key_statistics_df.loc['Institutional_Ownership', most_recent_qtr_date_str] = aaii_date_and_misc_series['Institutional Ownership %']
  aaii_key_statistics_df.loc['Insider_Ownership', most_recent_qtr_date_str] = aaii_date_and_misc_series['Insider Ownership %']

  logging.debug("")
  logging.debug("The Key Statistics DF Prepared from AAII Data is \n" + aaii_key_statistics_df.to_string() + "\n")
  logging.info("Read in Key Statistics data from AAII file")
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Prepare the dataframe for Financials qtr
  # ---------------------------------------------------------------------------
  logging.debug("")
  logging.debug("=======================================")
  logging.debug("Preparing QTR Data ")
  logging.debug("=======================================")
  aaii_qtr_df = pd.DataFrame(columns=['AAII_QTR_DATA'])
  aaii_qtr_df.set_index(['AAII_QTR_DATA'], inplace=True)
  for qtr_idx in qtr_str_list:
    aaii_qtr_date_str = aaii_date_and_misc_series['Ending date ' + str(qtr_idx)]
    logging.debug("Getting Quarterly data from AAII file for : " + str(qtr_idx) + ", which corresponds to date : " + str(aaii_qtr_date_str))
    # Provess only of the date is available in the AAII file
    if not ((str(aaii_qtr_date_str) == 'NaT') or (len(str(aaii_qtr_date_str)) == 0)):
      tmp_date_dt =  dt.datetime.strptime(str(aaii_qtr_date_str),'%Y-%m-%d %H:%M:%S').date()
      tmp_date_str =  tmp_date_dt.strftime('%m/%d/%Y')
      # This add a new column corresponding to the qtr date
      aaii_qtr_df.assign(tmp_date_str = "")
      # These add rows/index for the corresponding dates (which are the columns columns - as added one by one in the above line)
      aaii_qtr_df.loc['Revenue', tmp_date_str] = aaii_financials_qtr_series['Sales '+str(qtr_idx)]
      aaii_qtr_df.loc['Inventory', tmp_date_str] = aaii_financials_qtr_series['Inventory '+str(qtr_idx)]
      aaii_qtr_df.loc['Diluted_EPS', tmp_date_str] = aaii_financials_qtr_series['EPS-Diluted '+str(qtr_idx)]
      aaii_qtr_df.loc['Shares_Diluted', tmp_date_str] = aaii_financials_qtr_series['Shares Diluted '+str(qtr_idx)]
      aaii_qtr_df.loc['Current_Assets', tmp_date_str] = aaii_financials_qtr_series['Current assets '+str(qtr_idx)]
      aaii_qtr_df.loc['Current_Liabilities', tmp_date_str] = aaii_financials_qtr_series['Current liabilities '+str(qtr_idx)]
      aaii_qtr_df.loc['Total_Assets', tmp_date_str] = aaii_financials_qtr_series['Total assets '+str(qtr_idx)]
      aaii_qtr_df.loc['Goodwill_Intangibles', tmp_date_str] = aaii_financials_qtr_series['Goodwill and intangibles '+str(qtr_idx)]
      aaii_qtr_df.loc['Total_Liabilities', tmp_date_str] = aaii_financials_qtr_series['Total liabilities '+str(qtr_idx)]
      aaii_qtr_df.loc['LT_Debt', tmp_date_str] = aaii_financials_qtr_series['Long-term debt '+str(qtr_idx)]
    else:
      logging.warning("Ticker : " + str(ticker) + ", has date for : " + str(qtr_idx) + ", which is either NaT or empty. Please check the AAII Data. ")
      logging.warning("This can happen if the company is a recent IPO in the last few years and does not have all the data")
      logging.warning("Will continue with whatever quarters of data is available")
      continue

  logging.debug("")
  logging.debug("The QTR DF Prepared from AAII Data is \n" + aaii_qtr_df.to_string() + "\n")
  # -------------------------------------------------------
  # Do a sanity check here to ensure that the qtr dates are
  # atleast 80 days apart but no more than 100 days apart
  # -------------------------------------------------------
  qtr_date_list = aaii_qtr_df.columns.tolist()
  qtr_date_list_dt = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in qtr_date_list]
  for date_idx in range(len(qtr_date_list_dt)-1):
    curr_qtr_date_dt = qtr_date_list_dt[date_idx]
    prev_qtr_date_dt = qtr_date_list_dt[date_idx + 1]
    diff_days = (curr_qtr_date_dt - prev_qtr_date_dt).days
    logging.debug("Comparing successive QTR dates : " + str(prev_qtr_date_dt) + " and : " + str(curr_qtr_date_dt) + " and the number of days b/w them are " + str(diff_days))
    if (diff_days > 100) or (diff_days < 80):
      logging.warning(str(ticker) + ": The two successive QTR dates in the AAII QTR df : " + str(prev_qtr_date_dt) + " and : " + str(curr_qtr_date_dt) + " are : " + str(diff_days) + " days apart")
      logging.warning(str(ticker) + ": They should be either less than 100 days or more than 80 days apart. This should not happen and can point to an error in AAII data. Please check")
      tickers_with_irregular_report_dates_df.loc[ticker, 'Reason'] = "qtr_dates_are_" + str(diff_days) + "_days_apart"
      # if ticker in aaii_qtr_or_yr_report_dates_too_far_apart:
      #   logging.error(str(ticker) + ": Since " + str(ticker) + " is in the list of already knows stocks that have somewhat inconsistent report dates, so will contiue")
      # else:
      # continue
      # logging.error("Exiting...")
      # sys.exit(1)

  logging.info("Read in QTR data from AAII file")
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Prepare the dataframe for Financials YR
  # ---------------------------------------------------------------------------
  logging.debug("")
  logging.debug("=======================================")
  logging.debug("Preparing YR Data ")
  logging.debug("=======================================")
  aaii_yr_df = pd.DataFrame(columns=['AAII_YR_DATA'])
  aaii_yr_df.set_index(['AAII_YR_DATA'], inplace=True)
  for yr_idx in yr_str_list:
    aaii_yr_date_str = aaii_date_and_misc_series['Ending date ' + str(yr_idx)]
    logging.debug("Getting Yearly data from AAII file for : " + str(yr_idx) + ", which corresponds to date : " + str(aaii_yr_date_str))
    if not ((str(aaii_yr_date_str) == 'NaT') or (len(str(aaii_yr_date_str)) == 0)):
      tmp_date_dt = dt.datetime.strptime(str(aaii_yr_date_str),'%Y-%m-%d %H:%M:%S').date()
      tmp_date_str =  tmp_date_dt.strftime('%m/%d/%Y')
      # This add a new column corresponding to the yr date str
      aaii_yr_df.assign(tmp_date_str = "")
      # These add rows/index for the corresponding dates (which are the columns columns - as added one by one in the above line)
      aaii_yr_df.loc['Revenue', tmp_date_str] = aaii_financials_yr_series['Sales '+str(yr_idx)]
      aaii_yr_df.loc['Net_Income', tmp_date_str] = aaii_financials_yr_series['Net income '+str(yr_idx)]
      aaii_yr_df.loc['Diluted_EPS', tmp_date_str] = aaii_financials_yr_series['EPS-Diluted '+str(yr_idx)]
      aaii_yr_df.loc['Cash_from_Operations', tmp_date_str] = aaii_financials_yr_series['Cash from operations '+str(yr_idx)]
      aaii_yr_df.loc['Capital_Expenditures', tmp_date_str] = aaii_financials_yr_series['Capital expenditures '+str(yr_idx)]
      aaii_yr_df.loc['Shares_Diluted', tmp_date_str] = aaii_financials_yr_series['Shares Diluted '+str(yr_idx)]
      aaii_yr_df.loc['LT_Debt', tmp_date_str] = aaii_financials_yr_series['Long-term debt '+str(yr_idx)]
      aaii_yr_df.loc['Total_Assets', tmp_date_str] = aaii_financials_yr_series['Total assets '+str(yr_idx)]
      aaii_yr_df.loc['Goodwill_Intangibles', tmp_date_str] = aaii_financials_yr_series['Goodwill and intangibles '+str(yr_idx)]
      aaii_yr_df.loc['Total_Liabilities', tmp_date_str] = aaii_financials_yr_series['Total liabilities '+str(yr_idx)]
    else:
      logging.warning("Ticker : " + str(ticker) + ", has date for : " + str(yr_idx) + ", which is either NaT or empty. Please check the AAII Data. ")
      logging.warning("This can happen if the company is a recent IPO in the last few years and does not have all the data")
      logging.warning("Will continue with whatever years of data is available")
      continue
      # sys.exit(1)

  logging.debug("")
  logging.debug("The YR DF Prepared from AAII Data is \n" + aaii_yr_df.to_string() + "\n")
  # -------------------------------------------------------
  # Do a couple of sanity checks here:
  # 1. Check if there is at least one valid date in AAII df and
  # 2. Ensure that the yr dates are  at least 358 days apart
  #    but no more than 372 days apart
  # -------------------------------------------------------
  # Do another sanity check to make sure that the YR df has some data otherwise skip
  if (len(aaii_yr_df.columns.tolist()) == 0):
    logging.warning(str(ticker) + " AAII YR does not have any columns - meaning that it does not have any valid dates. Skipping...")
    skipped_tickers_df.loc[ticker, 'Reason'] = "No_valid_yr_Dates_found_in_AAII_Data"
    continue

  yr_date_list = aaii_yr_df.columns.tolist()
  yr_date_list_dt = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in yr_date_list]
  for date_idx in range(len(yr_date_list_dt)-1):
    curr_yr_date_dt = yr_date_list_dt[date_idx]
    prev_yr_date_dt = yr_date_list_dt[date_idx + 1]
    diff_days = (curr_yr_date_dt - prev_yr_date_dt).days
    logging.debug("Comparing successive YR dates : " + str(prev_yr_date_dt) + " and : " + str(curr_yr_date_dt) + " and the number of days b/w them are " + str(diff_days))
    if (diff_days > 372) or (diff_days < 358):
      logging.warning(str(ticker) + ": The two successive YR dates in the AAII YR df : " + str(prev_yr_date_dt) + " and : " + str(curr_yr_date_dt) + " are : " + str(diff_days) + " days apart")
      logging.warning(str(ticker) + ": They should be either less than 372 days or more than 358 days apart. This should not happen and can point to an error in AAII data. Please check")
      tickers_with_irregular_report_dates_df.loc[ticker, 'Reason'] = "yr_dates_are_" + str(diff_days) + "_days_apart"
      # if ticker in aaii_qtr_or_yr_report_dates_too_far_apart:
      #   logging.error(str(ticker) + ": Since " + str(ticker) + " is in the list of already knows stocks that have somewhat inconsistent report dates, so will contiue")
      # else:
      # continue
        # logging.error("Exiting...")
        # sys.exit(1)

  logging.info("Read in YR data from AAII file")
  # ---------------------------------------------------------------------------

  # ===========================================================================
  #                PART 2 - Read the already existing Analysis Data
  #                   and merge it with created AAII Analysis Data
  # ===========================================================================
  # todo : Check if the data merges alright
  #   ticker csv has less cols    : Need to check if aaii date cols get inserted
  #   ticker csv has more cols    : Need to check if aaii date cols get inserted and ticker already existing cols don't get affected
  #   ticker csv has equal cols   : Need to change the data and see if the data is corrected from AAII
  #   ticker csv has less rows    : Works
  #   ticker csv has more rows    : Error flagged
  #   ticker csv has equal rows   : Need to change the data and see if the data is corrected from AAII

  logging.debug("")
  logging.debug("==============================================================================================================")
  logging.info("Now merging/creating(if the data does not exist) the Key Statistics, QTR and YR data into already existing file")
  logging.debug("==============================================================================================================")

  # Read the appropriate file
  for qtr_yr_idx in ['key_statistics','qtr','yr']:
    logging.debug("")
    logging.debug("=======================================")
    logging.debug("Staring the merge/create for " + str(qtr_yr_idx).upper())
    logging.debug("=======================================")
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

    # if ticker csv exists, then merge aaii df with it, else put aaii df in new ticker csv file
    if (os.path.exists(ticker_csv_filepath + "\\" + ticker_csv_filename) is True):
      ticker_csv_df = data = pd.read_csv(ticker_csv_filepath + "\\" + ticker_csv_filename)
      logging.info("File "  + str(ticker_csv_filename) + " exists. Will read-in and merge the latest AAII data into it")
      ticker_csv_df.set_index("AAII_" + str(qtr_yr_idx).upper() + "_DATA", inplace=True)
      logging.debug("\n\nThe Ticker df as read from the ticker csv file : \n" + ticker_csv_df.to_string() + "\n")
      logging.debug("Will now check for all the rows and column in aaii df and see if they exist in ticker df")
      logging.debug("If the are present in both, then will replace that data with AAII data - assumption being that AAII might have updated data meanwhile - company restated etc...")
      logging.debug("If they are present only in AAII, then will insert them in the ticker df because ticker df is lacking those rows/columns b/c AAII has the latest data (from 2020 while ticker df only has data till 2019 etc)")
      logging.debug("If they are present only in ticker df, then that data will be left as is. The most common reason for this is that ticker df has 2012 data while AAII start from 2013")
      logging.debug("")

      # -----------------------------------------------------------------------
      # Start the process of comparing aaii df rows and columns with
      # ticker csv df rows and columns respectively
      # -----------------------------------------------------------------------

      # -----------------------------------------------------------------------
      #         ##########     Work on Rows     ##########
      # -----------------------------------------------------------------------
      # Iterate through the rows for aaii_df and ticker csv
      # to find out if there are row(s) in aaii_df that are not in ticker csv.
      # If so then aapend that row(s) to ticker df
      # -----------------------------------------------------------------------
      logging.debug("Checking for rows (in order to insert rows, if aaii df has additional rows as compared to ticker df...")
      logging.debug("")
      common_rows = []
      different_rows = []
      aaii_df_rows_list = aaii_df.index.tolist()
      ticker_csv_df_rows_list = ticker_csv_df.index.tolist()
      logging.debug("The rows in aaii df   : " + str(sorted(aaii_df_rows_list)))
      logging.debug("The rows in ticker df : " + str(sorted(ticker_csv_df_rows_list)))
      logging.debug("")

      # -----------------------------------------------------------------------
      # This case should not happen - There should not be more rows in the ticker df
      # as compared to aaii df - That means that Sundeep modified AAII Investor Pro data
      # to download fewer rows or AAII Investor Pro deleted a a row (or renamed it). That
      # needs to be dealt with separately from this script. For now exit.
      # After thinking some more - (but right now leave it as is -- sys.exit)
      # One other alternative is to save that row data and then merge with the
      # dataframe later after aaii data has merged but more than likely we should
      # not end up in a situation like this, so sys.exit for now here.
      # Another option is the delete that row from the ticker df - this will
      # permanently delete that row from ticker csv as well - when it gets
      # written later in the script (That is a cheap way of cleaning up the
      # ticker csv file)
      # maybe make a list ignore_ticker_row_list / delete_ticker_cs_row_list
      # ----------------------------------------------------------------------
      if (len(ticker_csv_df_rows_list)) > len(aaii_df_rows_list):
        logging.error("The number of rows in ticker df : " + str(len(ticker_csv_df_rows_list)))
        logging.error("The number of rows in aaii   df : " + str(len(aaii_df_rows_list)))
        logging.error("Since the number of rows in ticker df is greater than the number of rows in aaii df")
        logging.error("that row(s) data will most likely be overwritten to NaN during the col. merge ")
        logging.error("Please correct the situation and rerun - Either remove the additional rows from ticker df or most likely download that row data in the aaii file")
        logging.error("Exiting...")
        sys.exit(1)

      # -----------------------------------------------------------------------
      # Dummy row is needed if there are more rows in aaii df and we need to add
      # row(s) to ticker df in the loop below
      # -----------------------------------------------------------------------
      ticker_csv_df_cols_list = ticker_csv_df.columns.tolist()
      dummy_list = []
      # This creates a dummy list with the number of elements equal to
      # the number of columns in the ticker df
      for col_idx in range(len(ticker_csv_df_cols_list)):
        dummy_list.append(float('nan'))

      for row_val in aaii_df_rows_list:
        if row_val in ticker_csv_df_rows_list:
          logging.debug("Row --> " + str(row_val) + " <-- is present in both AAII df and ticker df. Will replace that row data in ticker df with latest data from AAII df later...")
          common_rows.append(row_val)
        else:
          logging.debug("Row --> " + str(row_val) + " <-- is present ONLY in AAII df. Inserting the row in ticker df with dummy data for now ")
          different_rows.append(row_val)
          # Add a dummy row to the ticker df. This will get populated with aaii data later
          ticker_csv_df = ticker_csv_df.append(pd.Series(dummy_list, index=ticker_csv_df.columns, name=row_val))
      logging.debug("")
      logging.debug("The common rows b/w the ticker and aaii df are : \n" + str(common_rows))
      logging.debug("")
      logging.debug("The different rows b/w the ticker and aaii df are : \n" + str(different_rows))
      logging.debug("The ticker df after potentially inserting new rows : \n"  + ticker_csv_df.to_string() + "\n")
      # -----------------------------------------------------------------------

      # -----------------------------------------------------------------------
      #         ##########     Now work on columns     ##########
      # -----------------------------------------------------------------------
      logging.debug("")
      logging.debug("Checking for columns b/w aaii and ticker df")
      logging.debug("If there are common cols. then will delete them for ticker df and will insert from aaii later with latest data")
      logging.debug("The cols that are not common b/w aaii and ticker df, then the ticker df cols will be left untouched")
      ticker_csv_df_cols_list = ticker_csv_df.columns.tolist()
      aaii_df_cols_list = aaii_df.columns.tolist()
      aaii_datelist_dt = sorted([dt.datetime.strptime(date, '%m/%d/%Y').date() for date in aaii_df_cols_list], reverse=True)
      ticker_datelist_dt = sorted([dt.datetime.strptime(date, '%m/%d/%Y').date() for date in ticker_csv_df_cols_list], reverse=True)
      logging.debug("The columns in aaii df   : " + str(aaii_datelist_dt))
      logging.debug("The columns in ticker df : " + str(ticker_datelist_dt))
      logging.debug("The latest date in aaii   df : " + str(aaii_datelist_dt[0]))
      logging.debug("The latest date in ticker df : " + str(ticker_datelist_dt[0]))

      # ---------------------------------------------------
      # Chedk if there are any aaii dates are newer(later)
      # than the latest date in ticker dates.
      # If so, then add the ticker name to the
      # new_dates_in_aaii_list. That list will be used
      # later to populate the logfile
      # ---------------------------------------------------
      new_dates_in_aaii_list = []
      for aaii_cols_idx in range(len(aaii_datelist_dt)):
        if (aaii_datelist_dt[aaii_cols_idx] > ticker_datelist_dt[0]):
          logging.debug("The date in AAII df : " + str(aaii_datelist_dt[aaii_cols_idx]) + " is newer than the latest date available in ticker df " + str(ticker_datelist_dt[0]))
          new_dates_in_aaii_list.append(dt.datetime.strftime(aaii_datelist_dt[aaii_cols_idx], '%m/%d/%Y'))
      # ---------------------------------------------------

      # -----------------------------------------------------------------------
      # Iterate through the columns for ticker_df_cols
      # if there are common cols, then delete that col from ticker df as they
      # will get replaced by the aaii columns with latest data later
      # Sundeep : The only hazard here is if AAII datas changed by a few days for
      # past qtr/yr then it will not be deleted and then we will have two qtr/yrs
      # that will be very close together...I haven't seen that yet, but maybe that
      # will appear in the charts (0_Analysis Chart) and then deal with it
      # -----------------------------------------------------------------------
      common_cols = []
      for ticker_cols_idx in range(len(ticker_csv_df_cols_list)) :
        ticker_col_val_org = ticker_csv_df_cols_list[ticker_cols_idx]
        ticker_col_val_dt = dt.datetime.strptime(ticker_col_val_org, '%m/%d/%Y').date()
        ticker_col_val = dt.datetime.strftime(ticker_col_val_dt, '%m/%d/%Y')
        if ticker_col_val_dt in aaii_datelist_dt:
          logging.debug("Column --> " + str(ticker_col_val_org) + " <-- is present in both AAII df and ticker df")
          logging.debug("Will delete " + str(ticker_col_val_org) + " column in ticker df and will replace it with latest data from AAII df later...")
          del ticker_csv_df[ticker_col_val_org]
          common_cols.append(ticker_col_val)
      logging.debug("")
      logging.debug("The common cols b/w the ticker and aaii df are " + str(common_cols))
      logging.debug("The ticker df after potentially inserting new rows and deleting common cols : \n"  + ticker_csv_df.to_string() + "\n")
      # -----------------------------------------------------------------------


      # -----------------------------------------------------------------------
      # At this point :
      # 1. The rows that were present in aaii and not in ticker df have been
      #     inserted in ticker df with dummy data
      # 2. The common cols from the ticker df are deleted, so all cols from aaii
      #     can be safely inserted here (they are supposedly going to have the
      #     latest data)
      # -----------------------------------------------------------------------
      # Copy all the cols from aaii df into ticker df here
      for aaii_col_val in aaii_df_cols_list:
        ticker_csv_df[aaii_col_val] = aaii_df[aaii_col_val]
      logging.debug("\n\nThe Ticker df after copying the latest from aaii df : \n" + ticker_csv_df.to_string() + "\n")
      # -----------------------------------------------------------------------

      # -----------------------------------------------------------------------
      # Now sort the ticker columns descending based on dates and write it to csv
      # -----------------------------------------------------------------------
      # Don't understand how this works...but it works
      ticker_csv_df = ticker_csv_df.iloc[:, pd.to_datetime(ticker_csv_df.columns, format='%m/%d/%Y').argsort()[::-1]].reset_index()
      ticker_csv_df.set_index("AAII_" + str(qtr_yr_idx).upper() + "_DATA", inplace=True)
      ticker_csv_df.sort_index(ascending=True,inplace=True)
      logging.debug("\n\nThe Ticker df after sorting by rows (ascending) column dates (descending)  \n" + ticker_csv_df.to_string() + "\n")
      ticker_csv_df.to_csv(ticker_csv_filepath + "\\" + ticker_csv_filename, sep=',', index=True, header=True)
      logging.debug("Done with merging ticker and aaii df for : " + str(qtr_yr_idx).upper())
      logging.debug("")
      # Now prepare dataframes for logfiles
      if (len(new_dates_in_aaii_list) > 0):
        logging.info("---> " + str(ticker) + " : Newly available AAII " + str(qtr_yr_idx).upper() + "  data for dates : " +str(new_dates_in_aaii_list) + " was added to ticker df")
        if (qtr_yr_idx == 'qtr'):
          ticker_qtr_updated_with_new_dates_from_aaii_df.loc[ticker, 'Updated_Data_Type'] = str(qtr_yr_idx).upper()
          ticker_qtr_updated_with_new_dates_from_aaii_df.loc[ticker, 'Reason'] = "Yes_New_AAII_" + str(qtr_yr_idx).upper() + "_data_for_dates_" +str(new_dates_in_aaii_list) + "_was_added_to_ticker_df"
        elif (qtr_yr_idx == 'yr'):
          ticker_yr_updated_with_new_dates_from_aaii_df.loc[ticker, 'Updated_Data_Type'] = str(qtr_yr_idx).upper()
          ticker_yr_updated_with_new_dates_from_aaii_df.loc[ticker, 'Reason'] = "Yes_New_AAII_" + str(qtr_yr_idx).upper() + "_data_for_dates_" + str(new_dates_in_aaii_list) + "_was_added_to_ticker_df"
      else:
        logging.debug(str(ticker) + " : No new dates were avaialable in AAII " + str(qtr_yr_idx).upper() + "  data. So the ticker csv was updated with the available AAII data")
        if (qtr_yr_idx == 'qtr'):
          ticker_qtr_NOT_updated_with_new_dates_from_aaii_df.loc[ticker, 'Updated_Data_Type'] = str(qtr_yr_idx).upper()
          ticker_qtr_NOT_updated_with_new_dates_from_aaii_df.loc[ticker, 'Reason'] = "No_new_dates_were_available_for_" + str(qtr_yr_idx).upper() + "_So_ticker_csv_was_updated_with_the_available_AAII_data"
        elif (qtr_yr_idx == 'yr'):
          ticker_yr_NOT_updated_with_new_dates_from_aaii_df.loc[ticker, 'Updated_Data_Type'] = str(qtr_yr_idx).upper()
          ticker_yr_NOT_updated_with_new_dates_from_aaii_df.loc[ticker, 'Reason'] = "No_new_dates_were_available_for_" + str(qtr_yr_idx).upper() + "_So_ticker_csv_was_updated_with_the_available_AAII_data"
    else:
      logging.info("File "  + str(ticker_csv_filename) + " does not exist. Will create anew and write the latest AAII data - with rows sorted in ascending order - into it")
      aaii_df.sort_index(ascending=True,inplace=True)
      aaii_df.to_csv(ticker_csv_filepath + "\\" + ticker_csv_filename, sep=',', index=True, header=True)
      new_csv_file_created_df.loc[ticker, 'Reason'] = "No_old_ticker_cs_file_existed"

      # -----------------------------------------------------------------------
  i_idx += 1

    # This works
    # Try access the dataframe element by element - this can be used later
    # ticker_csv_df_cols_list = ticker_csv_df.columns.tolist()
    # ticker_csv_df_rows_list = ticker_csv_df.index.tolist()
    # for rows_idx in ticker_csv_df_rows_list:
    #   for  aaii_cols_idx in ticker_csv_df_cols_list:
    #     logging.debug("Row : " + str(rows_idx) + ", Column : " + str(aaii_cols_idx) + ", Value : " + str(ticker_csv_df.loc[rows_idx,aaii_cols_idx]))

# -----------------------------------------------------------------------------
logging.info("")
logging.info("Total Number of tickers in the list                               : " + str(total_number_of_ticker))
logging.info("Skipped tickers                                                   : " + str(len(skipped_tickers_df.index.tolist())))
logging.info("Tickers with irregular report dates                               : " + str(len(tickers_with_irregular_report_dates_df.index.tolist())))
logging.info("Tickers for which brand new csv was created                       : " + str(len(new_csv_file_created_df.index.tolist())))
logging.info("Tickers for which AAII has new dates for qtr                      : " + str(len(ticker_qtr_updated_with_new_dates_from_aaii_df.index.tolist())))

# -----------------------------------------------------------------------------
# If the tickers dates were updated for both qtr and yr, then remove it
# from qtr - as it just clutters the csv with duplicate names.
# -----------------------------------------------------------------------------
if ((len(ticker_qtr_updated_with_new_dates_from_aaii_df.index.tolist()) > 0) and (len(ticker_yr_updated_with_new_dates_from_aaii_df.index.tolist()) > 0)):
  updated_qtr_dates_ticker_list = ticker_qtr_updated_with_new_dates_from_aaii_df.index.tolist()
  updated_yr_dates_ticker_list = ticker_yr_updated_with_new_dates_from_aaii_df.index.tolist()
  for updated_yr_dates_ticker in updated_yr_dates_ticker_list:
    if updated_yr_dates_ticker in updated_qtr_dates_ticker_list:
      logging.debug(str(updated_yr_dates_ticker) + " has both the qtr and yr dates updated, Deleting it from ticker_qtr_updated_with_new_dates_from_aaii_df")
      ticker_qtr_updated_with_new_dates_from_aaii_df.drop(index= [updated_yr_dates_ticker], inplace=True)
# -----------------------------------------------------------------------------

logging.info("Tickers for which AAII has new dates for yr                       : " + str(len(ticker_yr_updated_with_new_dates_from_aaii_df.index.tolist())))
logging.info("Unique Tickers with dates for qtr (after removing common w/yr)    : " + str(len(ticker_qtr_updated_with_new_dates_from_aaii_df.index.tolist())))
logging.info("Tickers for which AAII DID NOT have new dates for qtr             : " + str(len(ticker_qtr_NOT_updated_with_new_dates_from_aaii_df.index.tolist())))
logging.info("Tickers for which AAII DID NOT have new dates for yr              : " + str(len(ticker_yr_NOT_updated_with_new_dates_from_aaii_df.index.tolist())))
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Print the information into various logfiles
# -----------------------------------------------------------------------------
skipped_tickers_logfile="SC_parse_AAII_skipped_tickers.csv"
tickers_with_irregular_report_dates_logfile="SC_parse_AAII_tickers_with_irregular_report_dates.csv"
new_csv_file_created_tickers_logfile="SC_parse_AAII_new_csv_file_created_tickers.csv"

ticker_updated_with_new_dates_from_aaii_logfile="SC_parse_AAII_was_ticker_updated_with_new_dates_from_aaii.csv"
ticker_NOT_updated_with_new_dates_from_aaii_logfile="SC_parse_AAII_was_ticker_NOT_updated_with_new_dates_from_aaii.csv"

skipped_tickers_df.sort_values(by=['Ticker'], ascending=[True]).to_csv(dir_path + log_dir + "\\" + skipped_tickers_logfile,sep=',', index=True, header=True)
tickers_with_irregular_report_dates_df.sort_values(by=['Ticker'], ascending=[True]).to_csv(dir_path + log_dir + "\\" + tickers_with_irregular_report_dates_logfile,sep=',', index=True, header=True)
new_csv_file_created_df.sort_values(by=['Ticker'], ascending=[True]).to_csv(dir_path + log_dir + "\\" + new_csv_file_created_tickers_logfile, sep=',', index=True, header=True)

ticker_qtr_updated_with_new_dates_from_aaii_df.sort_values(by=['Ticker'], ascending=[True]).to_csv(dir_path + log_dir + "\\" + ticker_updated_with_new_dates_from_aaii_logfile, sep=',', index=True, header=True)
ticker_yr_updated_with_new_dates_from_aaii_df.sort_values(by=['Ticker'], ascending=[True]).to_csv(dir_path + log_dir + "\\" + ticker_updated_with_new_dates_from_aaii_logfile, mode='a',sep=',', index=True, header=False)

ticker_qtr_NOT_updated_with_new_dates_from_aaii_df.sort_values(by=['Ticker'], ascending=[True]).to_csv(dir_path + log_dir + "\\" + ticker_NOT_updated_with_new_dates_from_aaii_logfile, sep=',', index=True, header=True)
ticker_yr_NOT_updated_with_new_dates_from_aaii_df.sort_values(by=['Ticker'], ascending=[True]).to_csv(dir_path + log_dir + "\\" + ticker_NOT_updated_with_new_dates_from_aaii_logfile, mode='a', sep=',', index=True, header=False)
# -----------------------------------------------------------------------------

logging.info("")
logging.info("All Done...")
