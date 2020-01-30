# ##############################################################################
# Download the historical data into individual csv
# ##############################################################################

import csv
import datetime
import openpyxl
import os
import xlrd
from yahoo_earnings_calendar import YahooEarningsCalendar

import pandas as pd
from yahoofinancials import YahooFinancials
# ##############################################################################

# =============================================================================
# Define the various File names and Directory Paths to be used and set the
# start and end dates
# =============================================================================
# dir_path = os.getcwd()
# user_dir = "\\..\\" + "User_Files"
# tracklist_file = "Tracklist.csv"
# tracklist_file_full_path = dir_path + user_dir + "\\" + tracklist_file
# yahoo_hist_out_dir = dir_path + "\\..\\Download\\YahooHistorical"
#
# start_date = '1900-01-01'
# # end_date_raw = str(datetime.datetime.now().year) + \
# #        "-" + str(datetime.datetime.now().month) + \
# #        "-" + str(datetime.datetime.now().day)
# end_date_raw = datetime.datetime.today() + datetime.timedelta(days=1)
# end_date = end_date_raw.strftime('%Y-%m-%d')
# # end_date = '2015-08-15'
# print ("Start Date set to: ", start_date, ", End Date set to: ", end_date)
# # =============================================================================


yec = YahooEarningsCalendar()
# Returns the next earnings date of BOX in Unix timestamp
unixtimestamp = yec.get_next_earnings_date('DIS')
# 1508716800
next_earnings_date = datetime.datetime.fromtimestamp(unixtimestamp).strftime('%Y-%m-%d %H:%M:%S')
next_earnings_date = datetime.datetime.fromtimestamp(unixtimestamp).strftime('%m/%d/%Y')
print ("Next earnings date for IBM is", next_earnings_date)


# date_from = datetime.datetime.strptime(
#     'Jan 31 2020  10:00AM', '%b %d %Y %I:%M%p')
# date_to = datetime.datetime.strptime(
#     'Feb 8 2020  1:00PM', '%b %d %Y %I:%M%p')
# print(yec.earnings_between(date_from, date_to))

print("Done")
# ##############################################################################



