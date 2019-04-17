
import pip
import openpyxl
import os
import logging
import time
import math

import pandas as pd
import xlrd as xl
import datetime as datetime_var
import pandas_datareader as pdr

from pandas import ExcelWriter
from pandas import ExcelFile
from xlrd import open_workbook, Book

def find_cell_addr(ws,tmp_str):
  for row in range(ws.nrows):
    for column in range(ws.ncols):
      if tmp_str == ws.cell(row, column).value:
        ## Need to find out how to make logger visible inside a def
        ##logger.debug("Found %s at Row: %s, Column: %s ",  tmp_str , row, column)
        return (row, column)

def main():
  logger = logging.getLogger()
  logger.setLevel(logging.DEBUG)

  formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

  fh = logging.FileHandler('log_filename.txt')
  fh.setLevel(logging.DEBUG)
  fh.setFormatter(formatter)
  logger.addHandler(fh)

  ch = logging.StreamHandler()
  ch.setLevel(logging.DEBUG)
  ch.setFormatter(formatter)
  logger.addHandler(ch)

  logger.debug ("Hello Worldd");

  dir_path = os.getcwd()
  logger.debug (dir_path)
  ticker = "AAL"
  ticker_fullpath=dir_path + "\\" + ticker + ".xlsm"
  logger.debug (ticker_fullpath)


  ## ------------------------------------------------------------------------------
  ## This is from pandas to read the xlsm file
  ## ------------------------------------------------------------------------------
  df=pd.read_excel(ticker_fullpath, sheetname="historical")
  logger.debug (df)
  ## This gets all the columns in the dataframe
  columns_name_list = df.columns.values.tolist()
  logger.debug(columns_name_list)
  open_price_col = df["Open"]
  ## logger.debug(open_price_col)
  for i in range(1,len(open_price_col)):
    print (open_price_col[i])
    if math.isnan(open_price_col[i]) == False:
      print ("Found the first non empty cell at row %s", i)
      ## Get the Date for the row above it
      date_last_historical = df.iloc[i-1,0]
      logger.debug("The oldest Date to start inserting from is %s", date_last_historical)
      break
  ## ------------------------------------------------------------------------------




  ## -------------------------------------------------------------------------
  ## Gets Yahoo Historical Data
  ## -------------------------------------------------------------------------
  time.sleep(5)
  ## ticker_historical = pdr.DataReader(ticker, 'yahoo', datetime_var.datetime(2018,11,12), datetime_var.datetime(2018,11,19))
  ticker_historical = pdr.DataReader(ticker, 'yahoo', datetime_var.datetime(date_last_historical.year,date_last_historical.month,date_last_historical.day),datetime_var.datetime(2018, 11, 18))
  my_test = type(ticker_historical)
  logger.debug("\n\nType %s", my_test)
  logger.debug("The first row: %s",ticker_historical.iloc[0])

  columns_name_list = ticker_historical.columns.values.tolist()
  columns_name_list = ticker_historical.columns.values
  logger.debug("The list of the columns are : %s" , columns_name_list[0])
  ticker_historical_sorted = ticker_historical.sort_values(by='Date', ascending=False)
  ## logger.debug (ticker_historical['Adj Close'])
  logger.debug (ticker_historical_sorted)
  ## -------------------------------------------------------------------------

  ## How to insert the datafram in excel file


  ## How to change the format of the date in the fist column
  columns_name_list = ticker_historical_sorted.columns.values.tolist()
  logger.debug("The list of the columns are : %s" , columns_name_list)
  '''
  date_col = ticker_historical_sorted["Date"]
  for i in range(1,len(date_col)):
    date_year = date_col[i].year
    date_month = date_col[i].month
    date_day = date_col[i].day
    date_new = date_month + "/" + date_day + "/" + date_year
    logger.debug("Formatted date is %s", date_new)
    '''



  ## How to loop around all the files

  '''

  wb=openpyxl.load_workbook(filename=ticker_fullpath,read_only=False,keep_vba=True,data_only=True)
  ws=wb.get_sheet_by_name("historical")

  ## ------------------------------------------------------------------------------
  ## This is from xlrd
  ## ------------------------------------------------------------------------------
  wb=open_workbook(ticker_fullpath)
  for ws in wb.sheets():
    logger.debug ("Sheet: %s", ws.name)

  ws=wb.sheet_by_name("historical")
  what_srch="Volume"
  logger.debug("Worksheet: %s, Matching: %s", ws.name, what_srch)
  (row,column)= find_cell_addr(ws,what_srch)
  logger.debug("Worksheet: %s, Matched: %s, Matching Row: %s, Matching Column: %s", ws.name, what_srch,row,column)
  ## ------------------------------------------------------------------------------
  '''

if __name__ == main():
    main()
