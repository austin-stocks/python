

import csv
import openpyxl
import os
import xlrd
import sys
import time
import logging
import pandas as pd
import datetime as dt
from yahoofinancials import YahooFinancials
from termcolor import colored, cprint

# 6/30/2019 - This scripte works as inteneded but get thrown off when there are Yahoo and CNBC projections for the
#  same date - an example is AAP - look at date 4/21/2017 this has Yahoo and CNBC data (In my opinion incorrectly
# as Yahoo date is not the same row as the earnings is). Anyway because of the way the script is written it will
# put the Yahoo date in the previous projections as all the rows what have nan in projection are deleted before
# the processing so currently the scirpt has not way of knowing whether the Yahoo data is for the previous quater
# or for the current quater. This shows up in the Earnings.csv file for AAP
# One solution is to delted all the rows that have Yahoo is the column immpediately following projection column
# that way we will lose that data but that should not be a big deal

dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
log_dir = "\\..\\..\\..\\Automation_Not_in_Git\\" + "Logs"
stock_files_dir = "..\..\..\Automation_Not_in_Git\\" + "Stock_Files"
yesterday_dt = dt.datetime.now() - dt.timedelta(days=1)
yesterday_str = yesterday_dt.strftime("%m/%d/%Y")

tracklist_df = pd.read_csv(dir_path + user_dir + "\\" + 'Tracklist.csv')
ticker_list_unclean = tracklist_df['Tickers'].tolist()
ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']


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
                    filename=dir_path + log_dir + "\\" + 'SC_Extract_Earnings_debug.txt',
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


logging.debug ("The current directory is " + str(dir_path))
for ticker_raw in ticker_list:
  ticker = ticker_raw.replace(" ", "").upper()  # Remove all spaces from ticker_raw and convert to uppercase
  logging.info("Getting Earnings for " + str(ticker))

  earnings_df = pd.read_excel(stock_files_dir + '\\' + ticker + '.xlsm', sheet_name='historical')

  logging.debug ("\n\nThe Unadultrated Historical Tab (which contains earnings data) from the stock file is \n\n" + earnings_df.to_string())
  logging.debug ("\n\nThe columns in the historical tab are :\n")
  for col in earnings_df.columns:
    logging.debug(str(col))

  # For some reason python reads the Date column as Timestamp
  # Convert it to string here We will convet it to Datetime later
  date_list = earnings_df['Date'].astype(str).tolist()
  qtr_eps_list = earnings_df['Q EPS'].tolist()
  projected_eps_list = earnings_df['projection'].tolist()
  logging.debug ("\nThe Raw Date list is :"+ str(date_list))

  # This works : The create a dataframe from a list of lists
  step1_df=pd.DataFrame(list(zip(date_list, qtr_eps_list, projected_eps_list)),
                        columns=['Date','Q EPS', 'projection'])
  logging.debug ("\nDataframe that only has Date, Q EPS and projection columns \n" + step1_df.to_string())
  # ===========================================================================
  # Clean up the dataframe
  # ===========================================================================
  # Remove all rows that do not have data in ALL columns
  step1_df.dropna(how='all',inplace=True)
  # Remove all rows that do not have data in Date column
  logging.debug ("\nNow going to remove the dataframe rows that don't have dates")
  step1_df.dropna(subset=['Date'],inplace=True)
  tmp_df = step1_df[step1_df.Date != 'NaT']
  step1_df = tmp_df
  logging.debug ("\nDataframe after dropping all rows with null in Date column\n" + step1_df.to_string())
  # Now we should have a dataframe that does not have any rows that do not have a valid date

  # Drop ONLY the rows now that do not have any data in Q EPS AND projection column
  logging.debug ("\nNow going to remove the dataframe rows that don't have Q EPS AND Projections")
  step1_df.dropna(subset=['Q EPS', 'projection'], how='all', inplace=True)
  logging.debug ("\nDataframe after dropping all the rows with null in (Q EPS AND projection BOTH) columns\n" +step1_df.to_string())
  # ===========================================================================

  # ===========================================================================
  # Now we should have a dataframe like this...
  # ===========================================================================
  # Now we should have a dataframe like this -
  # Every row should have a date
  # NOT Every row will have Q EPS 
  # Every row should have a projected EPS
  # Not every row will have Q eps because there are (almost always) multiple projectinos for each eap and the original 
  # stocfile (Ann xlsm) has them vertical. So for e.g in this case for 2020-12-31 the actual/last updated earnings
  #  is 1.58 but the projection when they have been updated in the past are in col 3 1.58, 1.59, 1.58, 1.57, 1.58, 1.68 and so on... 
  '''  
         Date         Q_EPS      Projection
  1     2020-12-31  1.580000    1.580000
  2     2020-12-30       NaN    1.590000
  3     2020-12-29       NaN    1.580000
  4     2020-12-28       NaN    1.570000
  5     2020-12-24       NaN    1.580000
  6     2020-12-23       NaN    1.680000
  7     2020-12-22       NaN    1.740000
  8     2020-12-21       NaN    1.730000
  9     2020-12-18       NaN    1.750000
  10    2020-12-17       NaN    1.820000
  11    2020-12-16       NaN    1.830000
  12    2020-12-15       NaN    1.820000
  13    2020-12-14       NaN    1.810000
  14    2020-12-11       NaN    1.820000
  15    2020-12-10       NaN    1.810000
  16    2020-12-09       NaN    1.864186
  17    2020-12-08       NaN    1.920422
  18    2020-12-07       NaN    1.932654
  19    2020-12-04       NaN    1.969350
  ...
  ...
  ... Previous Quarter date rolls around
  ...
  65    2020-09-30  1.610000    1.610000
  66    2020-09-29       NaN    1.600000
  '''
  logging.debug ("\nNow we have a dataframe in which : \nEvery row should have a date.\nNot every row will have Q eps.\nEvery row should have a projected EPS")

  # ---------------------------------------------------------------------------
  # Extract the lists and write csv file (Read the above comment about the
  # dataframe carefully - this will help in understanding the code below
  # (Also go through the debug file to for good logical flow of how the dataframe
  # is printed row by row in the csv file
  # ---------------------------------------------------------------------------
  csvFile=open("..\..\..\Automation_Not_in_Git" + '\\' + "Extracted_Earnings" + '\\' + ticker + "_earnings.csv", 'w+', newline='')
  writer = csv.writer(csvFile, delimiter=',')
  # Put the Header Row in the csv
  csv_header_row_list = ["CNBC_Matches_Reported_EPS","Q_Report_Date", "Q_Date", "Q_EPS_Diluted","Q_EPS_Adjusted","Q_EPS_Projections_Date_0","Q_EPS_Projections_1","Q_EPS_Projections_Date_1","Q_EPS_Projections_2","Q_EPS_Projections_Date_2","Q_EPS_Projections_2","Q_EPS_Projections_Date_2"]
  writer.writerow(csv_header_row_list)

  step1_date_list = [dt.datetime.strptime(date, '%Y-%m-%d').date() for date in step1_df.Date.tolist()]
  # step1_date_list = [dt.datetime.strptime(date, '%Y-%m-%d %H:%M:%S').date() for date in step1_df.Date.tolist()]
  step1_eps_list = step1_df['Q EPS'].tolist()
  step1_projected_eps_list = step1_df['projection'].tolist()

  # Get the positions of various fields from the header_row_list
  # The positions will be used later to fill the dates/EPS reported/EPS projected numbers/strings
  # in the approprite column
  cnbc_matches_pos = csv_header_row_list.index("CNBC_Matches_Reported_EPS")
  q_report_date_pos = csv_header_row_list.index("Q_Report_Date")
  q_date_pos = csv_header_row_list.index("Q_Date")
  q_eps_diluted_pos = csv_header_row_list.index("Q_EPS_Diluted")
  q_eps_adjusted_pos = csv_header_row_list.index("Q_EPS_Adjusted")
  q_eps_projections_date_0_pos = csv_header_row_list.index("Q_EPS_Projections_Date_0")
  q_eps_projections_1_pos = csv_header_row_list.index("Q_EPS_Projections_1")
  # logging.debug("The position for Q_EPS_Adjusted : " + str(q_eps_adjusted_pos))
  # logging.debug("The position for Q_EPS_Projections_Date_0 : " + str(q_eps_projections_date_0_pos))

  logging.debug ("\nWill now go row by row over the dataframe...Remember that one row generally will have multiple projections")
  row_number = 0
  csv_line = []
  for x in step1_date_list:
    step1_eps = step1_eps_list[row_number]
    step1_projected_eps = step1_projected_eps_list[row_number]
    logging.debug ("")
    logging.debug ("Row Number : " + str(row_number) +  ", Date is : " + str(x) + ", Q EPS is : " + str(step1_eps) + ", Projected EPS is : " + str(step1_projected_eps))

    # -----------------------------------------------------
    # This is the row that has the Q_EPS non-nan, which means
    # that this is the first row for a new quarter...so start
    # writing a fresh csv_line inside this if statement
    # -----------------------------------------------------
    if (str(step1_eps) != 'nan'):
      logging.debug ("")
      logging.debug ("Row " + str(row_number) + " : has both Q EPS and projections. This means that this row is the 1st instance of Q EPS...")
      logging.debug ("Row " + str(row_number) + " : All subsequent rows till we hit another row like this row will ONLY have projections")

      if (row_number > 0):
        logging.debug("Since the row number is gt 0 which means that we already processed atleast one iteration of going throught Q EPS and Projections...")
        logging.debug("so it is time to print into earnings file")
        logging.debug("Printing " + str(csv_line))
        writer.writerow(csv_line)

      # this is needed to be initialized to 200 (it can be anything) elements so that
      # the positional insertion can work properly
      csv_line = []
      for i_int in range(200):
        csv_line.append("")

      csv_line[q_date_pos] = x.strftime('%m/%d/%Y')
      csv_line[q_eps_diluted_pos] = step1_eps
      if (row_number == 0):
        csv_line[cnbc_matches_pos] =  "N"
        csv_line[q_eps_projections_date_0_pos] = yesterday_str
      else:
        csv_line[cnbc_matches_pos] = ""
        csv_line[q_eps_projections_date_0_pos] = ""

      csv_line[q_eps_adjusted_pos] = ""
      csv_line[q_report_date_pos] = ""
      csv_line[q_eps_projections_1_pos] = step1_projected_eps
      insert_index = q_eps_projections_1_pos+1
      logging.debug ("CSV Line after processing the row that had reported EPS :\n " + str(csv_line))

    # -----------------------------------------------------
    # We are processing the row in the dataframe that has
    # the Q_EPS = nan, which means that this is the row
    # that just has the EPS projection...
    # That means that the csv_line has already been started and
    # we just need to add (concatenate) to the cav_line until
    # we come across a row_number that has the Q_EPS = not nan
    # in the df and then write the entire csv_line in the
    # csv file (that happens in the if statement above
    # -----------------------------------------------------
    else:
      logging.debug ("Row " + str(row_number) + " : This is a row where only projections are present")
      logging.debug ("Row " + str(row_number) + " : So this row will only write to Q_EPS_Projections_x column")
      csv_line[insert_index] = ""
      csv_line[insert_index+1] = step1_projected_eps
      insert_index = insert_index+2
      logging.debug("CSV Line after processing the row that only had projected EPS :\n" + str(csv_line))

    row_number = row_number+1

print ("ALL Done")
csvFile.close()
