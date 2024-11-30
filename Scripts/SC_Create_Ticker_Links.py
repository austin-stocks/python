# ##############################################################################
# Download the historical data into individual csv
# ##############################################################################

import csv
import datetime
import openpyxl
import os
import xlrd
import datetime as dt
import time
import pandas as pd
from termcolor import colored, cprint
import sys
import logging
# ##############################################################################

# =============================================================================
# Define the various File names and Directory Paths to be used and set the
# start and end dates
# =============================================================================
dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
log_dir = "\\..\\..\\..\\Automation_Not_in_Git\\" + "Logs"
tracklist_file = "Tracklist.csv"
tracklist_file_full_path = dir_path + user_dir + "\\" + tracklist_file
# =============================================================================

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
                    filename=dir_path + log_dir + "\\" + 'SC_Create_Ticker_links_log.txt',
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

# -----------------------------------------------------------------------------
# Read the tracklist file
# -----------------------------------------------------------------------------
get_sp_holdings = 0
get_qqq_holdings = 0
get_ibd50_holdings = 0
if (get_sp_holdings == 1):
  tracklist_df = pd.read_excel(dir_path + user_dir + "\\" + 'SPY_Holdings.xlsx', sheet_name="SPY")
  ticker_list_unclean = tracklist_df['Identifier'].tolist()
  ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']
elif (get_qqq_holdings == 1):
  tracklist_df = pd.read_excel(dir_path + user_dir + "\\" + 'QQQ_Holdings.xlsx', sheet_name="QQQ")
  ticker_list_unclean = tracklist_df['HoldingsTicker'].tolist()
  ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']
elif (get_ibd50_holdings == 1):
  tracklist_df = pd.read_excel(dir_path + user_dir + "\\" + 'IBD50_Holdings.xlsx', sheet_name="IBD50")
  ticker_list_unclean = tracklist_df['Symbol'].tolist()
  ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']
else:
  # Read the trracklist and convert the read tickers into a list
  tracklist_df = pd.read_csv(tracklist_file_full_path)
  # print ("The Tracklist df is", tracklist_df)
  ticker_list_unclean = tracklist_df['Tickers'].tolist()
  ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']
# -----------------------------------------------------------------------------

yahoo_comany_info_df = pd.read_excel(dir_path + user_dir + "\\" + 'Yahoo_Company_Info.xlsm', sheet_name="Company_Info")
yahoo_comany_info_df.set_index('Ticker', inplace=True)
# logging.info (yahoo_comany_info_df)

## Read the IBD Data Tables to get some information
## 'RS Rating', 'PE Ratio', 'Industry Group Rank', '# of Funds - last reported qrtr', ' Comp. Rating', 'EPS Rating', 'Acc/Dis Rating',Ind Grp RS', 'SMR Rating', 'Spon Rating', 'Last Qtr EPS % Chg.', 'Curr Qtr EPS Est. % Chg.', 'Curr Yr EPS Est. % Chg.', 'Last Qtr Sales % Chg.', 'Pretax Margin', 'IPO Date'

## Read the AAII financial to get some information


ticker_links_df = pd.DataFrame(columns=['Ticker','Name', 'Sector', 'Industry','SChart', 'CNBC-Earnings','CNBC-Fin','Y-Profile','Y-BS','PSI','AAII'])
ticker_links_df.set_index('Ticker', inplace=True)

# -----------------------------------------------------------------------------
# For each ticker in ticker_list create the links and put that in the df
# Once done, that df is printed out in the xlsx file in the logdir
# -----------------------------------------------------------------------------
i = 1
for ticker_raw in ticker_list:
  # time.sleep(7)
  missing_data_found = 0
  missing_data_index = ""
  ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase
  logging.info("Iteration no : " +str(i) + " : " + str(ticker))

  # Remove the "." from the ticker and replace by "-" as this is what Yahoo has
  if (ticker == "BRK.B"):
    ticker = "BRK-B"
  elif (ticker == "BF.B"):
    ticker = "BF-B"

  ticker_company_name = "#NA#"
  ticker_sector = "#NA#"
  ticker_industry = "#NA#"
  chart_update_date_str = "#NA#"
  if (yahoo_comany_info_df.index.isin([(ticker)]).any()):
    # This works - get the value in the column corresponding to the index
    ticker_company_name = yahoo_comany_info_df.loc[ticker, 'Company_Name']
    ticker_sector = yahoo_comany_info_df.loc[ticker, 'Sector']
    ticker_industry = yahoo_comany_info_df.loc[ticker, 'Industry']

  ticker_links_df.loc[ticker, 'Name'] = ticker_company_name
  ticker_links_df.loc[ticker, 'Sector'] = ticker_sector
  ticker_links_df.loc[ticker, 'Industry'] = ticker_industry
  ticker_links_df.loc[ticker, 'SChart'] = 'https://stockcharts.com/h-sc/ui?s='+str(ticker)
  ticker_links_df.loc[ticker, 'PSI'] = 'https://www.profitspi.com/stock/view.aspx?v=stock-chart&uv=294571&p=' + str(ticker)
  ticker_links_df.loc[ticker, 'CNBC-Earnings'] = 'https://www.cnbc.com/quotes/' + str(ticker) +'?tab=earnings'
  ticker_links_df.loc[ticker, 'CNBC-Fin'] = 'https://www.cnbc.com/quotes/' + str(ticker) +'?tab=financials'
  ticker_links_df.loc[ticker, 'Y-Profile'] = 'https://finance.yahoo.com/quote/' + str(ticker)
  ticker_links_df.loc[ticker, 'Y-BS'] = 'https://finance.yahoo.com/quote/' + str(ticker) + "/balance-sheet"
  ticker_links_df.loc[ticker, 'AAII'] = 'https://www.aaii.com/stock/ticker/' + str(ticker)

  i = i+1

logging.info("")
logging.info("Now creating xlsx with links in the logdir : ")
# Now print to the file
curr_date = dt.date.today()
# logging.info("Todays date is : " + str(curr_date))
ticker_links_logfile= str(curr_date) + "_" + "Tickers_Links.xlsx"
writer = pd.ExcelWriter(dir_path + log_dir + "\\" + ticker_links_logfile, engine='xlsxwriter')
# ticker_links_df.sort_values(by=['Ticker'], ascending=[False]).to_excel(writer)
ticker_links_df.to_excel(writer)
logging.info("Created : " + str(log_dir) + "\\"  + str(ticker_links_logfile) + " <-- Tickers links")
writer.close()
logging.info("All Done...")
