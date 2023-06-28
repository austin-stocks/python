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

# Read the IBD Industry Group Running file. This file right now is created manually 
# by Sundeep every weekend. I think that IBD updates the Industry Rankings on Fridays
# and that also get reflected in the Data tables (the screener that I use to
# shortly afterwards. However, to be
# on the safer side, I download both the Industry rankings and data tables on 
# Saturday or Sunday - but still give it a Friday date to be consistent
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
logging.debug("Will eavluate and Rank the Industry Groups for dates : " + str(weekly_dates_list))

# This df will eventually contain the Industry groups that will pass our 
# criteria. Right now the criteria is that we have decreasing Industry 
# group rank (decreasing means good) for 8 weeks
inds_best_rank_8wks_df = pd.DataFrame(columns=['Industry_Group','Rank'])
inds_best_rank_8wks_df.set_index('Industry_Group', inplace=True)

# =============================================================================
# Parse the running industry group file to find out that industry groups that 
# match our criteria. Right now we have two criteria
# 1. Inustries which has lowest ranks sometime in the last 3 weeks with the 
#    last 8 weeks
# 2. Inustries which has lowest ranks this weeks in the last 8 weeks.
# 3. We can add more criteria as we progress and think through this
# =============================================================================
inds_best_rank_sometime_in3wks_out_of_8wks_cnt = 0
inds_best_rank_8wks_cnt = 0
for inds_name in inds_gp_list:
  logging.debug("\n")
  # logging.debug("Industry Name : " + str(inds_name))
  inds_gp_series = ibd_inds_gp_rank_df.loc[inds_name]
  # logging.debug("The Industry Series is : \n" + str(inds_gp_series))
  inds_rank_list = []
  # Note that weekly dates list is already truncated above to the 
  # desired length (determined by no_of_weeks_to_lookback)
  for date_dt in weekly_dates_list:
    inds_rank = inds_gp_series[date_dt]
    logging.debug("Industry Name : " + str(inds_name) + ", Date : " + str(date_dt) + ", Rank : " + str(inds_rank))
    inds_rank_list.append(inds_rank)

  logging.debug("The Rank list for : " + str(inds_name) + ", is : " + str(inds_rank_list))
  # Check if atleast one of the last 3 weeks are the lowest in the last 8 weeks
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
    inds_best_rank_sometime_in3wks_out_of_8wks_cnt += 1
    logging.debug(str(inds_name).ljust(30) + ", Current Rank : " + str(rank_week_m0).ljust(5) + str(inds_rank_list[1:8]).ljust(40) + " has lowest rank sometime within last 3 weeks out of last 8 weeks")
    # If they are and the ranking has been improving in the last 3 weeks too, then
    # all the better. These are the inds groups for which we should get the high
    # ranking stocks to look at every week
    if ((rank_week_m0 <= rank_week_m1) and (rank_week_m1 <= rank_week_m2)):
      inds_best_rank_8wks_cnt += 1
      # TODO : Put this industry in a df / list so that it can be then used
      # later to pull out all the tickers (or the best 10% rated tickers
      # from the data tables xlsx
      logging.info(str(inds_name).ljust(30) + ", Current Rank : " + str(rank_week_m0).ljust(5) + str(inds_rank_list[1:8]).ljust(40) + " has the lowest rank in the last 8 weeks")
      # inds_best_rank_8wks_df.loc[inds_name.strip()] = rank_week_m0
      inds_best_rank_8wks_df.loc[inds_name] = rank_week_m0

logging.info("")
logging.info("Found " + str(inds_best_rank_sometime_in3wks_out_of_8wks_cnt).ljust(5) + " industries that had best rank sometime in the last 3 weeks out of last 8 weeks")
logging.info("Found " + str(inds_best_rank_8wks_cnt).ljust(5) + " industries that had best rank this week out of last 8 weeks")

# =============================================================================

# =============================================================================
# Next step is to read the data tables and find out all the tickers that
# are in the industry groups that have lowest rank in the current weeks vs
# last 8 weeks and put them in a csv/xlsx and they become the watchlist
# =============================================================================
ibd_data_tables_file = latest_weekly_date_str + "-Data_Tables.csv"
ibd_data_tables_file = "2023-06-23" + "-Data_Tables.csv"
logging.debug("Opening file " + str(dir_path + ibd_data_tables_dir + "\\" + ibd_data_tables_file))
# ibd_data_tables_df = pd.read_excel(dir_path + ibd_data_tables_dir + "\\" + ibd_data_tables_file, sheet_na
# me="Stock_list",engine='xlrd')
ibd_data_tables_df = pd.read_csv(dir_path + ibd_data_tables_dir + "\\" + ibd_data_tables_file,encoding = "ISO-8859-1")
logging.debug("The Data tables file is : \n" + ibd_data_tables_df.to_string())
best_rank_in_8wks_filter_list = inds_best_rank_8wks_df['Rank'].tolist()
best_rank_in_8wks_filter_list.sort(reverse=False)
logging.debug("The ranks to filter (grep) out from the Data tables file are : " + str(best_rank_in_8wks_filter_list))

best_ranks_in_8wks_df = ibd_data_tables_df.loc[ibd_data_tables_df['Industry Group Rank'].isin(best_rank_in_8wks_filter_list)]
logging.debug("The extracted rows from Data tables that have best ranks in 8 weeks are")
logging.debug("These are the tickers that we should be doing furthur research on\n" + best_ranks_in_8wks_df.to_string())
# Add the industry Name column to the dataframe and do a reverse lookup into the
# inds_best_rank_8wks_df to find out the industry name and populate it
best_ranks_in_8wks_df.insert(2,"Industry Name", " ")
best_ranks_in_8wks_df.reset_index
best_ranks_in_8wks_df.set_index('Symbol', inplace=True)

for i_index, row in best_ranks_in_8wks_df.iterrows():
  ticker = i_index
  ticker_rank = row['Industry Group Rank']
  ticker_inds_name = ibd_inds_gp_rank_df[ibd_inds_gp_rank_df[weekly_dates_list[0]] == ticker_rank].index.values
  best_ranks_in_8wks_df.at[i_index, 'Industry Name'] = "{}".format(*ticker_inds_name)
  logging.debug("Ticker : " + str(ticker) + ", It's Industry Rank : " + str(ticker_rank) + ", Industry Name "  + str(ticker_inds_name))

# Finally rearrage the colums of the dataframe to Sundeep's liking
desired_column_placement = ["Symbol", "Price", "Vol- 50 Day Avg. (1000s)","Industry Name", "Industry Group Rank",
                            "Comp. Rating","EPS Rating", "RS Rating", "Acc/Dis Rating", "Ind Grp RS", "SMR Rating", "Spon Rating", "PE Ratio",
                            "# of Funds - last reported qrtr",
                            "Last Qtr EPS % Chg.", "Curr Qtr EPS Est. % Chg.",
                            "Curr Yr EPS Est. % Chg.",
                            "Last Qtr Sales % Chg.",
                            "Pretax Margin",
                            "IPO Date",
                            "Vol. (1000s)",
                            "Div Yield",
                            "Vol. % Change",
                            "Price $ Change","Price % Change"]
best_ranks_in_8wks_df.reset_index(inplace=True)
best_ranks_in_8wks_df = best_ranks_in_8wks_df[desired_column_placement]
best_ranks_in_8wks_df.set_index('Symbol', inplace=True)

# Publist the results
inds_best_rank_8wks_logfile=latest_weekly_date_str + "-Industries_with_best_ranks_8wks.csv"
# inds_best_rank_8wks_df.sort_values(by=['Rank'], ascending=[True]).to_csv(dir_path + log_dir + "\\" + inds_best_rank_8wks_logfile,sep=',', index=True, header=True,encoding = "ISO-8859-1")
inds_best_rank_8wks_df.sort_values(by=['Rank'], ascending=[True]).to_csv(dir_path + log_dir + "\\" + inds_best_rank_8wks_logfile,sep=',', index=True, header=True)
logging.info("Created : " + str(inds_best_rank_8wks_logfile) + " <-- Sorted by IBD Industry Rank")

tickers_in_best_ranks_in_8wks_logfile= latest_weekly_date_str + "-Tickers_in_Industries_with_best_ranks_8wks.csv"
best_ranks_in_8wks_df.sort_values(by=['Industry Group Rank','Comp. Rating','Symbol'], ascending=[True,False,True]).to_csv(dir_path + log_dir + "\\" + tickers_in_best_ranks_in_8wks_logfile,sep=',', index=True, header=True)
logging.info("Created : " + str(tickers_in_best_ranks_in_8wks_logfile) + " <-- Sorted by IBD Industry Rank")
# =============================================================================

