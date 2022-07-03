import argparse
import sys
import datetime as dt
from time import sleep
from typing import Optional

import requests
import requests_html
from requests.models import Response

import os
import sys
import logging
import pandas as pd
import datetime as dt

# =============================================================================
# Define the various filenames and Directory Paths to be used
# =============================================================================
dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
tracklist_file = "Tracklist.csv"
calendar_file = "Calendar.csv"
configuration_file = "Configurations.csv"
tracklist_file_full_path = dir_path + user_dir + "\\" + tracklist_file
calendar_file_full_path = dir_path + user_dir + "\\" + calendar_file
configurations_file_full_path = dir_path + user_dir + "\\" + configuration_file
yahoo_hist_in_dir = dir_path + "\\..\\Download\YahooHistorical"
yahoo_hist_out_dir = dir_path + "\\..\\Historical"
log_dir = "\\..\\" + "Logs"
# =============================================================================

# -----------------------------------------------------------------------------
# Function to get the page from tipranks
# -----------------------------------------------------------------------------
def get_page(url: str) -> Response:
  headers: str = {"User-Agent": requests_html.user_agent()}
  with requests_html.HTMLSession() as s:
    resp: Response = s.get(url, headers=headers)
    try:
      resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
      print(e)
      return None
  # print ("Returning :\n" , resp.text)
  return resp
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Function to process the information from the page
# -----------------------------------------------------------------------------
def process_page(url: str, verbose: bool) -> Optional[tuple]:
  count = 0
  max_retries = 3
  while count < max_retries:
    # Checking the count rather than sleep on the final loop check when we are just going to exit
    if not count == 0:
      sleep(5)
    try:
      page = get_page(url)
      print ("Here in trying...")
      # print ("Gotten :\n", page)
      page.html.render(sleep=2)
      # print("Now it has turned to \n", page.text)
    except:
      print ("Here in except...")
      if verbose:
        print("An error occurred during page loading and processing")
      return None
    row = page.html.find(".rt-tbody .rt-tr", first=True)
    # print ("Now it has turned to \n", row.text)
    if row:
      print ("Here in row...")
      # There is row data so continue processing
      break
    if page.html.find(
      ".client-components-stock-research-earings-style__EarningsHistoryTable span",
      containing="Currently, no data available",
    ):
      # This ticker doesn't provide earnings calendar data so exit rather than try to reload
      print ("Here in if page.html.find...")
      if verbose:
        print(f"Notice: No earnings calendar available for this stock ticker")
      return None
    if verbose:
      print(f"Sleeping... ({count + 1})")
    print("Here in sleep and incrementing count...")
    count += 1
  else:
    # Page loading has failed to return the row afer 'max_retries'
    print("Here in else when page loading has failed...")
    return None

  data = row.find(".rt-td")
  print("Here in extracting data from row for final return...")
  # print ("Now it has turned to \n", data)
  return data[0].text, data[1].text
# -----------------------------------------------------------------------------


# =============================================================================
# Main Program
# =============================================================================
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
TipRanks_earnings_calendar_df = pd.DataFrame(columns=['Ticker','Earnings_Date'])
TipRanks_earnings_calendar_df.set_index('Ticker', inplace=True)

ticker_list=["AAON","ABG","ACU","ADUS","AQUA","ASGN","ASML","AUDC","AVNT","AVTR","AZPN","BERY","BLD","BRO","CACC","CACI","CARG","CASH","CCK","CCMP","CCOI","CCS","CDW","CENT","CHE","CMBM","CNXN","CPSI","CRMT","CRNC","CSGP","CSGS","CSL","CUTR","DCO","ECOM","EME","ENSG","ESNT","EVC","EVTC","EXP","EXTR","FAF","FHI","FIX","FIZZ","FLT","FN","FOXA","G","GDOT","GLDD","GNTX","GOOG","GPI","HAE","HCSG","HELE","HONE","HTH","IAA","IART","ICLR","IEX","IIIN","IOSP","JBSS","JBT","KAI","LFUS","LGIH","LHCG","LOPE","LPLA","LSTR","MANT","MASI","MEDP","MKTX","MMS","MSEX","MTX","MYRG","NMIH","NSIT","NSP","NSSC","NTGR","NVT","OMCL","OSIS","OTEX","PFSI","PLUS","PNTG","POWL","PRAA","PRFT","PRI","PRIM","PZZA","QLYS","RBA","RRX","RUTH","SCPL","SF","SITE","SKYW","SLGN","SNBR","SSNC","STRL","SYNH","TCBI","TDY","TFX","THRM","TITN","TKR","TNET","TRU","TSM","TTEC","TTEK","TTGT","TYL","UFPI","UFPT","UI","UNF","USPH","VRSK","WAL","WD","WING","WLDN","WNS","WTW","XPEL"]
# ticker_list = ["AMT", "IBM"]
i_int = 0
for ticker_raw in ticker_list:
  ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase
  i_int += 1

  url: str = f"https://www.tipranks.com/stocks/{ticker}/earnings-calendar"

  print("\nIteration : " + str(i_int) + " Processing : " + str(ticker))

  quality_of_stock = master_tracklist_df.loc[ticker, 'Quality_of_Stock']
  if ((quality_of_stock != 'Wheat') and (quality_of_stock != 'Wheat_Chaff') and (quality_of_stock != 'Essential') and (quality_of_stock != 'Sundeep_List')):
    # logging.info (str(ticker) +  " is not Wheat or Essential...skipping")
    print (str(ticker) +  " is not Wheat or Essential...skipping")
    continue

  scraped_data: tuple = process_page(url, '1')
  # print("The scraped data is", scraped_data)
  if scraped_data:
    # datetime = dt.datetime.strptime(scraped_data[0], "%b %d, %Y")
    # output: str = f"{dt.date().isoformat()}|{scraped_data[1]}"
    # print("The earnings data is", output)

    earnings_date_dt = dt.datetime.strptime(scraped_data[0], "%b %d, %Y")
    print("The earnings date is", earnings_date_dt)
    ticker_next_earnings_date_str = dt.datetime.strftime(earnings_date_dt, '%m/%d/%Y')
    TipRanks_earnings_calendar_df.loc[ticker] = [ticker_next_earnings_date_str]
  else:
    print("No data available")
    TipRanks_earnings_calendar_df.loc[ticker] = '#NA#'
           
# =============================================================================

now = dt.datetime.now()
date_time = now.strftime("%Y_%m_%d")
TipRanks_earnings_calendar_logfile = "TipRanks_earnings_calendar_" + date_time + ".csv"
TipRanks_earnings_calendar_df.sort_values(by=['Earnings_Date','Ticker'], ascending=[True,True]).to_csv(dir_path + log_dir + "\\" + TipRanks_earnings_calendar_logfile,sep=',', index=True, header=True)


