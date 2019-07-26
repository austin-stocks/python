

import csv
import openpyxl
import os
import xlrd
import sys
import time
import pandas as pd
import datetime as dt
from yahoofinancials import YahooFinancials
from termcolor import colored, cprint

dir_path = os.getcwd()


# 6/30/2019 - This scripte works as inteneded but get thrown off when there are Yahoo and CNBC projections for the
#  same date - an example is AAP - look at date 4/21/2017 this has Yahoo and CNBC data (In my opinion incorrectly
# as Yahoo date is not the same row as the earnings is). Anyway because of the way the script is written it will
# put the Yahoo date in the previous projections as all the rows what have nan in projection are deleted before
# the processing so currently the scirpt has not way of knowing whether the Yahoo data is for the previous quater
# or for the current quater. This shows up in the Earnings.csv file for AAP
# One solution is to delted all the rows that have Yahoo is the column immpediately following projection column
# that way we will lose that data but that should not be a big deal

tracklist_df = pd.read_csv('Get_Earnings_Tracklist.csv')
ticker_list_unclean = tracklist_df['Tickers'].tolist()
ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']

for ticker_raw in ticker_list:
  ticker = ticker_raw.replace(" ", "").upper()  # Remove all spaces from ticker_raw and convert to uppercase
  print("Getting Earnings for ", ticker)

  # todo : Why does this not work here?
  # earnings_df = pd.read_excel(dir_path + "\\" + "Stock_Files" + "\\" + ticker + '.xlsm', sheet_name="historical")
  earnings_df = pd.read_excel('C:\Sundeep\Stocks_Automation\Scripts\Experiments\Stocks_Files' + "\\" + ticker + '.xlsm', sheet_name="historical")


  print ("The Historical Tab is :", earnings_df)
  for col in earnings_df.columns:
    print(col)

  date_list = earnings_df['Date'].tolist()
  qtr_eps_list = earnings_df['Q EPS'].tolist()
  projected_eps_list = earnings_df['projection'].tolist()

  step1_df=pd.DataFrame(list(zip(date_list, qtr_eps_list, projected_eps_list)),
    columns=['Date','Q EPS', 'projection'])
  print ("New dataframe :", step1_df)

  step1_df.dropna(how='all',inplace=True)
  step1_df.dropna(subset=['Date'],inplace=True)
  step1_df.to_csv('debug1.csv')



  # Drop ONLY the rows now that do not have any data in projection tab
  # step1_df_tmp = step1_df[pd.notnull(step1_df['projection'])]
  step1_df.dropna(subset=['Q EPS', 'projection'], how='all', inplace=True)

  step1_df.to_csv('debug.csv')
  print ("New dataframe after dropping all the null from projection column:", step1_df)

  step1_date_list = step1_df['Date'].tolist()
  step1_eps_list = step1_df['Q EPS'].tolist()
  step1_projected_eps_list = step1_df['projection'].tolist()

  csvFile=open('Extracted_Earnings' + "\\" + ticker + "_earnings.csv", 'w+', newline='')
  writer = csv.writer(csvFile)
  # Put the Header Row in the csv
  writer.writerow(["Date", "Q_EPS_Diluted"])

  # todo : format the date (should be quick) before writing it in the csv (earnings) file
  tmp_index = 0
  csv_line = []
  for x in step1_date_list:
    step1_eps = step1_eps_list[tmp_index]
    step1_projected_eps = step1_projected_eps_list[tmp_index]
    print ("Index : ", tmp_index, ", Date is : ", x, ", Q EPS is : ", step1_eps, ", Projected EPS is : ", step1_projected_eps)
    if (str(step1_eps) != 'nan'):
      print ("CSV String is :", csv_line)
      if (tmp_index > 0):
        writer.writerow(csv_line)

      csv_line = []
      print ("Found 1st Instance")
      csv_line.insert(0, x.date())
      csv_line.insert(1, step1_eps)
      csv_line.insert(2, step1_projected_eps)
      insert_index = 3
    else:
      csv_line.insert(insert_index, step1_projected_eps)
      insert_index = insert_index+1
    tmp_index = tmp_index+1

csvFile.close()

