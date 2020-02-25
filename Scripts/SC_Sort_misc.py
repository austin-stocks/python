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
charts_dir = "\\..\\" + "Charts"
earnings_dir = "\\..\\" + "Earnings"
historical_dir = "\\..\\" + "Historical"
master_tracklist_file = "Master_Tracklist.xlsx"
master_tracklist_df = pd.read_excel(dir_path + user_dir + "\\" + master_tracklist_file, sheet_name="Main")
master_tracklist_df.sort_values('Ticker', inplace=True)
ticker_list_unclean = master_tracklist_df['Ticker'].tolist()
ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']
# The index can only be changed after the Ticker has been put to list
# In other words index cannot be read as a list
master_tracklist_df.set_index('Ticker', inplace=True)
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

# Disnable and enable global level logging
logging.disable(sys.maxsize)
logging.disable(logging.NOTSET)
# -----------------------------------------------------------------------------

all_chart_files_list=os.listdir(dir_path + charts_dir + "\\")
logging.debug("The files in the chart direcotry are" + str(all_chart_files_list))

# -----------------------------------------------------------------------------
# Declare all the dataframes that we are going to need to write into txt file
# and set their columns
# -----------------------------------------------------------------------------
today = dt.date.today()
one_qtr_ago_date = today - dt.timedelta(days=80)
one_month_ago_date = today - dt.timedelta(days=15)
logging.info("Today : " + str(today) +  " One month ago : " +str(one_month_ago_date) + " One qtr ago : " +str(one_qtr_ago_date))

historical_last_updated_df = pd.DataFrame(columns=['Ticker','Date'])
earnings_last_reporeted_df = pd.DataFrame(columns=['Ticker','Date'])
eps_projections_last_updated_df = pd.DataFrame(columns=['Ticker','Date'])
charts_last_updated_df  = pd.DataFrame(columns=['Ticker','Date'])
eps_report_newer_than_eps_projection_df = pd.DataFrame(columns=['Ticker','Actual_EPS_Report','EPS_Projections_Last_Updated'])

gt_1_month_old_historical_last_updated_df = pd.DataFrame(columns=['Ticker','Date'])
gt_1_month_old_eps_projections_last_updated_df = pd.DataFrame(columns=['Ticker','Date'])
gt_1_qtr_old_eps_projections_last_updated_df = pd.DataFrame(columns=['Ticker','Date'])
gt_1_month_charts_last_updated_df = pd.DataFrame(columns=['Ticker','Date'])

historical_last_updated_df.set_index('Ticker', inplace=True)
earnings_last_reporeted_df.set_index('Ticker', inplace=True)
eps_projections_last_updated_df.set_index('Ticker', inplace=True)
charts_last_updated_df.set_index('Ticker', inplace=True)
eps_report_newer_than_eps_projection_df.set_index('Ticker', inplace=True)

gt_1_month_old_historical_last_updated_df.set_index('Ticker', inplace=True)
gt_1_month_old_eps_projections_last_updated_df.set_index('Ticker', inplace=True)
gt_1_qtr_old_eps_projections_last_updated_df.set_index('Ticker', inplace=True)
gt_1_month_charts_last_updated_df.set_index('Ticker', inplace=True)
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Loop through all the tickers
# -----------------------------------------------------------------------------
# ticker_list = ['AUDC', 'MED']
for ticker_raw in ticker_list:
  ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase
  logging.debug("================================")
  logging.info("Processing : " + str(ticker))
  # if ticker in ["CCI", , "CY", "EXPE", "FLS", "GCBC","GOOG","HURC","KMI","KMX","PNFP","QQQ","RCMT","TMO","TMUS","TTWO",,"WLTW"]:
  if ticker in ["QQQ"]:
    logging.info("File for " + str(ticker) + "does not exist in earnings directory. Skipping...")
    continue
  quality_of_stock = master_tracklist_df.loc[ticker, 'Quality_of_Stock']
  if ((quality_of_stock != 'Wheat') and (quality_of_stock != 'Wheat_Chaff') and (quality_of_stock != 'Essential')):
    logging.info(str(ticker) + " is not Wheat...skipping")
    continue

  # ---------------------------------------------------------------------------
  # Read the Historical data file and get the last date for which prices are available
  # If it is more than a month then put it in gt_1_month old
  # ---------------------------------------------------------------------------
  historical_df = pd.read_csv(dir_path + historical_dir + "\\" + ticker + "_historical.csv")
  date_str_list = historical_df.Date.tolist()
  date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in date_str_list]
  ticker_adj_close_list = historical_df.Adj_Close.tolist()
  ticker_curr_price = next(x for x in ticker_adj_close_list if not math.isnan(x))
  ticker_curr_date = date_list[ticker_adj_close_list.index(ticker_curr_price)]
  historical_last_updated_df.loc[ticker]= [ticker_curr_date]
  if (ticker_curr_date < one_month_ago_date):
    logging.debug("Historical Data was last updated on : " + str(ticker_curr_date) + ", more than a month ago")
    gt_1_month_old_historical_last_updated_df.loc[ticker]= [ticker_curr_date]
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Get the last earnings report date from Master Tracklist
  # ---------------------------------------------------------------------------
  eps_actual_report_date = ""
  try:
    eps_actual_report_date = dt.datetime.strptime(str(master_tracklist_df.loc[ticker, 'Last_Earnings_Date']),'%Y-%m-%d %H:%M:%S').date()
  except:
    logging.error("**********************  ERROR ERROR ERROR ERROR ****************************")
    logging.error(str(ticker) + " is wheat and does not have a earnings date in the Master Tracklist file. Exiting....")
    logging.error("**********************  ERROR ERROR ERROR ERROR ****************************")
    sys.exit(1)
  eps_actual_report_date_dt = dt.datetime.strptime(str(eps_actual_report_date), '%Y-%m-%d').date()
  if (eps_actual_report_date_dt > dt.date.today()):
    logging.error("  The Last quarterly earnings date for " + str(ticker) + " is " + str(eps_actual_report_date_dt) + " which is in future... :-(")
    logging.error("  This seems like a typo :-)...Please correct it in Master Tracklist file and rerun")
    sys.exit(1)

  date_year = eps_actual_report_date_dt.year
  if (date_year < 2019):
    logging.error("==========     Error : The date for " + str(ticker) + " last earnings is older than 2019     ==========")
    sys.exit()
  earnings_last_reporeted_df.loc[ticker]= [eps_actual_report_date_dt]
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
  date_year = eps_projection_date_0_dt.year

  if (date_year < 2019):
    logging.error("==========     Error : Seems like the projected EPS date is older than 2019. Please correct and rerun the script")
    sys.exit(1)
  if (eps_projection_date_0_dt > dt.date.today()):
    logging.error("  The  Q_EPS_Projections_Date_0 date for " + str(ticker) + " is " + str(eps_projection_date_0_dt) + " which is in future... :-(")
    logging.error("  This seems like a typo :-)...Please correct it in Earnings csv file and rerun")
    sys.exit(1)

  eps_projections_last_updated_df.loc[ticker]= [eps_projection_date_0_dt]

  if (eps_projection_date_0_dt < one_month_ago_date):
    logging.debug("Projected EPS were last updated on : " + str(eps_projection_date_0_dt) + ", more than a month ago")
    gt_1_month_old_eps_projections_last_updated_df.loc[ticker]= [eps_projection_date_0_dt]

  if (eps_projection_date_0_dt < one_qtr_ago_date):
    logging.debug("Projected EPS were last updated on : " + str(eps_projection_date_0_dt) + ", more than a quarter ago")
    gt_1_qtr_old_eps_projections_last_updated_df.loc[ticker]= [eps_projection_date_0_dt]

  if (eps_actual_report_date_dt > eps_projection_date_0_dt):
    logging.error("The Earnings report date : " + str(eps_actual_report_date_dt) + " is newer than the earnings projection date : " + str(eps_projection_date_0_dt))
    logging.error("I don't understand how you let it happen - The possible reasons could be ")
    logging.error("1. You forgot to update the Earnings projection on the Earnings report date....Ok. I understand. Plese update the eranings projections now and rerun ")
    logging.error("2. You mistyped the date (either the earnings report date in master tracklist or more likely in for earnings projections in earning file...I understand. It happens sometimes. Please fix and rerun")
    logging.error("3. You did not update the Earnings projection on the Earnings report date intentionally....BAD BAD....How can you do that???? ")
    eps_report_newer_than_eps_projection_df.loc[ticker, 'Actual_EPS_Report'] = eps_actual_report_date_dt
    eps_report_newer_than_eps_projection_df.loc[ticker, 'EPS_Projections_Last_Updated'] = eps_projection_date_0_dt
    # sys.exit(1)

  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Get all the charts in the charts directory for the ticker and find out the
  # chart file with the latest appended date
  # ---------------------------------------------------------------------------
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



historical_last_updated_df.sort_values(by=['Date','Ticker'], ascending=[True,True]).to_csv(dir_path + log_dir + "\\" + historical_last_updated_logfile,sep=' ', index=True, header=False)
earnings_last_reporeted_df.sort_values(by=['Date','Ticker'], ascending=[True,True]).to_csv(dir_path + log_dir + "\\" + earnings_last_reported_logfile,sep=' ', index=True, header=False)
eps_projections_last_updated_df.sort_values(by=['Date','Ticker'], ascending=[True,True]).to_csv(dir_path + log_dir + "\\" + eps_projections_last_updated_logfile,sep=' ', index=True, header=False)
charts_last_updated_df.sort_values(by=['Date','Ticker'], ascending=[True,True]).to_csv(dir_path + log_dir + "\\" + charts_last_updated_logfile,sep=' ', index=True, header=False)
eps_report_newer_than_eps_projection_df.sort_values(by='Actual_EPS_Report').to_csv(dir_path + log_dir + "\\" + eps_report_newer_than_eps_projection_logfile,sep=' ', index=True, header=False)
logging.info("Created : " + str(historical_last_updated_logfile) + " <-- Tickers sorted by date - old to new - as to when their historical Prices were updated in their respective historical file")
logging.info("Created : " + str(earnings_last_reported_logfile) + " <-- Tickers sorted by date - old to new - as to when their Last Earnings were updated in Master_Tracklist file")
logging.info("Created : " + str(eps_projections_last_updated_logfile) + " <-- Tickers sorted by date - old to new - as to when their Earnings Projections were updated in their respective Earnings file")
logging.info("Created : " + str(charts_last_updated_logfile) + " <-- Tickers sorted by date - old to new - as to when their Charts were creates in the Charts directory")
logging.info("Created : " + str(eps_report_newer_than_eps_projection_logfile) + " <-- THIS FILE SHOULD BE EMPTY. It is a BAD thing if this file is not emptly. The file has the tickers for which the earnings projections are newer than the reported earnings date")
if (len(eps_report_newer_than_eps_projection_df.index) > 0):
  logging.error(eps_report_newer_than_eps_projection_logfile + " is not empty...You gotta investigate it")

# This is not needed as we get the data from the above files anyway .... However this works and if needed can be
# resurrected.
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

