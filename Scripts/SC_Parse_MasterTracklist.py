import pandas as pd
import os
import sys
import time
import datetime as dt
import numpy as np



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
gt_1_qtr_old_financials_df = pd.DataFrame(columns=['Ticker','Date'])
gt_1_qtr_old_earnings_df = pd.DataFrame(columns=['Ticker','Date'])
gt_1_month_old_earnings_df = pd.DataFrame(columns=['Ticker','Date'])
likely_earnings_date_df = pd.DataFrame(columns=['Ticker','Date'])

gt_1_qtr_old_financials_df.set_index('Ticker', inplace=True)
gt_1_qtr_old_earnings_df.set_index('Ticker', inplace=True)
gt_1_month_old_earnings_df.set_index('Ticker', inplace=True)
likely_earnings_date_df.set_index('Ticker', inplace=True)

today = dt.date.today()
one_qtr_ago_date = today - dt.timedelta(days=80)
one_month_ago_date = today - dt.timedelta(days=25)
print ("Today is", today, "one month ago", one_month_ago_date, "one qtr ago", one_qtr_ago_date)
# -----------------------------------------------------------------------------



# -----------------------------------------------------------------------------
# Loop through all the tickers to check the dates when
# Their earnings were updated
#   Flag if the earnings were update more than a qtr ago
#   Flag if the earnings were update more than a month ago
# Their financials were updated
#   Flag if the financials were update more than a qtr ago
# Their earnings were reported
#   Flag if today is 80 days out from the report date - because the earnings
#   reporting may be coming soon
#   Right now this can be used to go to some website (zacks, yahoo) to find out
#   which stocks are going to report earnings soon - and the list gives a clue
#   on what stocks that may be. That can be used to populate another column
#   in the tracklist - that puts a data of upcoming earnings.
# Maybe at at later date - when I get some clarity - I can add a actual earnings
# date from zacks/yahoo and do a opposite calcuations - saying that earnings is
# coming up in the next 10 days or so
# -----------------------------------------------------------------------------
for ticker_raw in ticker_list:
  ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase
  date_updated_earnings = master_tracklist_df.loc[ticker, 'Last_Updated_EPS_Projections']
  date_updated_financials = master_tracklist_df.loc[ticker, 'Last_Updated_Financials']
  last_earnings_date = master_tracklist_df.loc[ticker, 'Last_Earnings_Date']

  # print ("Processing", ticker, "Last date for updated Earnings", date_updated_earnings, "Last Date for updated Fiancials", date_updated_financials)

  # Check if the last_updated_earnings date is NOT NaT then compare it against todays date
  if (not pd.isnull(date_updated_earnings)):
    # Compare with the dates
    date_updated_earnings_dt = dt.datetime.strptime(str(date_updated_earnings), '%Y-%m-%d %H:%M:%S').date()
    if (date_updated_earnings_dt < one_qtr_ago_date):
      print("Processing", ticker," : Earnings were updated on:", date_updated_earnings_dt, "more than a quarter ago")
      gt_1_qtr_old_earnings_df.loc[ticker]= [date_updated_earnings_dt]
    if (date_updated_earnings_dt < one_month_ago_date):
      print("Processing", ticker," : Earnings were updated on:", date_updated_earnings_dt, " more than a month ago")
      gt_1_month_old_earnings_df.loc[ticker]= [date_updated_earnings_dt]

  if (not pd.isnull(date_updated_financials)):
    date_updated_financials_dt = dt.datetime.strptime(str(date_updated_financials), '%Y-%m-%d %H:%M:%S').date()
    if (date_updated_financials_dt < one_month_ago_date):
      gt_1_qtr_old_financials_df.loc[ticker] = [date_updated_financials_dt]

  if (not pd.isnull(last_earnings_date)):
    last_earnings_date_dt = dt.datetime.strptime(str(last_earnings_date), '%Y-%m-%d %H:%M:%S').date()
    if (today > (last_earnings_date_dt  + dt.timedelta(days=60))):
      print("Processing", ticker," : Last Earnings Reported Date was :", last_earnings_date_dt, " Maybe the company will report soon again")
      likely_earnings_date_df.loc[ticker] = [last_earnings_date_dt]

# -----------------------------------------------------------------------------
# Print all the df to their respective files
# -----------------------------------------------------------------------------
gt_1_qtr_old_earnings_df.sort_values(by='Date').to_csv('gt_1_qtr_old_earnings_df.txt',sep=' ', index=True, header=False)
gt_1_month_old_earnings_df.sort_values(by='Date').to_csv('gt_1_month_old_earnings.txt',sep=' ', index=True, header=False)
gt_1_qtr_old_financials_df.sort_values(by='Date').to_csv('gt_1_qtr_old_financials.txt',sep=' ', index=True, header=False)
likely_earnings_date_df.sort_values(by='Date').to_csv('likely_earnings_date.txt',sep=' ', index=True, header=False)
# -----------------------------------------------------------------------------

