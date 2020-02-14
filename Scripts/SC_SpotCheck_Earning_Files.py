import pandas as pd
import os
import sys
import time
import datetime as dt
import numpy as np
import logging
import math


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
                    filename=dir_path + log_dir + "\\" + 'SC_SpotCheck_Earning_files.txt',
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


# -----------------------------------------------------------------------------
# Declare all the dataframes that we are going to need to write into txt file
# and set their columns
# -----------------------------------------------------------------------------
ignore_qtr_eps_date_staleness_list = [
'SNBR','CCI','GTLS','POOL','ACU','CDNS','PSB','CSGP','RUSHA','LAD','ASGN','BOOM','FAF','LH','SAH','YNDX','WCN',
'TAYD','MEDP','OKE','LDOS','EME','ZBRA','MANT','MAS','MASI','CLH','FLS','QLYS','WYND','OLED','QDEL','FOXF','GNRC',
'GPN','EQIX','AMT','ANET','AMOT','ALSN','HMSY','BABA',
]

today = dt.date.today()
one_qtr_ago_date = today - dt.timedelta(days=80)
one_month_ago_date = today - dt.timedelta(days=15)
logging.info("Today : " + str(today) +  " One month ago : " +str(one_month_ago_date) + " One qtr ago : " +str(one_qtr_ago_date))

gt_1_month_old_eps_projections_df = pd.DataFrame(columns=['Ticker','Date'])
gt_1_qtr_old_eps_projections_df = pd.DataFrame(columns=['Ticker','Date'])
likely_earnings_date_df = pd.DataFrame(columns=['Ticker','Date'])
eps_report_newer_than_eps_projection_df = pd.DataFrame(columns=['Ticker','Earnings_Reported', 'Earnings_Projections_Updated'])
projected_eps_analysis_df = pd.DataFrame(columns=['Ticker','All_Projected_EPS_Positive','EPS_2.5%','EPS_5%','EPS_7.5%','EPS_10%','Earnings_Reported', 'Earnings_Projections_Updated_0', 'Earnings_Projections_Updated_1', 'Days_between_esp_projections_were_updated', 'Direction_of_latest_eps_projection', 'Direction_of_comparison_between_two_eps_projections'])
eps_report_newer_tnan_eps_projection_df = pd.DataFrame(columns=['Ticker','Actual_EPS_Report','EPS_Projections_Last_Updated'])
gt_1_month_old_historical_update_df = pd.DataFrame(columns=['Ticker','Date'])

gt_1_month_old_eps_projections_df.set_index('Ticker', inplace=True)
gt_1_qtr_old_eps_projections_df.set_index('Ticker', inplace=True)
likely_earnings_date_df.set_index('Ticker', inplace=True)
eps_report_newer_than_eps_projection_df.set_index('Ticker', inplace=True)
projected_eps_analysis_df.set_index('Ticker', inplace=True)
eps_report_newer_tnan_eps_projection_df.set_index('Ticker', inplace=True)
gt_1_month_old_historical_update_df.set_index('Ticker', inplace=True)
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Loop through all the tickers to check the dates when
# -----------------------------------------------------------------------------
# ticker_list = ['AUDC', 'MED']
for ticker_raw in ticker_list:
  ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase
  logging.debug("================================")
  logging.info("Processing : " + str(ticker))
  # if ticker in ["CCI", , "CY", "EXPE", "FLS", "GCBC","GOOG","HURC","KMI","KMX","PNFP","QQQ","RCMT","TMO","TMUS","TTWO",,"WLTW"]:
  if ticker in ["QQQ"]:
    print ("File for ", ticker, "does not exist in earnings directory. Skipping...")
    continue
  quality_of_stock = master_tracklist_df.loc[ticker, 'Quality_of_Stock']
  if ((quality_of_stock != 'Wheat') and (quality_of_stock != 'Wheat_Chaff') and (quality_of_stock != 'Essential')):
    logging.debug(str(ticker) + " is not Wheat...skipping")
    continue

  # Initialize the dataframe
  projected_eps_analysis_df.loc[ticker, 'All_Projected_EPS_Positive'] = 0
  projected_eps_analysis_df.loc[ticker, 'Earnings_Reported'] = "1900-01-01"
  projected_eps_growth_rate_gt_10 = False
  projected_eps_growth_rate_gt_7_5 = False
  projected_eps_growth_rate_gt_5_0 = False
  projected_eps_growth_rate_gt_2_5 = False

  # ---------------------------------------------------------------------------
  # Read the Earnings file
  # ---------------------------------------------------------------------------
  earnings_file = ticker + "_earnings.csv"
  qtr_eps_df = pd.read_csv(dir_path + earnings_dir + "\\" + earnings_file)
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Read the Historical data file and check the date of the last date where the
  # historical data is available. If it is more than a month then it is time to
  # update historical data for the ticker
  # ---------------------------------------------------------------------------
  historical_df = pd.read_csv(dir_path + historical_dir + "\\" + ticker + "_historical.csv")
  date_str_list = historical_df.Date.tolist()
  date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in date_str_list]
  ticker_adj_close_list = historical_df.Adj_Close.tolist()
  ticker_curr_price = next(x for x in ticker_adj_close_list if not math.isnan(x))
  ticker_curr_date = date_list[ticker_adj_close_list.index(ticker_curr_price)]
  if (ticker_curr_date < one_month_ago_date):
    logging.debug("Historical Data was last updated on : " + str(ticker_curr_date) + ", more than a month ago")
    gt_1_month_old_historical_update_df.loc[ticker]= [ticker_curr_date]
  # ---------------------------------------------------------------------------


  # ---------------------------------------------------------------------------
  # Get the last earnings report date from Master Tracklist
  # if ((quality_of_stock == "Wheat") and pd.isnull(eps_actual_report_date)):
  # ---------------------------------------------------------------------------
  eps_actual_report_date = ""
  try:
    eps_actual_report_date = dt.datetime.strptime(str(master_tracklist_df.loc[ticker, 'Last_Earnings_Date']),'%Y-%m-%d %H:%M:%S').date()
  except:
    logging.error  ("**********************  ERROR ERROR ERROR ERROR ****************************")
    logging.error (str(ticker) + " is wheat and does not have a earnings date in the Master Tracklist file. Exiting....")
    logging.error("**********************  ERROR ERROR ERROR ERROR ****************************")
    sys.exit(1)
  eps_actual_report_date_dt = dt.datetime.strptime(str(eps_actual_report_date), '%Y-%m-%d').date()
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Get the earnings projected date from the earnings file
  # ---------------------------------------------------------------------------
  if 'Q_EPS_Projections_Date_0' in qtr_eps_df.columns:
    eps_projection_date_0 = qtr_eps_df['Q_EPS_Projections_Date_0'].tolist()[0]
    logging.debug ("Earnings file : " + str(earnings_file) + ", Projected EPS was last updated on " + str(eps_projection_date_0))
    eps_projection_date_0_dt = dt.datetime.strptime(str(eps_projection_date_0), '%m/%d/%Y').date()
  else:
    logging.error("Column Q_EPS_Projections_Date_0 DOES NOT exist in " + str(earnings_file))
    sys.exit(1)
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Check if the Last EPS Projections update date is older than a month or a qtr
  # ---------------------------------------------------------------------------
  date_year = eps_projection_date_0_dt.year
  # print ("The Year when EPS Projection was updated is : ", date_year)
  if (date_year < 2019):
    logging.error ("==========     Error : Seems like the projected EPS date is older than 2019. Please correct and rerun the script")
    sys.exit(1)

  if (eps_projection_date_0_dt < one_month_ago_date):
    logging.debug("Projected EPS were last updated on : " + str(eps_projection_date_0_dt) + ", more than a month ago")
    gt_1_month_old_eps_projections_df.loc[ticker]= [eps_projection_date_0_dt]

  if (eps_projection_date_0_dt < one_qtr_ago_date):
    logging.debug("Projected EPS were last updated on : " + str(eps_projection_date_0_dt) + ", more than a quarter ago")
    gt_1_qtr_old_eps_projections_df.loc[ticker]= [eps_projection_date_0_dt]
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Check if the eps report date is older than - say 80 days - This means that
  # the company is likely to report earnings soon
  # ---------------------------------------------------------------------------
  date_year = eps_actual_report_date_dt.year
  # print ("The Year of the last reported earnings is : ", date_year)
  if (date_year < 2019):
    print ("==========     Error : The date for ", ticker, " last earnings is older than 2019     ==========")
    sys.exit()
  if (today > (eps_actual_report_date_dt  + dt.timedelta(days=50))):
    logging.debug("Last Earnings Reported Date was : " +str(eps_actual_report_date_dt) + ", Maybe the company will report soon again")
    if (ticker not in ignore_qtr_eps_date_staleness_list):
      likely_earnings_date_df.loc[ticker] = [eps_actual_report_date_dt]
    else:
      logging.info("**********************  WARNING WARNING WARNING ****************************")
      logging.info("Found this ticker symbol in the ignore_qtr_eps_date_staleness_list and will IGNORE the date staleness")
      logging.info("of the last earnings report date. I am assuming that that list is upto date")
      logging.info("That YOU HAVE CHECKED FOR THE CORRECTNESS OF THE EARNINGS DATE (the company has actually NOT repored)")
      logging.info("and you just want to ignore them getting reported in the likely_earnings_date for now to ")
      logging.info("prevent clutter. Please remove the ticker from the ignore date as soon as the company reports earninga and")
      logging.info("the earnings data is updated in the Master Tracklist file")
      logging.info("**********************  WARNING WARNING WARNING ****************************")

  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Check if the last eps reported earnings date is later (newer) than when the
  # eps projection was updated in the earnings file
  # This means that the earnings projections was updated before the eps report date
  # and so the earnings file needs to be updated now with the eps projections
  if (eps_actual_report_date_dt > eps_projection_date_0_dt):
    logging.debug("EPS projections were updated on " + str(eps_projection_date_0_dt) + ", which is before the company reported Earnings : " + str(eps_actual_report_date_dt) + ". This is unusual...please fix immediately")
    eps_report_newer_tnan_eps_projection_df.loc[ticker] = [eps_actual_report_date_dt,eps_projection_date_0_dt]
  # ---------------------------------------------------------------------------



  # ---------------------------------------------------------------------------
  # Get the last quarter of reported earning to match in the earnings csv file
  # ---------------------------------------------------------------------------
  qtr_eps_date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in qtr_eps_df.Q_Date.tolist()]
  # Now get the date
  qtr_eps_date_list_eps_actual_report_date_match = min(qtr_eps_date_list, key=lambda d: abs(d - eps_actual_report_date))
  qtr_eps_date_list_eps_actual_report_date_index = qtr_eps_date_list.index(qtr_eps_date_list_eps_actual_report_date_match)
  logging.debug("Last Reported Earnings Date : " + str(eps_actual_report_date) + ", matches : " + str(qtr_eps_date_list_eps_actual_report_date_match) + ", in the earnings file df at index " + str(qtr_eps_date_list_eps_actual_report_date_index))
  # If the date match in the eps_date_list is a date in the future date (that can happen if
  # the eps_actual_report_date is more than 45 days after the quarter date. In this case we need to
  # move the match date index back by a quarter (by adding 1 to it - as the index starts
  # from 0 for the futuremost date)
  if ((qtr_eps_date_list_eps_actual_report_date_match >= dt.date.today()) or (qtr_eps_date_list_eps_actual_report_date_match >= eps_actual_report_date)):
    qtr_eps_date_list_eps_actual_report_date_index += 1
    qtr_eps_date_list_eps_actual_report_date_match = qtr_eps_date_list[qtr_eps_date_list_eps_actual_report_date_index]
    logging.debug("Since the match date was in the future, so getting the matching date from the immediate past")
    logging.debug("Last Reported Earnings Date : " + str(eps_actual_report_date) + ", matches : " + str(qtr_eps_date_list_eps_actual_report_date_match) + ", in the earnings file df at index " + str(qtr_eps_date_list_eps_actual_report_date_index))

  qtr_eps_actual_value = qtr_eps_df['Q_EPS_Diluted'].tolist()[qtr_eps_date_list_eps_actual_report_date_index]
  # Once we get the index of the last quarted report date, then get all the earnings
  # projections starting from 0 till that index. This gives all the future eps projections
  eps_projections_most_recent_list =   qtr_eps_df['Q_EPS_Diluted'].tolist()[0:qtr_eps_date_list_eps_actual_report_date_index]
  eps_projections_next_most_recent_list = qtr_eps_df['Q_EPS_Projections_1'].tolist()[0:qtr_eps_date_list_eps_actual_report_date_index]
  logging.debug ("The Most recent EPS Projections list is " + str(eps_projections_most_recent_list))
  logging.debug ("The Next Most recent EPS Projections list is " + str(eps_projections_next_most_recent_list))

  # Now process those numbers
  # 1. Find out if all the projections are positive
  # 2. Find out if the projections are increasing
  # 3. Find out the increase % of projections for each quarter
  no_of_eps_projections = len(eps_projections_most_recent_list)

  logging.info("Checking if ALL the Projected EPS are positive")
  eps_projections_most_recent_all_positive = 1
  for eps_projection_idx in range(no_of_eps_projections):
    logging.debug ("\tEPS Projections Index :" + str(eps_projection_idx) + ", Projected EPS : " + str(eps_projections_most_recent_list[eps_projection_idx]))
    eps_projection = eps_projections_most_recent_list[eps_projection_idx]
    if (eps_projection < 0):
      eps_projections_most_recent_all_positive = 0
  if (eps_projections_most_recent_all_positive == 1):
    logging.debug ("Good...All the EPS Projections are positive")
  else:
    logging.debug ("Not necessarity bad...could mean seasonality, but certainly not the very best company. All the projected EPS are not positive...")

  logging.info ("Comparing the Actual Last reported EPS with all the Projected EPS from most recent list to see if all(each) the Projected EPS's are greater then the last reported EPS")
  logging.debug ("Last Report Date : " + str(eps_actual_report_date) + " Matches with Quarter Date : " +str(qtr_eps_date_list_eps_actual_report_date_match) +  " and the EPS reported was : " + str(qtr_eps_actual_value))
  eps_projections_most_recent_all_gt_last_reported_eps = 1
  for eps_projection_idx in range(no_of_eps_projections):
    logging.debug("\tEPS Projections Index :" + str(eps_projection_idx) + ", Projected EPS : " + str(eps_projections_most_recent_list[eps_projection_idx]))
    eps_projection_x = eps_projections_most_recent_list[eps_projection_idx]
    if (eps_projection_x < qtr_eps_actual_value):
      eps_projections_most_recent_all_gt_last_reported_eps = 0
  if (eps_projections_most_recent_all_gt_last_reported_eps == 1):
    logging.debug ("Good...All the future Projected EPS from most recent updates are greater than the Most rencently reported Actual EPS")
  else:
    logging.debug ("Not necessarily bad...could mean seasonality. All the future Projected EPS most recent updates are NOT greater than the Most recently reported Actual EPS")

  logging.info ("Comparing the Projected EPS quarter by quarter successively to see if they are all increasing with each projected quarter")
  eps_projections_most_recent_all_increasing = 1
  for eps_projection_idx in range(no_of_eps_projections-1):
    logging.debug("\tEPS Projections Index :" + str(eps_projection_idx) + ", Projected EPS : " + str(eps_projections_most_recent_list[eps_projection_idx]))
    eps_projection_x = eps_projections_most_recent_list[eps_projection_idx]
    eps_projection_x_plus1 = eps_projections_most_recent_list[eps_projection_idx+1]
    if (eps_projection_x < eps_projection_x_plus1):
      eps_projections_most_recent_all_increasing = 0
  if (eps_projections_most_recent_all_increasing == 1):
    logging.debug ("Good...All the future EPS Projections from most recent updates are increasing")
  else:
    logging.debug ("Not necessarily bad...could mean seasonality. All the future EPS Projections from most recent updates are NOT increasing")

  # 1. if everything is looking good then find the growth rate of the projected EPS
  # 2. Maybe also then find out if the ticker is below the channel or not - That can be calculated independently though...
  # 3. Find out how to compare the most recent Projected Earnings with the second to last time they were updated....
  #   if (eps_projections_most_recent_all_positive == 1):

  # if the projected earnings are all positive and are increasing then calculate the growth rate
  projected_eps_growth_rate_list = []
  for i in range(no_of_eps_projections-1):
    projected_eps_growth_rate_list.append(float('nan'))

  if (eps_projections_most_recent_all_positive == 1) and (eps_projections_most_recent_all_increasing == 1):
    logging.info("Checking the growth rate of projected earnings. Will have to start in reverse to get the math right")
    for eps_projection_idx in reversed(range(0,no_of_eps_projections)):
      # logging.debug("\tEPS Projections Index : " + str(eps_projection_idx) + ", Projected EPS : " + str(eps_projections_most_recent_list[eps_projection_idx]))
      if (eps_projection_idx == 0):
        continue
      eps_projection_x = eps_projections_most_recent_list[eps_projection_idx]
      eps_projection_x_minus1 = eps_projections_most_recent_list[eps_projection_idx-1]
      projected_eps_growth_rate = float((eps_projection_x_minus1 - eps_projection_x)/eps_projection_x)*100
      logging.debug("\tEPS Projections Index : " + str(eps_projection_idx) + ", Next EPS Projections Index : " + str(eps_projection_idx-1) +
                    ", Projected EPS : " + str(eps_projection_x) + ", Next Projected EPS : " + str(eps_projection_x_minus1) +
                    ", Growth Rate : " + str(projected_eps_growth_rate))
      projected_eps_growth_rate_list[eps_projection_idx-1] = projected_eps_growth_rate


    projected_eps_growth_rate_gt_10 = check_list_elements_with_val(projected_eps_growth_rate_list, 10)
    projected_eps_growth_rate_gt_7_5 = check_list_elements_with_val(projected_eps_growth_rate_list, 7.5)
    projected_eps_growth_rate_gt_5_0 = check_list_elements_with_val(projected_eps_growth_rate_list, 5)
    projected_eps_growth_rate_gt_2_5 = check_list_elements_with_val(projected_eps_growth_rate_list, 2.5)
    if (projected_eps_growth_rate_gt_10):
      logging.debug("Projected EPS is growing at greater than 10% per quarter - compounded")
    elif (projected_eps_growth_rate_gt_7_5):
      logging.debug("Projected EPS is growing at greater than 7.5% per quarter - compounded")
    elif (projected_eps_growth_rate_gt_5_0):
      logging.debug("Projected EPS is growing at greater than 5% per quarter - compounded")
    elif (projected_eps_growth_rate_gt_2_5):
      logging.debug("Projected EPS is growing at greater than 2.5% per quarter - compounded")
    else:
      logging.debug("Projected EPS is growing at slower than 2.5% per quarter - compounded")


  projected_eps_analysis_df.loc[ticker, 'All_Projected_EPS_Positive'] = eps_projections_most_recent_all_positive
  projected_eps_analysis_df.loc[ticker, 'Earnings_Reported'] = eps_actual_report_date
  projected_eps_analysis_df.loc[ticker, 'EPS_2.5%'] = projected_eps_growth_rate_gt_2_5
  projected_eps_analysis_df.loc[ticker, 'EPS_5%'] = projected_eps_growth_rate_gt_5_0
  projected_eps_analysis_df.loc[ticker, 'EPS_7.5%'] = projected_eps_growth_rate_gt_7_5
  projected_eps_analysis_df.loc[ticker, 'EPS_10%'] = projected_eps_growth_rate_gt_10

  logging.debug("================================")
  logging.info("")
  # ---------------------------------------------------------------------------

logging.info("")
logging.info("********************")
logging.info("***** All Done *****")
logging.info("********************")


# -----------------------------------------------------------------------------
# Print all the df to their respective files
# -----------------------------------------------------------------------------
gt_1_month_old_eps_projections_df.sort_values(by='Date').to_csv(dir_path + log_dir + "\\" + 'gt_1_month_old_eps_projections.txt',sep=' ', index=True, header=False)
gt_1_qtr_old_eps_projections_df.sort_values(by='Date').to_csv(dir_path + log_dir + "\\" + 'gt_1_qtr_old_eps_projections_df.txt',sep=' ', index=True, header=False)
likely_earnings_date_df.sort_values(by='Date').to_csv(dir_path + log_dir + "\\" + 'likely_earnings_date.txt',sep=' ', index=True, header=False)
eps_report_newer_than_eps_projection_df.sort_values(by='Earnings_Reported').to_csv(dir_path + log_dir + "\\" + 'report_newer_than_earnings.txt',sep=' ', index=True, header=False)
projected_eps_analysis_df.sort_values(by='Ticker').to_csv(dir_path + log_dir + "\\" + 'projected_eps_analysis.csv', index=True, header=True)
gt_1_month_old_historical_update_df.sort_values(by='Date').to_csv(dir_path + log_dir + "\\" + 'gt_1_month_historica_update.txt',sep=' ', index=True, header=False)
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

