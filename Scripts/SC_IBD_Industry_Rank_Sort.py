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
import xlsxwriter


def human_format(num, precision=2, suffixes=['', 'K', 'M', 'B', 'T', 'P']):
  m = sum([abs(num / 1000.0 ** x) >= 1 for x in range(1, len(suffixes))])
  return f'{num / 1000.0 ** m:.{precision}f}{suffixes[m]}'

# -----------------------------------------------------------------------------
# Read the master tracklist file into a dataframe
# -----------------------------------------------------------------------------
dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
log_dir = "\\..\\" + "Logs"
ibd_inds_gp_dir = "\\..\\" + "IBD" + "\\" + "IBD-Industry-Groups"
ibd_data_tables_dir = "\\..\\" + "IBD" + "\\" + "Data_Tables"
ibd_inds_gp_file = "Industry-Groups-Running-Rank.xlsx"
master_tracklist_file = "Master_Tracklist.xlsm"

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

master_tracklist_df = pd.read_excel(dir_path + user_dir + "\\" + master_tracklist_file, sheet_name="Main")
master_tracklist_ticker_list = master_tracklist_df['Tickers'].tolist()
logging.debug("The tickers in Master Tracklist are :  " + str(master_tracklist_ticker_list))

# Read the IBD Industry Group Running file. This file right now is created manually
# by Sundeep every weekend. I think that IBD updates the Industry Rankings on Fridays
# and that also get reflected in the Data tables (the screener that I use to
# shortly afterwards.
# However, to be on the safer side, I download both the Industry rankings and
# data tables on Saturday or Sunday - but still give it a Friday date to be consistent
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
logging.debug("Weekly Date List from IBD Industry Group File : " + str(weekly_dates_list))

# ---------------------------------------------------------
# Remove all right hand side of the weekly dates list, if Sundeep
# wants to do run this macro for the older date
# run_for_weekly_date_str = "6/23/2023"
# ---------------------------------------------------------
run_for_weekly_date_str = ""
if (run_for_weekly_date_str):
  logging.info("Generating the Industry Ranking and processing IBD Data Tables for the date : " + str(run_for_weekly_date_str))
  run_for_weekly_date_dt = dt.datetime.strptime(run_for_weekly_date_str, '%m/%d/%Y')
  if (run_for_weekly_date_dt in weekly_dates_list):
    match_position = weekly_dates_list.index(run_for_weekly_date_dt)
    logging.debug("Found " + str(run_for_weekly_date_str) + ", at position " + str(match_position))
    logging.debug("Truncating the date list to not contain any newer dates than " +str(run_for_weekly_date_str))
    # Delete all dates from the list to the left of the match position
    del weekly_dates_list[:match_position]
    logging.debug("Weekly Date list after removing all the dates to the left of the user defind date" + str(weekly_dates_list))
  else:
    logging.error("")
    logging.error("==========================================================================")
    logging.error("The date : " + str(run_for_weekly_date_str) + ",  for which you want to rank the Industry Group is NOT found in " + str(ibd_inds_gp_file))
    logging.error("The date should be in the format %m/%d/%Y, and should be assigned to the varilable run_for_weekly_date_str a few lines above this line in the script")
    logging.error("Please correct and rerun")
    logging.error("==========================================================================")
# ---------------------------------------------------------

# TODO : Sanity check that all the dates are no more than 9 days
# apart, otherwise it suggest a skipped week
# Truncate the list to 10 elements - as we only want to look at 10 weeks -
# This can be easily changed to whatever weeks we need
no_of_weeks_to_lookback = 10
del weekly_dates_list[no_of_weeks_to_lookback:]
weekly_dates_str_list = [dt.datetime.strftime(date, '%m/%d/%Y') for date in weekly_dates_list]
latest_weekly_date_str = dt.datetime.strptime(weekly_dates_str_list[0], '%m/%d/%Y').strftime("%Y-%m-%d")
logging.debug("Eavluating Rankings in the Industry Groups for dates : " + str(weekly_dates_list))
logging.info("")
logging.info("Eavluating Rankings in the Industry Groups starting at  : " + str(latest_weekly_date_str))
logging.info("")

# This df will eventually contain the Industry groups that will pass our 
# criteria. Right now the criteria is that we have decreasing Industry 
# group rank (decreasing means good) for 8 weeks
inds_best_rank_8wks_df = pd.DataFrame(columns=['Industry_Group','Rank'])
inds_best_rank_8wks_df.set_index('Industry_Group', inplace=True)

# =============================================================================
# Parse the running industry group file to find out that industry groups that 
# match our criteria. Right now we have two criteria
# 1. Inustries which have lowest ranks sometime in the last 3 weeks
#    within the last 8 weeks
# 2. Inustries which have lowest ranks this week in the last 8 weeks.
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
      logging.info(str(inds_name).ljust(30) + ", Current Rank : " + str(rank_week_m0).ljust(5) + str(inds_rank_list[1:8]).ljust(40) + " has the lowest rank in the last 8 weeks")
      inds_best_rank_8wks_df.loc[inds_name] = rank_week_m0

logging.info("")
logging.info("Found " + str(inds_best_rank_sometime_in3wks_out_of_8wks_cnt).ljust(5) + " industries that had best rank sometime in the last 3 weeks out of last 8 weeks")
logging.info("Found " + str(inds_best_rank_8wks_cnt).ljust(5) + " industries that had best rank this week out of last 8 weeks")
# =============================================================================

# =============================================================================
# Now that we have the industries with good rank then get the tickers corresponding
# to those industries and then go from there.
# Next step is to read the data tables and find out all the tickers that
# are in the industry groups that have lowest rank in the current weeks vs
# last 8 weeks and put them in a csv/xlsx and they become the watchlist
# TODO : 06/29/2023 : Sundeep
# Another idea is to ignore the industry group but just see which stocks
# have RS rating improve (starting at 60 and now more than 75) in the
# last 3-4 weeks. This can also be done on the daily file but that can be
# another macro that does that, one that operates on daily ibd_data tables
# =============================================================================
logging.debug("The Latest weekly date extracted from Industry-Group-Running file : " + str(latest_weekly_date_str))
ibd_data_tables_file = latest_weekly_date_str + "-Data_Tables.csv"
logging.debug("Opening file " + str(dir_path + ibd_data_tables_dir + "\\" + ibd_data_tables_file))
# -------------------------------------------------------------


# ---------------------------------------------------------
# Clean the data from the Data tables, as some of the columns
# are read as string and some columns have "," and they are
# actually floats, while somre are read as strings but are dates
logging.info("")
logging.info("Starting to Process IBD Data Tables file : " + str(dir_path + ibd_data_tables_dir + "\\" + ibd_data_tables_file))
ibd_data_tables_df = pd.read_csv(dir_path + ibd_data_tables_dir + "\\" + ibd_data_tables_file,encoding = "ISO-8859-1")
logging.debug("The Data tables file is : \n" + ibd_data_tables_df.to_string())

tmp_int = ibd_data_tables_df['Symbol'].tolist()
logging.info("Cleaning up the data in the IBD Data Tables file, it has " + str(len(tmp_int)).ljust(6) + " tickers...")
logging.info("...No entries will be removed, just data format will be made more usable in this step")
ibd_data_tables_df.reset_index
ibd_data_tables_df["Price"]                           = [float(str(i).replace(",", "")) for i in ibd_data_tables_df["Price"]]
ibd_data_tables_df["PE Ratio"]                        = [float(str(i).replace(",", "")) for i in ibd_data_tables_df["PE Ratio"]]
ibd_data_tables_df["RS Rating"]                       = [float(str(i).replace(",", "")) for i in ibd_data_tables_df["RS Rating"]]
ibd_data_tables_df["Last Qtr EPS % Chg."]             = [float(str(i).replace(",", "")) for i in ibd_data_tables_df["Last Qtr EPS % Chg."]]
ibd_data_tables_df["Curr Qtr EPS Est. % Chg."]        = [float(str(i).replace(",", "")) for i in ibd_data_tables_df["Curr Qtr EPS Est. % Chg."]]
ibd_data_tables_df["Curr Yr EPS Est. % Chg."]         = [float(str(i).replace(",", "")) for i in ibd_data_tables_df["Curr Yr EPS Est. % Chg."]]
ibd_data_tables_df["Last Qtr Sales % Chg."]           = [float(str(i).replace(",", "")) for i in ibd_data_tables_df["Last Qtr Sales % Chg."]]
ibd_data_tables_df["Pretax Margin"]                   = [float(str(i).replace(",", "")) for i in ibd_data_tables_df["Pretax Margin"]]
ibd_data_tables_df["# of Funds - last reported qrtr"] = [float(str(i).replace(",", "")) for i in ibd_data_tables_df["# of Funds - last reported qrtr"]]
ibd_data_tables_df["Vol- 50 Day Avg. (1000s)"]        = [float(str(i).replace(",", "")) for i in ibd_data_tables_df["Vol- 50 Day Avg. (1000s)"]]
ibd_data_tables_df["Vol. (1000s)"]                    = [float(str(i).replace(",", "")) for i in ibd_data_tables_df["Vol. (1000s)"]]
ibd_data_tables_df["Vol. % Change"]                   = [float(str(i).replace(",", "")) for i in ibd_data_tables_df["Vol. % Change"]]
ibd_data_tables_df['IPO Date']                        = ibd_data_tables_df['IPO Date'].fillna('1900-01-01')
ibd_data_tables_df["IPO Date"]                        = [dt.datetime.strptime(str(date), '%Y-%m-%d').date() for date in ibd_data_tables_df["IPO Date"]]
# ---------------------------------------------------------

# ---------------------------------------------------------
# Then filter the data tables based on the best industry ranks
# that were captured in the df from reading the inds running
# list file above
# ---------------------------------------------------------
best_rank_in_8wks_filter_list = inds_best_rank_8wks_df['Rank'].tolist()
best_rank_in_8wks_filter_list.sort(reverse=False)
logging.debug("The ranks to filter (grep) out from the Data tables file are : " + str(best_rank_in_8wks_filter_list))
ticker_with_best_ind_ranks_in_8wks_df = ibd_data_tables_df.loc[ibd_data_tables_df['Industry Group Rank'].isin(best_rank_in_8wks_filter_list)]
logging.debug("The extracted rows from Data tables that have best ranks in 8 weeks are")
logging.debug("These are the tickers that we should be doing furthur research on\n" + ticker_with_best_ind_ranks_in_8wks_df.to_string())
logging.debug("These are the tickers that we should be doing furthur research on\n" + ticker_with_best_ind_ranks_in_8wks_df.to_string())
tmp_int = ticker_with_best_ind_ranks_in_8wks_df['Symbol'].tolist()
logging.info("Captured/Filtered the tickers, from IBD Data Table file, that are in the Industry Groups that have their best ranks in last 8 wks...")
logging.info("...There are " + str(len(tmp_int)).ljust(6) + " tickers on the list")

# -------------------------------------------------------------

# -------------------------------------------------------------
# Add the various columns that will be useful while analyzing the
# list that was geenrated.
# -------------------------------------------------------------
logging.info("Inserting additional columns for profitspi, stockcharts and such and populating them appropriately")
ticker_with_best_ind_ranks_in_8wks_df.insert(2,"In Master", " ")    # Is Sundeep already tracking?
ticker_with_best_ind_ranks_in_8wks_df.insert(2,"SChart", " ")    # Stockcharts
ticker_with_best_ind_ranks_in_8wks_df.insert(2,"TD", " ")  # TD Ameritrade
ticker_with_best_ind_ranks_in_8wks_df.insert(2,"CNBC", " ")  # CNBC
ticker_with_best_ind_ranks_in_8wks_df.insert(2,"Y-Profile", " ")  # Yahoo Finance Profile
ticker_with_best_ind_ranks_in_8wks_df.insert(2,"Y-BS", " ")  # Yahoo Finance Balance Sheet
ticker_with_best_ind_ranks_in_8wks_df.insert(2,"SPI", " ")  # Profitspy
ticker_with_best_ind_ranks_in_8wks_df.insert(2,"AAII", " ")  # Profitspy
ticker_with_best_ind_ranks_in_8wks_df.insert(2,"Industry Name", " ")
ticker_with_best_ind_ranks_in_8wks_df.insert(2,"Price*Volume", " ")
ticker_with_best_ind_ranks_in_8wks_df.reset_index
ticker_with_best_ind_ranks_in_8wks_df.set_index('Symbol', inplace=True)

# Loop through all the tickers in the df
# 1. Do a reverse lookup into the ibd_inds_gp_rank_df to find out the industry name
#    (corresponding the the industry rank for the tikcer from the ibd data table)
#    and populate the Industry Name column
# 2. Populate the Price*Volume column
# 3. Populate the stockcharts link column
for i_index, row in ticker_with_best_ind_ranks_in_8wks_df.iterrows():
  ticker = i_index
  ticker_rank = row['Industry Group Rank']
  # Reverse lookup from ticker industry Rank to Industry Name
  ticker_inds_name = ibd_inds_gp_rank_df[ibd_inds_gp_rank_df[weekly_dates_list[0]] == ticker_rank].index.values
  ticker_price = row['Price']
  ticker_avg_vol = row['Vol- 50 Day Avg. (1000s)']
  price_times_vol = ticker_price*ticker_avg_vol*1000
  ticker_with_best_ind_ranks_in_8wks_df.at[i_index, 'Price*Volume'] = price_times_vol
  # ticker_with_best_ind_ranks_in_8wks_df.at[i_index, 'Price*Volume'] = human_format(price_times_vol)
  # ticker_with_best_ind_ranks_in_8wks_df.at[i_index, 'Price*Volume'] = f'{int(price_times_vol):,}'
  ticker_with_best_ind_ranks_in_8wks_df.at[i_index, 'Industry Name'] = "{}".format(*ticker_inds_name)
  ticker_with_best_ind_ranks_in_8wks_df.at[i_index, 'Y-Profile'] = 'https://finance.yahoo.com/quote/' + str(ticker)
  ticker_with_best_ind_ranks_in_8wks_df.at[i_index, 'SChart'] = 'https://stockcharts.com/h-sc/ui?s='+str(ticker)
  ticker_with_best_ind_ranks_in_8wks_df.at[i_index, 'SPI'] = 'https://www.profitspi.com/stock/view.aspx?v=stock-chart&uv=269175&p=' + str(ticker)
  ticker_with_best_ind_ranks_in_8wks_df.at[i_index, 'TD'] = 'https://research.tdameritrade.com/grid/public/research/stocks/earnings?period=qtr&section=0&symbol=' + str(ticker)
  ticker_with_best_ind_ranks_in_8wks_df.at[i_index, 'CNBC'] = 'https://www.cnbc.com/quotes/' + str(ticker) +'?tab=earnings'
  ticker_with_best_ind_ranks_in_8wks_df.at[i_index, 'AAII'] = 'https://www.aaii.com/stock/ticker/' + str(ticker)
  ticker_with_best_ind_ranks_in_8wks_df.at[i_index, 'Y-BS'] = 'https://finance.yahoo.com/quote/' + str(ticker) + "/balance-sheet"
  if (ticker in master_tracklist_ticker_list):
    logging.debug(str(ticker) + ", found in Master Tracklist")
    ticker_with_best_ind_ranks_in_8wks_df.at[i_index, 'In Master'] = 1
  else:
    ticker_with_best_ind_ranks_in_8wks_df.at[i_index, 'In Master'] = 0
  logging.debug("Ticker : " + str(ticker) + ", Price*Volume : " + str(price_times_vol) + ", Industry Rank : " + str(ticker_rank) + ", Industry Name "  + str(ticker_inds_name))

# Rearrage the colums of the dataframe to Sundeep's liking
desired_column_placement = ["Symbol", "RS Rating","Industry Name",
                            "Y-Profile", "SChart", "SPI", "TD", "CNBC","AAII","Y-BS",
                            "In Master",
                            "# of Funds - last reported qrtr",
                            "Price*Volume",  "Industry Group Rank",
                            "Comp. Rating","EPS Rating",  "Acc/Dis Rating", "Ind Grp RS", "SMR Rating", "Spon Rating", "PE Ratio",
                            "Last Qtr EPS % Chg.", "Curr Qtr EPS Est. % Chg.",
                            "Curr Yr EPS Est. % Chg.",
                            "Last Qtr Sales % Chg.",
                            "Pretax Margin",
                            "Price",
                            "IPO Date",
                            "Vol- 50 Day Avg. (1000s)","Vol. (1000s)",
                            "Div Yield",
                            "Vol. % Change",
                            "Price $ Change","Price % Change"]

ticker_with_best_ind_ranks_in_8wks_df.reset_index(inplace=True)
ticker_with_best_ind_ranks_in_8wks_df = ticker_with_best_ind_ranks_in_8wks_df[desired_column_placement]
# -------------------------------------------------------------
# Now the df can be futhur filtered based on Sundeep's subjective criterion
# 1. Filter out based on Price*Volume (any stock that has less than %M
# (or whatever) number Sundeep wants to pick)
# 2. Filter out if the number of funds are less than, say 100
# 3. Filter out any RS rating of less than 70
# -------------------------------------------------------------
logging.info("")
logging.info("Thinning down the ticker list furthur based on Sundeep's subjective criterion")
ticker_with_best_ind_ranks_in_8wks_filtered_df = ticker_with_best_ind_ranks_in_8wks_df.copy()

logging.info("    Price*Voulme              > 5000000")
ticker_with_best_ind_ranks_in_8wks_filtered_df = ticker_with_best_ind_ranks_in_8wks_filtered_df.loc[ticker_with_best_ind_ranks_in_8wks_df['Price*Volume'] > 5000000]
tmp_int = ticker_with_best_ind_ranks_in_8wks_filtered_df['Symbol'].tolist()
logging.info("...There are " + str(len(tmp_int)).ljust(6) + " tickers on the list")

logging.info("    Funds that hold the stock > 100")
ticker_with_best_ind_ranks_in_8wks_filtered_df = ticker_with_best_ind_ranks_in_8wks_filtered_df.loc[ticker_with_best_ind_ranks_in_8wks_df['# of Funds - last reported qrtr'] > 100]
tmp_int = ticker_with_best_ind_ranks_in_8wks_filtered_df['Symbol'].tolist()
logging.info("...There are " + str(len(tmp_int)).ljust(6) + " tickers on the list")

logging.info("    RS Rating                 > 70")
ticker_with_best_ind_ranks_in_8wks_filtered_df = ticker_with_best_ind_ranks_in_8wks_filtered_df.loc[ticker_with_best_ind_ranks_in_8wks_df['RS Rating'] > 70]
tmp_int = ticker_with_best_ind_ranks_in_8wks_filtered_df['Symbol'].tolist()
logging.info("...There are " + str(len(tmp_int)).ljust(6) + " tickers on the list")

ticker_with_best_ind_ranks_in_8wks_df.set_index('Symbol', inplace=True)
ticker_with_best_ind_ranks_in_8wks_filtered_df.set_index('Symbol', inplace=True)
logging.info("")
logging.info("")
logging.info("All Filtering is done... Now writing the reports in Log directory")
logging.info("--------------------------------------------------")
# =============================================================================



# =============================================================================
# Finally publist the results in the logs directory
# =============================================================================
inds_best_rank_8wks_logfile=latest_weekly_date_str + "-Industries_with_best_ranks_8wks.csv"
inds_best_rank_8wks_df.sort_values(by=['Rank'], ascending=[True]).to_csv(dir_path + log_dir + "\\" + inds_best_rank_8wks_logfile,sep=',', index=True, header=True)
logging.info("Created : " + str(inds_best_rank_8wks_logfile) + " <-- Just the Industries with best Ranks in the last 8 wks")

tickers_in_best_ranks_in_8wks_logfile= latest_weekly_date_str + "-Tickers_in_Industries_with_best_ranks_8wks.xlsx"
writer = pd.ExcelWriter(dir_path + log_dir + "\\" + tickers_in_best_ranks_in_8wks_logfile, engine='xlsxwriter')
ticker_with_best_ind_ranks_in_8wks_df.sort_values(by=['RS Rating','# of Funds - last reported qrtr','Price*Volume'], ascending=[False,False,False]).to_excel(writer)
logging.info("Created : " + str(tickers_in_best_ranks_in_8wks_logfile) + " <-- Tickers in the best ranked Industries in the last 8 weeks, with stockcharts links etc")
writer.save()

tickers_in_best_ranks_in_8wks_filtered_logfile= latest_weekly_date_str + "-Tickers_in_Industries_with_best_ranks_8wks_filtered.xlsx"
writer = pd.ExcelWriter(dir_path + log_dir + "\\" + tickers_in_best_ranks_in_8wks_filtered_logfile, engine='xlsxwriter')
ticker_with_best_ind_ranks_in_8wks_filtered_df.sort_values(by=['RS Rating','# of Funds - last reported qrtr','Price*Volume'], ascending=[False,False,False]).to_excel(writer)
logging.info("Created : " + str(tickers_in_best_ranks_in_8wks_filtered_logfile) + " <-- Tickers in the best ranked Industries in the last 8 weeks, with stockcharts links etc and filtered according to Sundeep's Criterion above")
writer.save()
# =============================================================================
