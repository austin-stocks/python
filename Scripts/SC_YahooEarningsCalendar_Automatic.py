


import csv
import datetime as dt
import openpyxl
import os
import xlrd
import logging
import sys
import pandas as pd

# This looks like an awesome package - more details about it are available at
# http://theautomatic.net/yahoo_fin-documentation/#python_version
from yahoo_fin.stock_info import *
# ##############################################################################


dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
log_dir = "\\..\\" + "Logs"

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
                    filename=dir_path + log_dir + "\\" + 'SC_YahooEarningsCalendar_Automatic_debug.txt',
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
# Read the master tracklist file into a dataframe
# -----------------------------------------------------------------------------
master_tracklist_file = "Master_Tracklist.xlsm"
master_tracklist_df = pd.read_excel(dir_path + user_dir + "\\" + master_tracklist_file, sheet_name="Main")
master_tracklist_df.sort_values('Tickers', inplace=True)
ticker_list_unclean = master_tracklist_df['Tickers'].tolist()
ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']
master_tracklist_df.set_index('Tickers', inplace=True)
# -----------------------------------------------------------------------------

now = dt.datetime.now()
now_datetime_str = now.strftime("%Y/%m/%d")
now_plus2wks_datetime = now + datetime.timedelta(days=14)
now_plus2wks_datetime_str = now_plus2wks_datetime.strftime("%Y/%m/%d")
logging.info("Will get the earnings calendar from : " + str(now_datetime_str) + " ==> " + str(now_plus2wks_datetime_str))
logging.info("")
earnings_in_week_dict_list = get_earnings_in_date_range(now_datetime_str, now_plus2wks_datetime_str)
logging.debug ("The earning in the week are " + str(earnings_in_week_dict_list))

yahoo_earnings_calendar_df = pd.DataFrame(columns=['Ticker','Earnings_Date'])
yahoo_earnings_calendar_df.set_index('Ticker', inplace=True)

# ticker_list = ["AMT", "JAZZ", "PLNT", "LGIH", "STWD", "RHP", "IIPR", 'USPH', 'EME', 'CBRE']
for tmp_dict in earnings_in_week_dict_list:
    logging.debug("Ticker : " + str(tmp_dict['ticker']) +  ", Earnings Date : " + str(tmp_dict['startdatetime']))
    if (tmp_dict['ticker'] in ticker_list):
      logging.info("Ticker : " + str(tmp_dict['ticker']) + ", Earnings Date : " + str(tmp_dict['startdatetime']))
      ticker = tmp_dict['ticker']
      earnings_date_str = tmp_dict['startdatetime'][0:10]
      earnings_date_dt = dt.datetime.strptime(earnings_date_str , '%Y-%m-%d')
      logging.debug("Earnings Date str is : " + str(earnings_date_str) + ", and earnings date dt is : " + str(earnings_date_dt))
      yahoo_earnings_calendar_df.loc[ticker] = earnings_date_str

now_datetime_str = now.strftime("%Y_%m_%d")
yahoo_earnings_calendar_logfile = "yahoo_earnings_calendar_" + now_datetime_str + ".csv"
yahoo_earnings_calendar_df.sort_values(by=['Earnings_Date','Ticker'], ascending=[True,True]).to_csv(dir_path + log_dir + "\\" + yahoo_earnings_calendar_logfile,sep=',', index=True, header=True)

# Try to get the earnings calendar in the format that would work just plug and play for Tracklist
yahoo_earnings_calendar_df.reset_index(inplace=True)
grouped_by_series = yahoo_earnings_calendar_df.groupby(["Earnings_Date"])["Ticker"].agg(lambda x: ' '.join(x))
logging.debug("The Earnings Calendar with grouped_by \n" + grouped_by_series.to_string())
# Now convert that series into dataframe
grouped_by_df = pd.DataFrame({'Earnings_Date':grouped_by_series.index, 'Ticker':grouped_by_series.values})
logging.debug("The Earnings Calendar with grouped_by \n" + grouped_by_df.to_string())

# I could not find a pythonic way of doing this, so doing it with a loop
pivoted_df = pd.DataFrame()

i = 0
for index, row in grouped_by_df.iterrows():
    logging.debug("Row " + row['Earnings_Date'] + ", Value " + row['Ticker'])
    tickers_split_list = row['Ticker'].split()
    pivoted_df[row['Earnings_Date']] = row['Ticker']
    for ticker in sorted(tickers_split_list,key=str):
     logging.debug("Row " + row['Earnings_Date'] + ", Ticker " + ticker)

    i = i+1

logging.debug("The Earnings Calendar with index as Earnings_Date looks like \n" + pivoted_df.to_string())

