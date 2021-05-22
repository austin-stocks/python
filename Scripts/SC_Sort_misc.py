import pandas as pd
import os
import sys
import time
import datetime as dt
import numpy as np
import logging
import math
import re

def check_list_elements_with_val(list1, val):
  # traverse in the list
  for x in list1:
    # compare with all the values with val
    if val >= x:
      return False
  return True

# -----------------------------------------------------------------------------
# Read the master tracklist file into a dataframe
# -----------------------------------------------------------------------------
dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
log_dir = "\\..\\" + "Logs"
chart_dir = "\\..\\" + "Charts"
my_linear_chart_dir = chart_dir + "\\" + "Linear" + "\\" + "Charts_With_Numbers"
earnings_dir = "\\..\\" + "Earnings"
historical_dir = "\\..\\" + "Historical"
master_tracklist_file = "Master_Tracklist.xlsx"
master_tracklist_df = pd.read_excel(dir_path + user_dir + "\\" + master_tracklist_file, sheet_name="Main")
master_tracklist_df.sort_values('Tickers', inplace=True)
ticker_list_unclean = master_tracklist_df['Tickers'].tolist()
ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']
# The index can only be changed after the Ticker has been put to list
# In other words index cannot be read as a list
master_tracklist_df.set_index('Tickers', inplace=True)
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
# Logging Levels
# Level
# CRITICAL
# ERROR
# WARNING
# INFO
# DEBUG
# NOTSET
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename=dir_path + log_dir + "\\" + 'SC_Sort_misc_debug.txt',
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

# disable and enable global level logging
logging.disable(sys.maxsize)
logging.disable(logging.NOTSET)
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Declare all the dataframes that we are going to need to write into and set their columns
# -----------------------------------------------------------------------------
today = dt.date.today()
one_qtr_ago_date = today - dt.timedelta(days=80)
one_month_ago_date = today - dt.timedelta(days=15)
logging.info("Today : " + str(today) +  " One month ago : " +str(one_month_ago_date) + " One qtr ago : " +str(one_qtr_ago_date))

historical_last_updated_df = pd.DataFrame(columns=['Ticker','Date'])
earnings_last_reported_df = pd.DataFrame(columns=['Ticker','Date','Where_found','Reason'])
eps_projections_last_updated_df = pd.DataFrame(columns=['Ticker','Date','Reason'])
charts_last_updated_df  = pd.DataFrame(columns=['Ticker','Date'])
eps_report_newer_than_eps_projection_df = pd.DataFrame(columns=['Ticker','Actual_EPS_Report','EPS_Projections_Last_Updated'])
skipped_tickers_df = pd.DataFrame(columns=['Ticker','Quality_of_Stock','Reason'])

historical_last_updated_df.set_index('Ticker', inplace=True)
earnings_last_reported_df.set_index('Ticker', inplace=True)
eps_projections_last_updated_df.set_index('Ticker', inplace=True)
charts_last_updated_df.set_index('Ticker', inplace=True)
eps_report_newer_than_eps_projection_df.set_index('Ticker', inplace=True)
skipped_tickers_df.set_index('Ticker', inplace=True)


# last_4_eps_report_dates_list = []
# gt_1_month_old_historical_last_updated_df = pd.DataFrame(columns=['Ticker','Date'])
# gt_1_month_old_eps_projections_last_updated_df = pd.DataFrame(columns=['Ticker','Date'])
# gt_1_qtr_old_eps_projections_last_updated_df = pd.DataFrame(columns=['Ticker','Date'])
# gt_1_month_charts_last_updated_df = pd.DataFrame(columns=['Ticker','Date'])
# gt_1_month_old_historical_last_updated_df.set_index('Ticker', inplace=True)
# gt_1_month_old_eps_projections_last_updated_df.set_index('Ticker', inplace=True)
# gt_1_qtr_old_eps_projections_last_updated_df.set_index('Ticker', inplace=True)
# gt_1_month_charts_last_updated_df.set_index('Ticker', inplace=True)
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Loop through all the tickers
# -----------------------------------------------------------------------------
# ticker_list = ['AUDC', 'MED']
i_int = 1
for ticker_raw in ticker_list:
  ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase
  logging.debug("================================")
  logging.info("Iteration # " + str(i_int).ljust(3) + ", Processing : " + str(ticker))
  i_int += 1
  # if ticker in ["CCI", , "CY", "EXPE", "FLS", "GCBC","GOOG","HURC","KMI","KMX","PNFP","QQQ","RCMT","TMO","TMUS","TTWO",,"WLTW"]:
  quality_of_stock = master_tracklist_df.loc[ticker, 'Quality_of_Stock']
  if ticker in ["QQQ"]:
    skipped_tickers_df.loc[ticker,'Quality_of_Stock'] = quality_of_stock
    skipped_tickers_df.loc[ticker,'Reason'] = "Is_ETF"
    continue
  if ((quality_of_stock != 'Wheat') and (quality_of_stock != 'Wheat_Chaff') and (quality_of_stock != 'Essential') and (quality_of_stock != 'Sundeep_List')):
  # if ((quality_of_stock != 'Wheat')):
    logging.info(str(ticker) + " is not Wheat...skipping")
    skipped_tickers_df.loc[ticker,'Quality_of_Stock'] = quality_of_stock
    skipped_tickers_df.loc[ticker,'Reason'] = "neither_Wheat_nor_Wheat_Chaff_nor_Essential_nor_Sundeep_List"
    continue
  if ticker in ["BRK.B"]:
    skipped_tickers_df.loc[ticker,'Quality_of_Stock'] = quality_of_stock
    skipped_tickers_df.loc[ticker,'Reason'] = "Berkshire"
    continue
  if ticker in ["JEF"]:
    skipped_tickers_df.loc[ticker,'Quality_of_Stock'] = quality_of_stock
    skipped_tickers_df.loc[ticker,'Reason'] = '     =====> Need_to_sort_out_mismatch_between_fiscal_year_and_earnings_report_date'
    continue
  if ticker in ["NTES"]:
    skipped_tickers_df.loc[ticker,'Quality_of_Stock'] = quality_of_stock
    skipped_tickers_df.loc[ticker,'Reason'] = '     =====> Need_to_sort_out_mismatch_report_currency_between_CNBC_and_Ann'
    continue
  if (ticker in ['FOX','TAYD', 'CRVL', 'WILC', 'WINA', 'GCBC']):
    skipped_tickers_df.loc[ticker,'Quality_of_Stock'] = quality_of_stock
    skipped_tickers_df.loc[ticker,'Reason'] = '     =====> No_CNBC_Projections_available._You_should_periodically_check_CNBC'
    continue


  # ---------------------------------------------------------------------------
  # Read the Historical data file and get the last date for which prices are available
  # ---------------------------------------------------------------------------
  historical_df = pd.read_csv(dir_path + historical_dir + "\\" + ticker + "_historical.csv")
  date_str_list = historical_df.Date.tolist()
  date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in date_str_list]
  ticker_adj_close_list = historical_df.Adj_Close.tolist()
  ticker_curr_price = next(x for x in ticker_adj_close_list if not math.isnan(x))
  ticker_curr_date = date_list[ticker_adj_close_list.index(ticker_curr_price)]
  historical_last_updated_df.loc[ticker]= [ticker_curr_date]
  # if the historical data was update more than a month then put it in gt_1_month old
  # if (ticker_curr_date < one_month_ago_date):
  #   logging.debug("Historical Data was last updated on : " + str(ticker_curr_date) + ", more than a month ago")
  #   gt_1_month_old_historical_last_updated_df.loc[ticker]= [ticker_curr_date]
  # ---------------------------------------------------------------------------


  # ---------------------------------------------------------------------------
  # Read the Earnings file to get when the earnings projections were last updated
  # ---------------------------------------------------------------------------
  earnings_file = ticker + "_earnings.csv"
  qtr_eps_df = pd.read_csv(dir_path + earnings_dir + "\\" + earnings_file)

  if 'Q_EPS_Projections_Date_0' in qtr_eps_df.columns:
    eps_projection_date_0 = qtr_eps_df['Q_EPS_Projections_Date_0'].tolist()[0]
    logging.debug("Earnings file : " + str(earnings_file) + ", Projected EPS was last updated on " + str(eps_projection_date_0))
    eps_projection_date_0_dt = dt.datetime.strptime(str(eps_projection_date_0), '%m/%d/%Y').date()
  else:
    logging.error("Column Q_EPS_Projections_Date_0 DOES NOT exist in " + str(earnings_file))
    sys.exit(1)

  # date_year = eps_projection_date_0_dt.year
  # if (date_year < 2019):
  #   logging.error("==========     Error : Seems like the projected EPS date is older than 2019. Please correct and rerun the script")
  #   sys.exit(1)
  if (eps_projection_date_0_dt > dt.date.today()):
    logging.error("  The  Q_EPS_Projections_Date_0 date for " + str(ticker) + " is " + str(eps_projection_date_0_dt) + " which is in future... :-(")
    logging.error("  This seems like a typo :-)...Please correct it in Earnings csv file and rerun")
    sys.exit(1)
  eps_projections_last_updated_df.loc[ticker,'Date']= eps_projection_date_0_dt
  eps_projections_last_updated_df.loc[ticker,'Reason']= master_tracklist_df.loc[ticker, 'Reason_Earnings_Projections_NOT_updated']

  # if (eps_projection_date_0_dt < one_month_ago_date):
  #   logging.debug("Projected EPS were last updated on : " + str(eps_projection_date_0_dt) + ", more than a month ago")
  #   gt_1_month_old_eps_projections_last_updated_df.loc[ticker]= eps_projection_date_0_dt
  #
  # if (eps_projection_date_0_dt < one_qtr_ago_date):
  #   logging.debug("Projected EPS were last updated on : " + str(eps_projection_date_0_dt) + ", more than a quarter ago")
  #   gt_1_qtr_old_eps_projections_last_updated_df.loc[ticker]= eps_projection_date_0_dt
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Get the last earnings report date from earnings file first
  # ---------------------------------------------------------------------------
  eps_actual_report_date = ""
  if ('Q_Report_Date' in qtr_eps_df.columns):
    qtr_eps_report_date_list = qtr_eps_df.Q_Report_Date.dropna().tolist()
    logging.debug("The Quarterly Report Date List from the earnings file after dropna is " + str(qtr_eps_report_date_list))
  if (len(qtr_eps_report_date_list) > 0):
    qtr_eps_report_date_list_dt = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in qtr_eps_report_date_list]
    eps_actual_report_date = qtr_eps_report_date_list_dt[0]
  else:
    earnings_last_reported_df.loc[ticker, 'Where_found'] = 'Master_Tracklist'
    eps_actual_report_date = dt.datetime.strptime(str(master_tracklist_df.loc[ticker, 'Last_Earnings_Date']),'%Y-%m-%d %H:%M:%S').date()

  # Sundeep : 05/22/2021 - This works - I am tring to get the last 4 dates when the company reported
  # I used this to accumlate all the last 4 quarter report dates to find out which are the months that
  # are most busy and which are the months that are least busy for me from the collection of quaterly earnings perspective
  # last_4_eps_report_dates_list.append(qtr_eps_report_date_list_dt[0])
  # last_4_eps_report_dates_list.append(qtr_eps_report_date_list_dt[1])
  # last_4_eps_report_dates_list.append(qtr_eps_report_date_list_dt[2])
  # last_4_eps_report_dates_list.append(qtr_eps_report_date_list_dt[3])
  # logging.debug("The last 4 quarters earnings report date for " + str(ticker) + " are " + str(last_4_eps_report_dates_list[-4:]))

  #
  # try:
  #   eps_actual_report_date = dt.datetime.strptime(str(master_tracklist_df.loc[ticker, 'Last_Earnings_Date']),'%Y-%m-%d %H:%M:%S').date()
  # except:
  #   logging.error("**********************  ERROR ERROR ERROR ERROR ****************************")
  #   logging.error(str(ticker) + " is wheat and does not have a earnings date in the Master Tracklist file. Exiting....")
  #   logging.error("**********************  ERROR ERROR ERROR ERROR ****************************")
  #   sys.exit(1)

  eps_actual_report_date_dt = dt.datetime.strptime(str(eps_actual_report_date), '%Y-%m-%d').date()
  if (eps_actual_report_date_dt > dt.date.today()):
    logging.error("  The Last quarterly earnings date for " + str(ticker) + " is " + str(eps_actual_report_date_dt) + " which is in future... :-(")
    logging.error("  This seems like a typo :-)...Please correct it in Master Tracklist file and rerun")
    sys.exit(1)
  # date_year = eps_actual_report_date_dt.year
  # if (date_year < 2019):
  #   logging.error("==========     Error : The date for " + str(ticker) + " last earnings is older than 2019     ==========")
  #   sys.exit()
  earnings_last_reported_df.loc[ticker,'Date']= eps_actual_report_date_dt

  if (eps_actual_report_date_dt > eps_projection_date_0_dt):
    logging.error("The Earnings report date : " + str(eps_actual_report_date_dt) + " is newer than the earnings projection date : " + str(eps_projection_date_0_dt))
    logging.error("I don't understand how you let it happen - The possible reasons could be ")
    logging.error("1. You forgot to update the Earnings projection on the Earnings report date....Ok. I understand. Plese update the eranings projections now and rerun ")
    logging.error("2. You mistyped the date (either the earnings report date in master tracklist or more likely in for earnings projections in earning file...I understand. It happens sometimes. Please fix and rerun")
    logging.error("3. You did not update the Earnings projection on the Earnings report date intentionally....BAD BAD....How can you do that???? ")
    eps_report_newer_than_eps_projection_df.loc[ticker, 'Actual_EPS_Report'] = eps_actual_report_date_dt
    eps_report_newer_than_eps_projection_df.loc[ticker, 'EPS_Projections_Last_Updated'] = eps_projection_date_0_dt
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Get all the charts in the charts directory for the ticker and find out the
  # chart file with the latest appended date
  # ---------------------------------------------------------------------------
  all_chart_files_list = os.listdir(dir_path + my_linear_chart_dir + "\\")
  logging.debug("The files in the chart directory are" + str(all_chart_files_list))
  my_regex = re.compile(re.escape(ticker) + re.escape("_")  + ".*jpg")
  ticker_chart_files_list = list(filter(my_regex.match, all_chart_files_list)) # Read Note
  logging.debug("The chart file list : " + str(ticker_chart_files_list))

  # For each file split the file name to get the date string.+
  # Then covert the date string to datetime and append it to the list
  ticker_chart_date_list = []
  for ticker_chart_filename in ticker_chart_files_list:
    # Check the length of the filename - it should be number of characters in the ticker and 16
    if len(ticker_chart_filename) > (len(ticker) + 16):
      logging.error("Error : The filename " + str(ticker_chart_filename) + " has more characters than allowed")
      skipped_tickers_df.loc[ticker, 'Quality_of_Stock'] = quality_of_stock
      skipped_tickers_df.loc[ticker, 'Reason'] = "Chart_filename_too_long"
      continue

    # Remove the .jpg at the end and then get the last 10 characters of the filename
    ticker_chart_date_str = (ticker_chart_filename[:-4])[-10:]
    ticker_chart_date_dt = dt.datetime.strptime(ticker_chart_date_str, "%Y_%m_%d")
    logging.debug("The date string for " + str(ticker_chart_filename) + "is " + str(ticker_chart_date_str) + "and the datetime is " + str(ticker_chart_date_dt))
    ticker_chart_date_list.append(ticker_chart_date_dt)

  logging.debug("The datetime list for "+ str(ticker) + " is " + str(ticker_chart_date_list))
  # Sort the list to the get the latest (youngest) datetime
  # and create a string for the ticker filename from the string
  ticker_chart_date_list.sort(reverse=True)
  logging.debug("The datetime SORTED list for " + str(ticker) + " is " + str(ticker_chart_date_list))
  charts_last_updated_df.loc[ticker] = [ticker_chart_date_list[0]]
  # ---------------------------------------------------------------------------

  logging.debug("================================")
  logging.debug("")
  # ---------------------------------------------------------------------------

  # -----------------------------------------------------------------------------
  # Update Reasons for some tickers
  # -----------------------------------------------------------------------------


# Sundeep : 05/22/2021 - This works - search for eps_report_dates_list above and see comments
# there to see how was this used
# logging.debug("The last quarters earnings report date list is " + str(last_4_eps_report_dates_list))
# logging.debug("The last quarters earnings report date list SORTED is " + str(sorted(last_4_eps_report_dates_list)))
# last_4_eps_report_dates_list = sorted(last_4_eps_report_dates_list)
# with open("fout.txt", "w") as fout:
#   print(*last_4_eps_report_dates_list, sep="\n", file=fout)
# -----------------------------------------------------------------------------
# Print all the df to their respective files
# -----------------------------------------------------------------------------
logging.info("")
logging.info("Now saving sorted data in " + str(dir_path + log_dir) + " directory")
logging.info("All the files with sorted data will be available there. Please look there when the script completes")
historical_last_updated_logfile = "historical_last_updated.txt"
earnings_last_reported_logfile = "earnings_last_reported.txt"
eps_projections_last_updated_logfile = "eps_projections_last_updated.txt"
charts_last_updated_logfile = "charts_last_updated.txt"
eps_report_newer_than_eps_projection_logfile = "eps_report_newer_than_eps_projection.txt"
skipped_tickers_logfile="skipped_tickers_Sort_misc.txt"

historical_last_updated_df.sort_values(by=['Date','Ticker'], ascending=[True,True]).to_csv(dir_path + log_dir + "\\" + historical_last_updated_logfile,sep=' ', index=True, header=False)
earnings_last_reported_df.sort_values(by=['Where_found','Reason','Date','Ticker'], ascending=[True,True,True,True]).to_csv(dir_path + log_dir + "\\" + earnings_last_reported_logfile,sep=' ', index=True, header=False)
eps_projections_last_updated_df.sort_values(by=['Date','Ticker','Reason'], ascending=[True,True,True]).to_csv(dir_path + log_dir + "\\" + eps_projections_last_updated_logfile,sep=' ', index=True, header=False)
charts_last_updated_df.sort_values(by=['Date','Ticker'], ascending=[True,True]).to_csv(dir_path + log_dir + "\\" + charts_last_updated_logfile,sep=' ', index=True, header=False)
eps_report_newer_than_eps_projection_df.sort_values(by='Actual_EPS_Report').to_csv(dir_path + log_dir + "\\" + eps_report_newer_than_eps_projection_logfile,sep=' ', index=True, header=True)
skipped_tickers_df.sort_values(by=['Ticker'], ascending=[True]).to_csv(dir_path + log_dir + "\\" + skipped_tickers_logfile,sep=' ', index=True, header=True)
logging.info("Created : " + str(historical_last_updated_logfile) + " <-- Sorted by date - based on the last Price date in their respective historical file")
logging.info("Created : " + str(earnings_last_reported_logfile) + " <-- Sorted by date - based on when their Last Earnings Date in their respective Earnings file")
logging.info("Created : " + str(eps_projections_last_updated_logfile) + " <-- Sorted by date - based on when the Earnings Projections were updated in their respective Earnings file")
logging.info("Created : " + str(charts_last_updated_logfile) + " <-- Sorted by date - based on when the Chart was creates in the Charts directory")
logging.info("Created : " + str(skipped_tickers_logfile) + " <-- Sorted by Ticker - Lists all the tickers that were skipped along with a reason")
logging.info("Created : " + str(eps_report_newer_than_eps_projection_logfile) + " <-- THIS FILE SHOULD BE EMPTY. It is a BAD thing if this file is not emptly. The file has the tickers for which the earnings projections are newer than the reported earnings date")
if (len(eps_report_newer_than_eps_projection_df.index) > 0):
  logging.error("")
  logging.error("*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+")
  logging.error("               " + str(eps_report_newer_than_eps_projection_logfile) + " IS NOT EMPTY...YOU GOTTA INVESTIGATE IT")
  logging.error("*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+*+")

# This is not needed as we get the data from the above files anyway...
# However this works and if needed can be resurrected.
# gt_1_month_old_historical_last_updated_df.sort_values(by='Date').to_csv(dir_path + log_dir + "\\" + 'gt_1_month_historical_last_updated.txt',sep=' ', index=True, header=False)
# gt_1_month_old_eps_projections_last_updated_df.sort_values(by='Date').to_csv(dir_path + log_dir + "\\" + 'gt_1_month_old_eps_projections_last_updated.txt',sep=' ', index=True, header=False)
# gt_1_qtr_old_eps_projections_last_updated_df.sort_values(by='Date').to_csv(dir_path + log_dir + "\\" + 'gt_1_qtr_old_eps_projections_last_updated.txt',sep=' ', index=True, header=False)
# gt_1_month_charts_last_updated_df.sort_values(by='Date').to_csv(dir_path + log_dir + "\\" + 'gt_1_month_charts_last_updated.txt',sep=' ', index=True, header=False)

logging.info("")
logging.info("********************")
logging.info("***** All Done *****")
logging.info("********************")
# -----------------------------------------------------------------------------




# Will need this eventually when we have financials up and running 
# gt_1_qtr_old_financials_df = pd.DataFrame(columns=['Ticker','Date'])
# gt_1_qtr_old_financials_df.set_index('Ticker', inplace=True)
# date_updated_financials = master_tracklist_df.loc[ticker, 'Last_Updated_Financials']
#   # ---------------------------------------------------------------------------
#   # Check for the last updated Financials
#   # ---------------------------------------------------------------------------
#   if (not pd.isnull(date_updated_financials)):
#     date_updated_financials_dt = dt.datetime.strptime(str(date_updated_financials), '%Y-%m-%d %H:%M:%S').date()
#     date_year = date_updated_financials_dt.year
#     # print ("The Year when Financials were updated is", date_year)
#     if (date_year < 2019):
#       print ("==========     Error : The date for ", ticker, " Financials is older than 2019     ==========")
#       sys.exit()
#     if (date_updated_financials_dt < one_month_ago_date):
#       print("Financials were updated on : ", date_updated_financials_dt, " more than a month ago")
#       gt_1_qtr_old_financials_df.loc[ticker] = [date_updated_financials_dt]
#   # ---------------------------------------------------------------------------
#
# gt_1_qtr_old_financials_df.sort_values(by='Date').to_csv('gt_1_qtr_old_financials.txt',sep=' ', index=True, header=False)


''' It seems that this code is not needed in this script
if 'Q_EPS_Projections_Date_1' in qtr_eps_df.columns:
  eps_projection_date_1 = qtr_eps_df['Q_EPS_Projections_Date_1'].tolist()[0]
  print("Second to Last Q EPS was updated in", earnings_file, " on ", eps_projection_date_1)
  if (not pd.isnull(eps_projection_date_1)):
    eps_projection_date_1_dt = dt.datetime.strptime(str(eps_projection_date_1), '%m/%d/%Y').date()
else:
  print("Column Q_EPS_Projections_Date_1 DOES NOT exist in ", earnings_file)
  sys.exit(1)
'''

''' This code can be useful to use - as an education in some other script
# -----------------------------------------------------------------------------
# Get all the files in the Earnings directory that end with _earnings.csv
# -----------------------------------------------------------------------------
for file in os.listdir("C:\Sundeep\Stocks_Automation\Earnings"):
  if file.endswith("_earnings.csv"):
    file_fullpath = os.path.join("C:\Sundeep\Stocks_Automation\Earnings", file)
    # print(file_fullpath)
    # -------------------------------------------------------------------------
    # Open the file and see if it has a column by the name of <XYN>
    # -------------------------------------------------------------------------
    file_df = pd.read_csv(file_fullpath)
    if 'Q_EPS_Projections_Date_0' in file_df.columns:
      # print ("Column exists in ", file_fullpath)
      a_var = 1
    else:
      print ("Column DOES NOT exist in ", file)

# -----------------------------------------------------------------------------
'''

