import pandas as pd
import os
import sys
import time
import datetime as dt
import numpy as np


# todo
# Get the next eps projections and compare them with the current eps projections to see if the projections
# have been trending up or down and get the results in a csv file

# -----------------------------------------------------------------------------
# Read the master tracklist file into a dataframe
# -----------------------------------------------------------------------------
dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
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
# Declare all the dataframes that we are going to need to write into txt file
# and set their columns
# -----------------------------------------------------------------------------
today = dt.date.today()
one_qtr_ago_date = today - dt.timedelta(days=80)
one_month_ago_date = today - dt.timedelta(days=30)
print ("Today is", today, "one month ago", one_month_ago_date, "one qtr ago", one_qtr_ago_date)

gt_1_month_old_eps_projections_df = pd.DataFrame(columns=['Ticker','Date'])
gt_1_qtr_old_eps_projections_df = pd.DataFrame(columns=['Ticker','Date'])
likely_earnings_date_df = pd.DataFrame(columns=['Ticker','Date'])
eps_report_newer_tnan_eps_projection_df = pd.DataFrame(columns=['Ticker','Date_Report', 'Date_Earnings'])

gt_1_month_old_eps_projections_df.set_index('Ticker', inplace=True)
gt_1_qtr_old_eps_projections_df.set_index('Ticker', inplace=True)
likely_earnings_date_df.set_index('Ticker', inplace=True)
eps_report_newer_tnan_eps_projection_df.set_index('Ticker', inplace=True)
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Loop through all the tickers to check the dates when
# -----------------------------------------------------------------------------
# ticker_list = ['AUDC']
for ticker_raw in ticker_list:
  ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase
  print("\nProcessing : ", ticker)
  # if ticker in ["CCI", , "CY", "EXPE", "FLS", "GCBC","GOOG","HURC","KMI","KMX","PNFP","QQQ","RCMT","TMO","TMUS","TTWO",,"WLTW"]:
  if ticker in ["QQQ"]:
    print ("File for ", ticker, "does not exist in earnings directory. Skipping...")
    continue
  ticker_is_wheat = master_tracklist_df.loc[ticker, 'Quality_of_Stock']
  if (ticker_is_wheat != 'Wheat'):
    print (ticker , " is not Wheat...skipping")
    continue

  # ---------------------------------------------------------------------------
  # Get the last and one before that projected earnings update date from the earnings.csv file
  # ---------------------------------------------------------------------------
  earnings_file = ticker + "_earnings.csv"
  earnings_file_fullpath = os.path.join("C:\Sundeep\Stocks_Automation\Earnings", earnings_file)
  qtr_eps_df = pd.read_csv(earnings_file_fullpath)
  if 'Q_EPS_Projections_Date_0' in qtr_eps_df.columns:
    eps_projection_date_0 = qtr_eps_df['Q_EPS_Projections_Date_0'].tolist()[0]
    print ("Last Q EPS was updated in", earnings_file, " on ",eps_projection_date_0)
    eps_projection_date_0_dt = dt.datetime.strptime(str(eps_projection_date_0), '%m/%d/%Y').date()
  else:
    print("Column Q_EPS_Projections_Date_0 DOES NOT exist in ", earnings_file)
    sys.exit(1)
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Get the last earnings report date from Master Tracklist
  # ---------------------------------------------------------------------------
  eps_report_date = dt.datetime.strptime(str(master_tracklist_df.loc[ticker, 'Last_Earnings_Date']),'%Y-%m-%d %H:%M:%S').date()
  if ((ticker_is_wheat == "Wheat") and pd.isnull(eps_report_date)):
    print ("**********************  ERROR ERROR ERROR ERROR ****************************")
    print ("Error - ", ticker , "is wheat and does not have a earnings date. Exiting....")
    print ("**********************  ERROR ERROR ERROR ERROR ****************************")
    sys.exit(1)
  eps_report_date_dt = dt.datetime.strptime(str(eps_report_date), '%Y-%m-%d').date()
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Check if the Last EPS Projections update date in older than a month or a qtr
  # ---------------------------------------------------------------------------
  date_year = eps_projection_date_0_dt.year
  # print ("The Year when EPS Projection was updated is : ", date_year)
  if (date_year < 2019):
    print ("\n\n==========     Error : The date for ", ticker, " EPS Projections is older than 2019     ==========")
    continue
    sys.exit(1)

  if (eps_projection_date_0_dt < one_month_ago_date):
    print("EPS Projections were updated on : ", eps_projection_date_0_dt, " more than a month ago")
    gt_1_month_old_eps_projections_df.loc[ticker]= [eps_projection_date_0_dt]

  if (eps_projection_date_0_dt < one_qtr_ago_date):
    print("EPS Projections were updated on : ", eps_projection_date_0_dt, " more than a quarter ago")
    gt_1_qtr_old_eps_projections_df.loc[ticker]= [eps_projection_date_0_dt]
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Check if the eps report date is older than - say 80 days - This means that
  # the company is likely to report earnings soon
  # ---------------------------------------------------------------------------
  date_year = eps_report_date_dt.year
  # print ("The Year of the last reported earnings is : ", date_year)
  if (date_year < 2019):
    print ("==========     Error : The date for ", ticker, " last earnings is older than 2019     ==========")
    sys.exit()
  if (today > (eps_report_date_dt  + dt.timedelta(days=100))):
    print("Last Earnings Reported Date was : ", eps_report_date_dt, " Maybe the company will report soon again")
    likely_earnings_date_df.loc[ticker] = [eps_report_date_dt]
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Check if the last eps reported earnings date is later (newer) than when the
  # eps projection was updated in the earnings file
  # This means that the earnings projections was updated before the eps report date
  # and so the earnings file needs to be updated now with the eps projections
  if (eps_report_date_dt > eps_projection_date_0_dt):
    print("Last Earnings Reported Date : ", eps_report_date_dt, " is newer than EPS Projections Update Date : ", eps_projection_date_0_dt, " This is unusal...please fix immediately")
    eps_report_newer_tnan_eps_projection_df.loc[ticker] = [eps_report_date_dt,eps_projection_date_0_dt]
  # ---------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Print all the df to their respective files
# -----------------------------------------------------------------------------
gt_1_month_old_eps_projections_df.sort_values(by='Date').to_csv('gt_1_month_old_eps_projections.txt',sep=' ', index=True, header=False)
gt_1_qtr_old_eps_projections_df.sort_values(by='Date').to_csv('gt_1_qtr_old_eps_projections_df.txt',sep=' ', index=True, header=False)
likely_earnings_date_df.sort_values(by='Date').to_csv('likely_earnings_date.txt',sep=' ', index=True, header=False)
eps_report_newer_tnan_eps_projection_df.sort_values(by='Date_Report').to_csv('report_newer_than_earnings.txt',sep=' ', index=True, header=False)
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


''' Not sure why is do we need this...
# ---------------------------------------------------------------------------
# Get the last quarter of reported earning to match in the earnings csv file
# ---------------------------------------------------------------------------
qtr_eps_date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in qtr_eps_df.Q_Date.tolist()]
# Now get the date
eps_date_list_eps_report_date_match = min(qtr_eps_date_list, key=lambda d: abs(d - eps_report_date))
eps_date_list_eps_report_date_index = qtr_eps_date_list.index(eps_date_list_eps_report_date_match)
print("The match date for Last reported Earnings date : ", str(eps_report_date), " in the Earnings df is : ",
      str(eps_date_list_eps_report_date_match), " at index ", str(eps_date_list_eps_report_date_index))
# If the date match in the eps_date_list is a date in the future date (that can happen if
# the eps_report_date is more than 45 days after the quarter date. In this case we need to
# move the match date index back by a quarter (by adding 1 to it - as the index starts
# from 0 for the futuremost date)
if (
  (eps_date_list_eps_report_date_match >= dt.date.today()) or (eps_date_list_eps_report_date_match >= eps_report_date)):
  eps_date_list_eps_report_date_index += 1
  eps_date_list_eps_report_date_match = qtr_eps_date_list[eps_date_list_eps_report_date_index]

# ---------------------------------------------------------------------------
'''