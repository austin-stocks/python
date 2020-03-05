import pandas as pd
import os
import sys
import time
import datetime as dt
import numpy as np
import logging
import math
from dateutil.relativedelta import relativedelta


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
configuration_file = "Configurations.csv"
master_tracklist_df = pd.read_excel(dir_path + user_dir + "\\" + master_tracklist_file, sheet_name="Main")
config_df = pd.read_csv(dir_path + user_dir + "\\" + configuration_file)
config_df.set_index('Ticker', inplace=True)
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
                    filename=dir_path + log_dir + "\\" + 'SC_SpotCheck_Earning_files_debug.txt',
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

update_with_aaii_projections = 1
if (update_with_aaii_projections == 1):
  aaii_analysts_projection_file = "AAII_Analysts.csv"
  aaii_analysts_projection_df = pd.read_csv(dir_path + user_dir + "\\" + aaii_analysts_projection_file)
  logging.debug("The AAII Analysts Projection df is " + aaii_analysts_projection_df.to_string())
  aaii_analysts_projection_df.set_index('Ticker', inplace=True)




# -----------------------------------------------------------------------------
# Declare all the dataframes that we are going to need to write into txt file
# and set their columns
# -----------------------------------------------------------------------------
ignore_qtr_eps_date_staleness_list = [
'CBOE','CP','GOOG','RACE'
]

today = dt.date.today()
one_qtr_ago_date = today - dt.timedelta(days=80)
one_month_ago_date = today - dt.timedelta(days=15)
logging.info("Today : " + str(today) +  " One month ago : " +str(one_month_ago_date) + " One qtr ago : " +str(one_qtr_ago_date))

projected_eps_analysis_df = pd.DataFrame(columns=['Ticker','All_Projected_EPS_Positive','EPS_2.5%','EPS_5%','EPS_7.5%','EPS_10%','Earnings_Reported', 'Earnings_Projections_Updated_0', 'Earnings_Projections_Updated_1', 'Days_between_esp_projections_were_updated', 'Direction_of_latest_eps_projection', 'Direction_of_comparison_between_two_eps_projections'])
projected_eps_analysis_df.set_index('Ticker', inplace=True)
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Loop through all the tickers to check the dates when
# -----------------------------------------------------------------------------
# ticker_list = ['AUDC','MED']
for ticker_raw in ticker_list:
  ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase
  logging.debug("================================")
  logging.info("Processing : " + str(ticker))
  # if ticker in ["CCI", , "CY", "EXPE", "FLS", "GCBC","GOOG","HURC","KMI","KMX","PNFP","QQQ","RCMT","TMO","TMUS","TTWO",,"WLTW"]:
  if ticker in ["QQQ"]:
    logging.info("File for " + str(ticker) +  " does not exist in earnings directory. Skipping...")
    continue
  quality_of_stock = master_tracklist_df.loc[ticker, 'Quality_of_Stock']
  if ((quality_of_stock != 'Wheat') and (quality_of_stock != 'Wheat_Chaff') and (quality_of_stock != 'Essential')):
    logging.debug(str(ticker) + " is not Wheat...skipping")
    continue
  if ticker in ignore_qtr_eps_date_staleness_list:
    logging.info(str(ticker) + " is in ignore list...skipping")
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
  logging.debug("The earnings datafaram is " + qtr_eps_df.to_string())
  # ---------------------------------------------------------------------------


  ticker_config_series = config_df.loc[ticker]
  if (str(ticker_config_series['Fiscal_Year']) != 'nan'):
    fiscal_yr_str = str(ticker_config_series['Fiscal_Year'])
    if not (all(x.isalpha() for x in fiscal_yr_str)):
      print("**********                                           ERROR                                       **********")
      print("**********     Entry for ", str(ticker).center(10), " 'Fiscal_Year' in the configurations file  is", fiscal_yr_str,"   **********")
      print("**********     It is not a 3 character month. Valid values(string) are:     **********")
      print("**********     Valid values [Jan, Feb, Mar,...,Nov, Dec]                                         **********")
      print("**********     Please correct and then run the script again                                      **********")
  else:
    fiscal_yr_str = "Dec"

  fiscal_qtr_str  = "BQ-"+fiscal_yr_str
  fiscal_yr_str = "BA-"+fiscal_yr_str
  logging.debug("The fiscal Year is " + str(fiscal_yr_str))



  if (update_with_aaii_projections == 1):
    # -------------------------------------------------------------------------
    # Find the fiscal years y0, y1 and y2 and their respective projections
    # -------------------------------------------------------------------------
    ticker_aaii_analysts_projection_series = aaii_analysts_projection_df.loc[ticker]
    logging.debug("The series for " + str(ticker) + " in the AAII Analysts df is " + str(ticker_aaii_analysts_projection_series))
    y_plus0_fiscal_year_end = ticker_aaii_analysts_projection_series['Date--Current fiscal year']
    if (str(y_plus0_fiscal_year_end) != 'nan'):
      y_plus0_fiscal_year_dt = dt.datetime.strptime(str(y_plus0_fiscal_year_end), '%m/%d/%Y').date()
    else:
      logging.debug("The y0 fiscal year end for " + str(ticker) + " is NaN in AAII Analysts df...Skippig")
      continue

    y_plus1_fiscal_year_dt = y_plus0_fiscal_year_dt + relativedelta(years=1)
    y_plus2_fiscal_year_dt = y_plus0_fiscal_year_dt + relativedelta(years=2)
    logging.debug("Y0 Fiscal Year for  " + str(ticker) + " ends on " + str(y_plus0_fiscal_year_end))
    logging.debug("Y1 Fiscal Year for  " + str(ticker) + " ends on " + str(y_plus1_fiscal_year_dt))
    logging.debug("Y2 Fiscal Year for  " + str(ticker) + " ends on " + str(y_plus2_fiscal_year_dt))
    y_plus0_fiscal_year_eps_projections = ticker_aaii_analysts_projection_series['EPS Est Y0']
    y_plus1_fiscal_year_eps_projections = ticker_aaii_analysts_projection_series['EPS Est Y1']
    y_plus2_fiscal_year_eps_projections = ticker_aaii_analysts_projection_series['EPS Est Y2']
    logging.debug("Y0 eps projections are " + str(y_plus0_fiscal_year_eps_projections))
    logging.debug("Y1 eps projections are " + str(y_plus1_fiscal_year_eps_projections))
    logging.debug("Y2 eps projections are " + str(y_plus2_fiscal_year_eps_projections))
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Now tht we have dates from AAII fiscal years compare it against the latest
    # date that is in the earnings file and find the number of year/quarters than
    # need to be inserted
    # -------------------------------------------------------------------------
    latest_qtr_date_in_earnings_file = qtr_eps_df['Q_Date'].tolist()[0]
    logging.debug("The latest Date in Earnings file is " + str(latest_qtr_date_in_earnings_file))
    latest_qtr_date_in_earnings_file_dt = dt.datetime.strptime(str(latest_qtr_date_in_earnings_file), '%m/%d/%Y').date()
    qtr_eps_list = qtr_eps_df.Q_EPS_Diluted.tolist()
    no_of_year_to_insert_eps_projections = 0
    # if (latest_qtr_date_in_earnings_file_dt == y_plus0_fiscal_year_dt):
    if ((y_plus2_fiscal_year_dt-latest_qtr_date_in_earnings_file_dt).days <=5):
      logging.debug(str(ticker) + " : The date for the Latest entry in the Earnings file: " + str(latest_qtr_date_in_earnings_file_dt) + " matches Y2 fiscal end date : " + str(y_plus2_fiscal_year_dt) + " ...so nothing needs to be inserted")
      logging.wanring(str(ticker) + " : Hmmm...However this should very rare...make sure for " + str(ticker) + "that the latest entry qtr_eps_date and the Y2 fiscal year dates actually match...")
    elif ((y_plus1_fiscal_year_dt -latest_qtr_date_in_earnings_file_dt).days <= 5):
      logging.debug(str(ticker) + " : The date for the Latest entry in the Earnings file: " + str(latest_qtr_date_in_earnings_file_dt) + " matches Y1 fiscal end date : " + str(y_plus1_fiscal_year_dt) + " ...so we can possibly add Y2 fiscal year projections")
      logging.debug("Checking if Y2 fiscal year eps projections are NOT nan")
      if ((str(y_plus0_fiscal_year_eps_projections) != 'nan') and (str(y_plus2_fiscal_year_eps_projections) != 'nan')):
        logging.debug(str(ticker) + " : Y2 fiscal year eps projections are NOT nan. So, will insert one year (Y2)")
        no_of_year_to_insert_eps_projections = 1
        fiscal_qtr_and_yr_dates_raw = pd.date_range(latest_qtr_date_in_earnings_file_dt, y_plus2_fiscal_year_dt,freq=fiscal_qtr_str)
      else:
        logging.debug(str(ticker) + " : Hmmm...it seems like Y2 eps projections are nan in AAII. Nothing inserted...This is unusual....Please check Y2 earnings projections in AAII nan")
    elif ((y_plus0_fiscal_year_dt-latest_qtr_date_in_earnings_file_dt).days <= 5):
      logging.debug(str(ticker) + " : The date for the Latest entry in the Earnings file: " + str(latest_qtr_date_in_earnings_file_dt) + " matches Y0 fiscal end date : " + str(y_plus0_fiscal_year_dt) + " ...so we can possibly add Y1 and Y2 fiscal year projections")
      logging.debug("So we can possibly add Y1 and Y2 fiscal year projections")
      logging.debug("Checking if both Y1 and Y2 fiscal year eps projections are NOT nan")
      if ((str(y_plus0_fiscal_year_eps_projections) != 'nan') and (str(y_plus1_fiscal_year_eps_projections) != 'nan') and (str(y_plus2_fiscal_year_eps_projections) != 'nan')):
        logging.debug (str(ticker) + " : Both Y1 and Y2 fiscal year eps projections are NOT nan. So, will insert two years (Y1 and Y2)")
        no_of_year_to_insert_eps_projections = 2
        fiscal_qtr_and_yr_dates_raw = pd.date_range(latest_qtr_date_in_earnings_file_dt, y_plus2_fiscal_year_dt,freq=fiscal_qtr_str)
      elif ( (str(y_plus0_fiscal_year_eps_projections) != 'nan') and (str(y_plus1_fiscal_year_eps_projections) != 'nan')):
        logging.debug("We will NOT insert for Y2 (as its eps projection is nan)")
        logging.debug(str(ticker) + " : Only Y1 fiscal year eps projections is NOT nan. So, will insert one year (Y1)")
        no_of_year_to_insert_eps_projections = 1
        fiscal_qtr_and_yr_dates_raw = pd.date_range(latest_qtr_date_in_earnings_file_dt, y_plus1_fiscal_year_dt,freq=fiscal_qtr_str)
      else:
        logging.debug(str(ticker) + " : Hmmm...it seems like both Y1 and Y2 eps projections are nan in AAII. Nothing inserted...This is unusual....Please check Y1 and Y2 earnings projections in AAII nan")
    else:
      logging.error("The date corresponding to the Latest entry in the Earnings file : " + str(latest_qtr_date_in_earnings_file_dt))
      logging.error("neither matches the Y0 fiscal year end from AAII file : " + str(y_plus0_fiscal_year_dt))
      logging.error("nor matches the Y1 fiscal year end from AAII file : " + str(y_plus1_fiscal_year_dt))
      logging.error("nor matches the Y2 fiscal year end from AAII file : " + str(y_plus2_fiscal_year_dt))
      sys.exit(1)

    fiscal_qtr_dates = []
    for x in fiscal_qtr_and_yr_dates_raw:
      fiscal_qtr_dates.append(x.date().strftime('%m/%d/%Y'))

    if (len(fiscal_qtr_dates) != 4) and (len(fiscal_qtr_dates) != 8):
      del fiscal_qtr_dates[0]
    logging.debug("The original qtr dates list is\n" + str(fiscal_qtr_and_yr_dates_raw))
    logging.debug("The modified qtr dates list is\n" + str(fiscal_qtr_dates))
    # -------------------------------------------------------------------------


    # -------------------------------------------------------------------------
    # Now that we have the number of years to insert, calcuate the projected
    # eps per quarter for future years - and insert in the dataframe
    # -------------------------------------------------------------------------
    if (no_of_year_to_insert_eps_projections > 0):
      logging.debug("The qtr eps list is " + str(qtr_eps_list))
      no_of_qtr_to_insert = no_of_year_to_insert_eps_projections*4
      tmp_eps = []
      for i_int in range(no_of_qtr_to_insert):
        tmp_eps.append(float('nan'))
      if (no_of_year_to_insert_eps_projections == 1):
        if (latest_qtr_date_in_earnings_file_dt == y_plus0_fiscal_year_dt):
          growth_factor = y_plus1_fiscal_year_eps_projections/y_plus0_fiscal_year_eps_projections
          logging.debug("Inserting one year of EPS projections with the growth factor for y_plus1 over y_plus0 : " + str(growth_factor))
        else:
          growth_factor = y_plus2_fiscal_year_eps_projections/y_plus1_fiscal_year_eps_projections
          logging.debug("Inserting one year of EPS projections with the growth factor for y_plus2 over y_plus1 : " + str(growth_factor))
        for i_int in range(no_of_qtr_to_insert):
          tmp_eps[i_int] = qtr_eps_list[3 - i_int]*growth_factor
          logging.debug("Inserting in tmp_eps list at index : " + str(i_int) + " Qtr eps : " + str(qtr_eps_list[3 - i_int]) + " Projected Calcuated EPS with grwoth factor : " + str(tmp_eps[i_int]))
      else:
        growth_factor = y_plus1_fiscal_year_eps_projections / y_plus0_fiscal_year_eps_projections
        logging.debug("Inserting two years of EPS projections - Inserting first year with the growth factor for y_plus1 over y_plus0 : " + str(growth_factor))
        for i_int in range(0,4):
          tmp_eps[i_int] = qtr_eps_list[3 - i_int] * growth_factor
          logging.debug("Inserting in tmp_eps list at index : " + str(i_int) + " Qtr eps : " + str(qtr_eps_list[3 - i_int]) + " Projected Calcuated EPS with grwoth factor : " + str(tmp_eps[i_int]))
        growth_factor = y_plus2_fiscal_year_eps_projections / y_plus1_fiscal_year_eps_projections
        logging.debug("Inserting two years of EPS projections - Inserting second year with the growth factor for y_plus2 over y_plus1 : " + str(growth_factor))
        for i_int in range(4,8):
          tmp_eps[i_int] = tmp_eps[i_int-4] * growth_factor
          logging.debug("Inserting in tmp_eps list at index : " + str(i_int) + " Qtr eps : " + str(tmp_eps[i_int-4]) + " Projected Calcuated EPS with grwoth factor : " + str(tmp_eps[i_int]))

      logging.debug("The tmp_eps list of projected eps to be inserted " + str(tmp_eps))
      for i_int in range(no_of_qtr_to_insert):
        logging.debug ("Inserting in qtr_eps_df at index : " + str(-(i_int+1)) + " Q_Date : " + str( fiscal_qtr_dates[i_int]) + " Q_EPS_Diluted : " + str(tmp_eps[i_int]))
        qtr_eps_df.loc[-(i_int+1)]= qtr_eps_df.loc[0]
        # qtr_eps_df.loc[-(i_int+1), 'Q_Date'] =  dt.datetime.strptime(fiscal_qtr_dates[i_int], '%m/%d/%Y').date()
        qtr_eps_df.loc[-(i_int+1), 'Q_Date'] =  fiscal_qtr_dates[i_int]
        qtr_eps_df.loc[-(i_int+1), 'Q_EPS_Diluted'] = tmp_eps[i_int]

    # -------------------------------------------------------------------------


  # qtr_eps_df_tmp = qtr_epq_df
  # qtr_eps_df.set_index('Q_Date', inplace=True)
  # qtr_eps_df['Q_Date'] = pd.to_datetime(qtr_eps_df['Q_Date'], format="%m/%d/%Y")
  qtr_eps_df['Q_Date'] = qtr_eps_df['Q_Date'].astype('datetime64[D]', format="%m/%d/%Y")
  qtr_eps_df.sort_values('Q_Date', inplace=True, ascending=False)
  qtr_eps_df.reset_index(inplace=True, drop=True)
  qtr_eps_df['Q_Date'] = pd.to_datetime(qtr_eps_df['Q_Date']).dt.strftime('%m/%d/%Y')

  logging.debug("The earnings datafaram after adding earning projection is " + qtr_eps_df.to_string())


  # sys.exit(1)
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
    logging.debug ("Projected EPS was last updated on " + str(eps_projection_date_0) + " as per Earnings file")
    eps_projection_date_0_dt = dt.datetime.strptime(str(eps_projection_date_0), '%m/%d/%Y').date()
  else:
    logging.error("Column Q_EPS_Projections_Date_0 DOES NOT exist in " + str(earnings_file))
    sys.exit(1)

  if 'Q_EPS_Projections_Date_1' in qtr_eps_df.columns:
    eps_projection_date_1 = qtr_eps_df['Q_EPS_Projections_Date_1'].tolist()[0]
    if (not pd.isnull(eps_projection_date_1)):
      eps_projection_date_1_dt = dt.datetime.strptime(str(eps_projection_date_1), '%m/%d/%Y').date()
      logging.debug("Projected EPS was last but second updated on " + str(eps_projection_date_1) + " as per earnings file")
    else:
      logging.error("Column Q_EPS_Projections_Date_1 DOES NOT exist in " + str(earnings_file))

  date_year = eps_projection_date_0_dt.year
  # print ("The Year when EPS Projection was updated is : ", date_year)
  if (date_year < 2019):
    logging.error ("==========     Error : Seems like the projected EPS date is older than 2019. Please correct and rerun the script")
    sys.exit(1)
  if (eps_projection_date_0_dt >  dt.date.today()):
    logging.error("It seems that Earnings projections date :  " + str(eps_projection_date_0_dt) + " is in future")
    logging.error("It is probably a typo as how can you have updated the earnings projection on a future date :-). Please correct and rerun")
    sys.exit(1)
  if (eps_projection_date_1_dt >  dt.date.today()):
    logging.error("It seems that Earnings projections date (2nd from last) :  " + str(eps_projection_date_1_dt) + " is in future")
    logging.error("It is probably a typo as how can you have updated the earnings projection on a future date :-). Please correct and rerun")
    sys.exit(1)
  if (eps_projection_date_0_dt <  eps_projection_date_1_dt):
    logging.error("It seems that Earnings projections update date :  " + str(eps_projection_date_0_dt) + " is older than the")
    logging.error("earnings update for 2nd to last date : " + str(eps_projection_date_1_dt))
    logging.error("It is probably a typo as how can you have updated the earnings projection on a day that is older")
    logging.error("than when you updated the 2nd to last earnings projections :-). Please correct and rerun")
    sys.exit(1)
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Check if the eps report date is older than - say 80 days - This means that
  # the company is likely to report earnings soon
  # ---------------------------------------------------------------------------
  date_year = eps_actual_report_date_dt.year
  # print ("The Year of the last reported earnings is : ", date_year)
  if (date_year < 2019):
    loggig.error("==========     Error : The date for " + str(ticker) + " last earnings is older than 2019     ==========")
    sys.exit()
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
projected_eps_analysis_df.sort_values(by='Ticker').to_csv(dir_path + log_dir + "\\" + 'projected_eps_analysis.csv', index=True, header=True)
# -----------------------------------------------------------------------------







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

