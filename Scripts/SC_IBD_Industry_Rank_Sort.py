import pandas as pd
import os
import sys
import time
import datetime as dt
import numpy as np
import logging
import math
import re
import json
from dateutil.relativedelta import relativedelta

# -----------------------------------------------------------------------------
# Read the master tracklist file into a dataframe
# -----------------------------------------------------------------------------
dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
log_dir = "\\..\\" + "Logs"
ibd_inds_gp_dir = "\\..\\" + "IBD" + "\\" + "IBD-Industry-Groups"
ibd_data_tables_dir = "\\..\\" + "IBD" + "\\" + "Data_Tables"
ibd_inds_gp_file = "Industry-Groups-Running-Rank.xlsx"

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
                    filename=dir_path + log_dir + "\\" + 'SC_IDB_Industry_Rank_Sort_debug.txt',
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

# Read the IBD Industry Group Running file
ibd_inds_gp_rank_df = pd.read_excel(dir_path + ibd_inds_gp_dir + "\\" + ibd_inds_gp_file, sheet_name="Rank")
# Sundeep : 06/25/2023 : TODO : Not sure what to do with Composite right now
ibd_inds_gp_composite_df = pd.read_excel(dir_path + ibd_inds_gp_dir + "\\" + ibd_inds_gp_file, sheet_name="Composite")
logging.debug("The Industry Rank DF " + ibd_inds_gp_rank_df.to_string())
ibd_inds_gp_rank_df.sort_values('Industry Group Name', inplace=True)
inds_gp_list = ibd_inds_gp_rank_df['Industry Group Name'].tolist()
ibd_inds_gp_rank_df.set_index('Industry Group Name', inplace=True)
weekly_dates_list = ibd_inds_gp_rank_df.columns.tolist()
# Sort the date list : It should be sorted already as it is read from
# the file, but still sort it before proceeding
weekly_dates_list.sort(reverse=True)
# TODO : Sanity check that all the dates are no more than 9 days
# apart, otherwise it suggest a skipped week

# Truncate the list to 10 elements - as we only want to look at 10 weeks -
# This can be easily changed to whatever weeks we need
no_of_weeks_to_lookback = 10
del weekly_dates_list[no_of_weeks_to_lookback:]
weekly_dates_str_list = [dt.datetime.strftime(date, '%m/%d/%Y') for date in weekly_dates_list]
latest_weekly_date_str = dt.datetime.strptime(weekly_dates_str_list[0], '%m/%d/%Y').strftime("%Y-%m-%d")
logging.debug("The dates for which the Ranking will be applied : " + str(weekly_dates_list))

inds_best_rank_8wks_df = pd.DataFrame(columns=['Industry_Group','Rank'])
inds_best_rank_8wks_df.set_index('Industry_Group', inplace=True)

num_inds_best_rank_sometime_in3wks_out_of_8wks = 0
num_inds_best_rank_8wks = 0
for inds_name in inds_gp_list:
  logging.debug("\n")
  logging.debug("Industry Name : " + str(inds_name))
  inds_gp_series = ibd_inds_gp_rank_df.loc[inds_name]
  logging.debug("The Industry Series is : \n" + str(inds_gp_series))
  inds_rank_list = []
  for date_dt in weekly_dates_list:
    inds_rank = inds_gp_series[date_dt]
    logging.debug("Date : " + str(date_dt) + ", Rank : " + str(inds_rank))
    inds_rank_list.append(inds_rank)

  logging.debug("The Rank list for : " + str(inds_name) + ", is : " + str(inds_rank_list))
  # Now check if the last 3 weeks are the lowest in the last 10 weeks
  rank_week_m0 = inds_rank_list[0]
  rank_week_m1 = inds_rank_list[1]
  rank_week_m2 = inds_rank_list[2]
  rank_week_m0_lowest = 1
  rank_week_m1_lowest = 1
  rank_week_m2_lowest = 1
  for tmp_rank in inds_rank_list[1:8]:
    if (tmp_rank < rank_week_m0):
      rank_week_m0_lowest = 0
  for tmp_rank in inds_rank_list[2:8]:
    if (tmp_rank < rank_week_m1):
      rank_week_m1_lowest = 0
  for tmp_rank in inds_rank_list[3:8]:
    if (tmp_rank < rank_week_m2):
      rank_week_m2_lowest = 0
  if ((rank_week_m0_lowest == 1) or (rank_week_m1_lowest == 1) or (rank_week_m2_lowest == 1)):
    num_inds_best_rank_sometime_in3wks_out_of_8wks += 1
    logging.debug(str(inds_name) + " has lowest Rank (good) in the last 3 weeks")
    # If they are and the ranking has been improving in the last 3 weeks too, then
    # all the better. These are the inds groups for which we should get the high
    # ranking stocks to look at every week
    if ((rank_week_m0 <= rank_week_m1) and (rank_week_m1 <= rank_week_m2)):
      num_inds_best_rank_8wks += 1
      # TODO : Put this industry in a df / list so that it can be then used
      # later to pull out all the tickers (or the best 10% rated tickers
      # from the data tables xlsx
      logging.info(str(inds_name).ljust(30) + ", Current Rank : " + str(rank_week_m0).ljust(5) + str(inds_rank_list[1:8]).ljust(40) + " has the lowest rank in the last 8 weeks")
      inds_best_rank_8wks_df.loc[inds_name.strip()] = rank_week_m0

logging.info("")
logging.info("Found " + str(num_inds_best_rank_sometime_in3wks_out_of_8wks).ljust(5) + " industries that had best rank sometime in the last 3 weeks out of last 8 weeks")
logging.info("Found " + str(num_inds_best_rank_8wks).ljust(5) + " industries that had best rank this week out of last 8 weeks")

inds_best_rank_8wks_logfile="Industries_with_best_ranks_8wks.csv"
# inds_best_rank_8wks_df.sort_values(by=['Rank'], ascending=[True]).to_csv(dir_path + log_dir + "\\" + inds_best_rank_8wks_logfile,sep=',', index=True, header=True,encoding = "ISO-8859-1")
inds_best_rank_8wks_df.sort_values(by=['Rank'], ascending=[True]).to_csv(dir_path + log_dir + "\\" + inds_best_rank_8wks_logfile,sep=',', index=True, header=True)
logging.info("Created : " + str(inds_best_rank_8wks_logfile) + " <-- Sorted by IBD Industry Rank")


# TODO : Next step is to read the data tables and find out all the tickers that
# are in those industry groups and put them in a csv/xlsx and they become
# the watchlist
ibd_data_tables_file = latest_weekly_date_str + "-Data_Tables.csv"
ibd_data_tables_file = "2023-06-23" + "-Data_Tables.csv"
logging.debug("Opening file " + str(dir_path + ibd_data_tables_dir + "\\" + ibd_data_tables_file))
# ibd_data_tables_df = pd.read_excel(dir_path + ibd_data_tables_dir + "\\" + ibd_data_tables_file, sheet_name="Stock_list",engine='xlrd')
ibd_data_tables_df = pd.read_csv(dir_path + ibd_data_tables_dir + "\\" + ibd_data_tables_file,encoding = "ISO-8859-1")
logging.debug("The Data tables file is : \n" + ibd_data_tables_df.to_string())
ranks_to_filter_list = inds_best_rank_8wks_df['Rank'].tolist()
ranks_to_filter_list.sort(reverse=False)
logging.debug("The ranks to filter out are : " + str(ranks_to_filter_list))

ibd_data_table_extraced_with_8wks_ranks_df = ibd_data_tables_df.loc[ibd_data_tables_df['Industry Group Rank'].isin(ranks_to_filter_list)]
logging.debug("There are the tickers that are of interest now \n" + ibd_data_table_extraced_with_8wks_ranks_df.to_string())

tickers_in_inds_best_rank_8wks_logfile="Tickers_in_Industries_with_best_ranks_8wks.csv"
ibd_data_table_extraced_with_8wks_ranks_df.sort_values(by=['Industry Group Rank','Comp. Rating','Symbol'], ascending=[True,False,True]).to_csv(dir_path + log_dir + "\\" + tickers_in_inds_best_rank_8wks_logfile,sep=',', index=True, header=True)
logging.info("Created : " + str(tickers_in_inds_best_rank_8wks_logfile) + " <-- Sorted by IBD Industry Rank")


# Till now we have all the inds gp names in a list and all the dates in a list (as datetime)
# 1. Alert Sundeep if any of the date are more than 9 dates apart (as that would indicate a
#    weekly miss
# 2. Make a few df
#    2a. One that shows the current week or week before that or the week before that
#        has the lowest number in the last 12 weeks (or 8 weeks)
#    2b. One that shows consistent successive decline in 3 weeks (or 4 weeks)
#    2c. One that shows the most improvement in the last 3 weeks (or 4 weeks - How to find that out?
#        as an improvement from 30 -> 15 is just a 15 rank improvment, but a improvement from
#        100 -> 85 is also an 15 rank improvement but maybe not as much as improvment from 30 -> 15)
#        This needs more thought...

sys.exit(1)


master_tracklist_df.sort_values('Tickers', inplace=True)
ticker_list_unclean = master_tracklist_df['Tickers'].tolist()
ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']
# The index can only be changed after the Ticker has been put to list
# In other words index cannot be read as a list
master_tracklist_df.set_index('Tickers', inplace=True)


# Read the dated IBD Industry Groups Ranking file
# The name of the file is in the format YYYY-MM-DD-Industry-Groups.csv
latest_date = "2023-05-12"
lastest_ibd_industry_file = latest_date + "-Industry-Groups.csv"

latest_ibd_gp_rank_df = pd.read_csv(dir_path + ibd_industry_group_dir + "\\" + lastest_ibd_industry_file)
logging.debug("The Latest Industry Rank df " + latest_ibd_gp_rank_df.to_string())

# Read the Running Industry Ranking file

# Make sure that the industry groups are the same in each file.
# Flag an error if different - as that would indicate that IBD
# changed (added/Deleted) one or more Industry Groups


# While updating the running file, ensure that the date column that you are
# updating does not already exist. If it does, then error out and let
# Sundeep figure out what to do

# Add a column to the running df corresponding to that date

# Figure out how to add the current (latest rank) pythonically
# to the industry group in the column added for the latest date

# Print out the df in the appropriate sheet of the running file

sys.exit(1)





# -----------------------------------------------------------------------------
# Declare all the dataframes that we are going to need to write into and set their columns
# -----------------------------------------------------------------------------
today = dt.date.today()
one_qtr_ago_date = today - dt.timedelta(days=80)
one_month_ago_date = today - dt.timedelta(days=15)
logging.info("Today : " + str(today) +  " One month ago : " +str(one_month_ago_date) + " One qtr ago : " +str(one_qtr_ago_date))

historical_last_updated_df = pd.DataFrame(columns=['Ticker','Date'])
earnings_report_date_1qtr_ago_df = pd.DataFrame(columns=['Ticker','Date','Where_found','Reason'])
earnings_report_date_4qtr_ago_df = pd.DataFrame(columns=['Ticker','Date','Where_found','Reason'])
eps_projections_last_updated_df = pd.DataFrame(columns=['Ticker','Date','Reason'])
charts_last_updated_df  = pd.DataFrame(columns=['Ticker','Date'])
eps_report_newer_than_eps_projection_df = pd.DataFrame(columns=['Ticker','Actual_EPS_Report','EPS_Projections_Last_Updated'])
price_target_df = pd.DataFrame(columns=['Ticker','PT_Change','Latest_PT','Previous_PT', 'Latest_Date', 'One_Month_Old_Date'])
skipped_tickers_df = pd.DataFrame(columns=['Ticker','Quality_of_Stock','Reason'])
eps_report_by_month_df = pd.DataFrame(columns=['Month', 'Count'])
month_sort_order_list = []

historical_last_updated_df.set_index('Ticker', inplace=True)
earnings_report_date_1qtr_ago_df.set_index('Ticker', inplace=True)
earnings_report_date_4qtr_ago_df.set_index('Ticker', inplace=True)
eps_projections_last_updated_df.set_index('Ticker', inplace=True)
charts_last_updated_df.set_index('Ticker', inplace=True)
eps_report_newer_than_eps_projection_df.set_index('Ticker', inplace=True)
price_target_df.set_index('Ticker', inplace=True)
skipped_tickers_df.set_index('Ticker', inplace=True)
eps_report_by_month_df.set_index('Month',inplace=True)

# ---------------------------------------------------------
# Generate and put the name of the months in a list
# ---------------------------------------------------------
for i_idx in range(12):
  month_name = dt.datetime.strptime(str(i_idx+1), "%m").strftime("%b")
  eps_report_by_month_df.loc[month_name,'Count'] = 0
  month_sort_order_list.append(month_name)
logging.debug("Month sort order list " + str(month_sort_order_list))
# ---------------------------------------------------------

# gt_1_month_old_historical_last_updated_df = pd.DataFrame(columns=['Ticker','Date'])
# gt_1_month_old_eps_projections_last_updated_df = pd.DataFrame(columns=['Ticker','Date'])
# gt_1_qtr_old_eps_projections_last_updated_df = pd.DataFrame(columns=['Ticker','Date'])
# gt_1_month_charts_last_updated_df = pd.DataFrame(columns=['Ticker','Date'])
# gt_1_month_old_historical_last_updated_df.set_index('Ticker', inplace=True)
# gt_1_month_old_eps_projections_last_updated_df.set_index('Ticker', inplace=True)
# gt_1_qtr_old_eps_projections_last_updated_df.set_index('Ticker', inplace=True)
# gt_1_month_charts_last_updated_df.set_index('Ticker', inplace=True)
# -----------------------------------------------------------------------------

# Read the PT json and the charts directory.
# No specific reason to read it here...it could have been read before too
with open(dir_path + user_dir + "\\" + price_target_json_file) as json_file:
  price_target_json = json.load(json_file)
all_chart_files_list = os.listdir(dir_path + my_linear_chart_dir + "\\")
logging.debug("The files in the chart directory are" + str(all_chart_files_list))

# -----------------------------------------------------------------------------
# Loop through all the tickers
# -----------------------------------------------------------------------------
# ticker_list = ['PLUS','AUDC', 'MED', 'IBM']
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
  # if (ticker in ['FOX','TAYD', 'CRVL', 'WILC', 'WINA', 'GCBC']):
  #   skipped_tickers_df.loc[ticker,'Quality_of_Stock'] = quality_of_stock
  #   skipped_tickers_df.loc[ticker,'Reason'] = '     =====> No_CNBC_Projections_available._You_should_periodically_check_CNBC'
  #   continue


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

  if (eps_projection_date_0_dt > dt.date.today()):
    logging.error("  The  Q_EPS_Projections_Date_0 date for " + str(ticker) + " is " + str(eps_projection_date_0_dt) + " which is in future... :-(")
    logging.error("  This seems like a typo :-)...Please correct it in Earnings csv file and rerun")
    sys.exit(1)
  eps_projections_last_updated_df.loc[ticker,'Date']= eps_projection_date_0_dt
  eps_projections_last_updated_df.loc[ticker,'Reason']= master_tracklist_df.loc[ticker, 'Reason_Earnings_Projections_NOT_updated']

  # date_year = eps_projection_date_0_dt.year
  # if (date_year < 2019):
  #   logging.error("==========     Error : Seems like the projected EPS date is older than 2019. Please correct and rerun the script")
  #   sys.exit(1)
  # if (eps_projection_date_0_dt < one_month_ago_date):
  #   logging.debug("Projected EPS were last updated on : " + str(eps_projection_date_0_dt) + ", more than a month ago")
  #   gt_1_month_old_eps_projections_last_updated_df.loc[ticker]= eps_projection_date_0_dt
  #
  # if (eps_projection_date_0_dt < one_qtr_ago_date):
  #   logging.debug("Projected EPS were last updated on : " + str(eps_projection_date_0_dt) + ", more than a quarter ago")
  #   gt_1_qtr_old_eps_projections_last_updated_df.loc[ticker]= eps_projection_date_0_dt
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Get the last earnings report date from earnings df
  # ---------------------------------------------------------------------------
  eps_report_date_1qtr_ago = ""
  eps_report_date_4qtr_ago = ""
  if ('Q_Report_Date' in qtr_eps_df.columns):
    qtr_eps_report_date_list = qtr_eps_df.Q_Report_Date.dropna().tolist()
    logging.debug("The Quarterly Report Date List from the earnings file after dropna is " + str(qtr_eps_report_date_list))
  if (len(qtr_eps_report_date_list) > 0):
    qtr_eps_report_date_list_dt = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in qtr_eps_report_date_list]
    eps_report_date_1qtr_ago = qtr_eps_report_date_list_dt[0]
    eps_report_date_4qtr_ago = qtr_eps_report_date_list_dt[3]
  else:
    earnings_report_date_1qtr_ago_df.loc[ticker, 'Where_found'] = 'Master_Tracklist'
    earnings_report_date_4qtr_ago_df.loc[ticker, 'Where_found'] = 'Master_Tracklist'
    eps_report_date_1qtr_ago = dt.datetime.strptime(str(master_tracklist_df.loc[ticker, 'Last_Earnings_Date']),'%Y-%m-%d %H:%M:%S').date()
    eps_report_date_4qtr_ago = dt.datetime.strptime(str(master_tracklist_df.loc[ticker, 'Last_Earnings_Date']),'%Y-%m-%d %H:%M:%S').date()

  eps_report_date_1qtr_ago_dt = dt.datetime.strptime(str(eps_report_date_1qtr_ago), '%Y-%m-%d').date()
  eps_report_date_4qtr_ago_dt = dt.datetime.strptime(str(eps_report_date_4qtr_ago), '%Y-%m-%d').date()
  if (eps_report_date_1qtr_ago_dt > dt.date.today()):
    logging.error("  The Last quarterly earnings date for " + str(ticker) + " is " + str(eps_report_date_1qtr_ago_dt) + " which is in future... :-(")
    logging.error("  This seems like a typo :-)...Please correct it in Master Tracklist file and rerun")
    sys.exit(1)
  if (eps_report_date_4qtr_ago_dt > dt.date.today()):
    logging.error("  The Last Year earnings date for " + str(ticker) + " is " + str(eps_report_date_4qtr_ago_dt) + " which is in future... :-(")
    logging.error("  This seems like a typo :-)...Please correct it in Master Tracklist file and rerun")
    sys.exit(1)
  earnings_report_date_1qtr_ago_df.loc[ticker,'Date']= eps_report_date_1qtr_ago_dt
  earnings_report_date_4qtr_ago_df.loc[ticker,'Date']= eps_report_date_4qtr_ago_dt

  if (eps_report_date_1qtr_ago_dt > eps_projection_date_0_dt):
    logging.error("The Earnings report date : " + str(eps_report_date_1qtr_ago_dt) + " is newer than the earnings projection date : " + str(eps_projection_date_0_dt))
    logging.error("I don't understand how you let it happen - The possible reasons could be ")
    logging.error("1. You forgot to update the Earnings projection on the Earnings report date....Ok. I understand. Plese update the eranings projections now and rerun ")
    logging.error("2. You mistyped the date (either the earnings report date in master tracklist or more likely in for earnings projections in earning file...I understand. It happens sometimes. Please fix and rerun")
    logging.error("3. You did not update the Earnings projection on the Earnings report date intentionally....BAD BAD....How can you do that???? ")
    eps_report_newer_than_eps_projection_df.loc[ticker, 'Actual_EPS_Report'] = eps_report_date_1qtr_ago_dt
    eps_report_newer_than_eps_projection_df.loc[ticker, 'EPS_Projections_Last_Updated'] = eps_projection_date_0_dt

  # Get the last 4 dates when the company reported earnings
  # Used to accumulate the last 4 quarter report dates across all tickers
  # to find out which are the months that most quarterly earnings are
  # reported and which months are least busy
  if (len(qtr_eps_report_date_list_dt) > 3):
    # Get the last 4 qtr earnings date and convert the month
    for i_idx in range(4):
      month = qtr_eps_report_date_list_dt[i_idx].strftime('%b')
      logging.debug("Earnings date " + str(qtr_eps_report_date_list_dt[i_idx]) + ", Earnings Month " + str(month))
      tmp_count = eps_report_by_month_df['Count'].loc[month]
      eps_report_by_month_df.loc[month,'Count'] = tmp_count + 1
      logging.debug("Previous earnings Count for " + str(month) + " : " + str(tmp_count) + ", Updated to : " + str(eps_report_by_month_df['Count'].loc[month]))

  # date_year = eps_report_date_1qtr_ago_dt.year
  # if (date_year < 2019):
  #   logging.error("==========     Error : The date for " + str(ticker) + " last earnings is older than 2019     ==========")
  #   sys.exit()
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Get all the charts in the charts directory for the ticker and find out the
  # chart file with the latest appended date
  # ---------------------------------------------------------------------------
  my_regex = re.compile(re.escape(ticker) + re.escape("_")  + ".*jpg")
  ticker_chart_files_list = list(filter(my_regex.match, all_chart_files_list)) # Read Note
  logging.debug("The chart file list for this ticker is : " + str(ticker_chart_files_list))

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

  # ---------------------------------------------------------------------------
  # Get the price target dict for the ticker
  # ---------------------------------------------------------------------------
  price_target_dict_needs_rename = {}
  price_target_date_list_dt = []
  price_target_amount_list = []
  pt_print_str = ""
  if ticker in price_target_json.keys():
    price_target_dict_needs_rename = price_target_json[ticker]
    logging.debug("Price target data for " + str(ticker) + " in Price Target Json : \n" + str(price_target_json[ticker]['Price_Target']))
    len_price_target = len(price_target_json[ticker]["Price_Target"])
    for i in range(len_price_target):
      i_price_target_date = price_target_json[ticker]["Price_Target"][i]["Date"]
      i_price_target_amount = price_target_json[ticker]["Price_Target"][i]["Target"].replace(',','')
      try:
        price_target_date_list_dt.append(dt.datetime.strptime(i_price_target_date, "%m/%d/%Y").date())
        price_target_amount_list.append(float(i_price_target_amount))
      except (ValueError):
        logging.error(
          "\n***** Error : Either the Dates or the Price Target Amount are not in proper format for Price_Target in Price Target json file.\n"
          "***** Error : The Dates should be in the format %m/%d/%Y and the Adjust Amount should be a int/float\n"
          "***** Error : Found somewhere in : Date : " + str(i_price_target_date) + ", Price Target : " + str(i_price_target_amount))
        sys.exit(1)

    # -----------------------------------------------------
    # Check for duplicate dates and ask the user to fix
    # duplicate dates - This should be rare, and if it happens
    # then the user needs to clean the json file
    # -----------------------------------------------------
    logging.debug("The price Target datelist is : " + str(price_target_date_list_dt))
    if (len(price_target_date_list_dt) != len(set(price_target_date_list_dt))):
      duplicate_items_list = [k for k,v in Counter(price_target_date_list_dt).items() if v>1]
      logging.error ("There are some duplicate dates in the Price_Target in Price Target json file...Please correct and rerun")
      logging.error ("Duplicates : " + str(duplicate_items_list))
      sys.exit(1)
    # -----------------------------------------------------

    # -----------------------------------------------------
    # Convert the date and the target amount arrays to np arrays
    # Then sort the date array - that will give us the index of
    # the sorted array. Then sort the target amount array with
    # the same indexes so they are sorted "in sync"
    # -----------------------------------------------------
    price_target_date_list_dt_np = np.array(price_target_date_list_dt)
    price_target_amount_list_np = np.array(price_target_amount_list)
    price_target_date_list_sorted_idx = np.flip(np.array(price_target_date_list_dt).argsort())
    logging.debug("The SORTED PT datelist index : " + str(price_target_date_list_sorted_idx))

    price_target_date_list_sorted_dt = price_target_date_list_dt_np[price_target_date_list_sorted_idx]
    price_target_amount_list_sorted = price_target_amount_list_np[price_target_date_list_sorted_idx]
    logging.debug("The SORTED PT datelist  : " + str(price_target_date_list_sorted_dt))
    logging.debug("The SORTED PT amount    : " + str(price_target_amount_list_sorted))
    about_1month_old_pt_date_dt = price_target_date_list_sorted_dt[0] - relativedelta(months=1)
    # logging.debug ("Latest PT date : " + str(price_target_date_list_sorted_dt[0]) + ", Date one month previous to that : " + str(about_1month_old_pt_date_dt))

    # Now match the one month prior date in the PT datelist
    # to get the index of that 1 month old date
    # Use that index to get the PT corresponding for that 1 month old matched date
    # Lastly compute the %change in the price targets (current vs the one month ago)
    # Finally - store all those 5 pieces of information in the df
    if (len(price_target_date_list_sorted_dt) > 1):
      prev_pt_date_match_dt = min(price_target_date_list_sorted_dt, key=lambda d: abs(d - about_1month_old_pt_date_dt))
      prev_pt_date_match_dt_index = np.where(price_target_date_list_sorted_dt == prev_pt_date_match_dt)
      logging.debug ("Latest PT date : " + str(price_target_date_list_sorted_dt[0]) + ", Date one month previous to that : " + str(prev_pt_date_match_dt) + ", at index : " + str(prev_pt_date_match_dt_index))
      prev_pt_val = price_target_amount_list_sorted[prev_pt_date_match_dt_index]
      logging.debug ("Latest PT date : " + str(price_target_date_list_sorted_dt[0]) +
                     ", Date one month previous to that : " + str(prev_pt_date_match_dt) +
                     ", at index : " + str(prev_pt_date_match_dt_index) +
                     ", PT at one month previous date : " + str(prev_pt_val))
    else:
      prev_pt_date_match_dt = price_target_date_list_sorted_dt[0]
      prev_pt_val = price_target_amount_list_sorted[0]

    price_target_df.loc[ticker, 'Latest_PT'] = price_target_amount_list_sorted[0]
    price_target_df.loc[ticker, 'Previous_PT'] = prev_pt_val
    price_target_df.loc[ticker, 'PT_Change'] = ((price_target_amount_list_sorted[0]/prev_pt_val)-1)*100
    price_target_df.loc[ticker, 'Latest_Date'] = price_target_date_list_sorted_dt[0]
    price_target_df.loc[ticker, 'One_Month_Old_Date'] = prev_pt_date_match_dt
  # ---------------------------------------------------------------------------

  # if (i_int > 26):
  #   break


# -----------------------------------------------------------------------------
# Print all the df to their respective files
# -----------------------------------------------------------------------------
logging.info("")
logging.info("Now saving sorted data in " + str(dir_path + log_dir) + " directory")
logging.info("All the files with sorted data will be available there. Please look there when the script completes")
historical_last_updated_logfile = "historical_last_updated.txt"
earnings_report_date_1qtr_ago_logfile = "earnings_reported_1qtr_ago.txt"
earnings_report_date_4qtr_ago_logfile = "earnings_reported_4qtr_ago.txt"
eps_projections_last_updated_logfile = "eps_projections_last_updated.txt"
charts_last_updated_logfile = "charts_last_updated.txt"
skipped_tickers_logfile="skipped_tickers_Sort_misc.txt"
eps_report_newer_than_eps_projection_logfile = "eps_report_newer_than_eps_projection.txt"
eps_report_by_month_logfile = "eps_report_by_month.txt"
price_target_logfile="Price_Target_Change.csv"


historical_last_updated_df.sort_values(by=['Date','Ticker'], ascending=[True,True]).to_csv(dir_path + log_dir + "\\" + historical_last_updated_logfile,sep=' ', index=True, header=False)
earnings_report_date_1qtr_ago_df.sort_values(by=['Where_found','Reason','Date','Ticker'], ascending=[True,True,True,True]).to_csv(dir_path + log_dir + "\\" + earnings_report_date_1qtr_ago_logfile,sep=' ', index=True, header=False)
earnings_report_date_4qtr_ago_df.sort_values(by=['Where_found','Reason','Date','Ticker'], ascending=[True,True,True,True]).to_csv(dir_path + log_dir + "\\" + earnings_report_date_4qtr_ago_logfile,sep=' ', index=True, header=False)
eps_projections_last_updated_df.sort_values(by=['Date','Ticker','Reason'], ascending=[True,True,True]).to_csv(dir_path + log_dir + "\\" + eps_projections_last_updated_logfile,sep=' ', index=True, header=False)
charts_last_updated_df.sort_values(by=['Date','Ticker'], ascending=[True,True]).to_csv(dir_path + log_dir + "\\" + charts_last_updated_logfile,sep=' ', index=True, header=False)
skipped_tickers_df.sort_values(by=['Ticker'], ascending=[True]).to_csv(dir_path + log_dir + "\\" + skipped_tickers_logfile,sep=' ', index=True, header=True)
eps_report_newer_than_eps_projection_df.sort_values(by='Actual_EPS_Report').to_csv(dir_path + log_dir + "\\" + eps_report_newer_than_eps_projection_logfile,sep=' ', index=True, header=True)
eps_report_by_month_df.to_csv(dir_path + log_dir + "\\" + eps_report_by_month_logfile,sep=' ', index=True, header=True)
price_target_df.sort_values(by=['PT_Change'], ascending=[False]).to_csv(dir_path + log_dir + "\\" + price_target_logfile,sep=',', index=True, header=True)

logging.info("Created : " + str(historical_last_updated_logfile) + " <-- Sorted by date - based on the last Price date in their respective historical file")
logging.info("Created : " + str(earnings_report_date_1qtr_ago_logfile) + " <-- Sorted by date - based on when their Last Quarter Earnings Date in their respective Earnings file")
logging.info("Created : " + str(earnings_report_date_4qtr_ago_logfile) + " <-- Sorted by date - based on when their Last Year Earnings Date in their respective Earnings file")
logging.info("Created : " + str(eps_projections_last_updated_logfile) + " <-- Sorted by date - based on when the Earnings Projections were updated in their respective Earnings file")
logging.info("Created : " + str(charts_last_updated_logfile) + " <-- Sorted by date - based on when the Chart was creates in the Charts directory")
logging.info("Created : " + str(skipped_tickers_logfile) + " <-- Sorted by Ticker - Lists all the tickers that were skipped along with a reason")
logging.info("Created : " + str(eps_report_newer_than_eps_projection_logfile) + " <-- THIS FILE SHOULD BE EMPTY. It is a BAD thing if this file is not emptly. The file has the tickers for which the earnings projections are newer than the reported earnings date")
logging.info("Created : " + str(eps_report_by_month_logfile) + " <-- Sorted by Month - Lists number of qtr earnings reports by month...Can use to help manage your workload")
logging.info("Created : " + str(price_target_logfile) + " <-- Sorted by PT % Change - Lists tickers sorted by their PT changes (curr PT vs Previous PT) in descending order")

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

