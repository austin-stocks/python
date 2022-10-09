import logging
import os
import sys
import datetime as dt
import pandas as pd


import yahoo_fin.stock_info as si
# http://theautomatic.net/yahoo_fin-documentation/
# The methods available with the package are
# get_analysts_info
# get_balance_sheet
# get_cash_flow
# get_company_info
# get_currencies
# get_data
# get_day_gainers
# get_day_losers
# get_day_most_active
# get_dividends
# get_earnings
# get_earnings_for_date
# get_earnings_in_date_range
# get_earnings_history
# get_financials
# get_futures
# get_holders
# get_income_statement
# get_live_price
# get_market_status
# get_next_earnings_date
# get_premarket_price
# get_postmarket_price
# get_quote_data
# get_quote_table
# get_top_crypto
# get_splits
# get_stats
# get_stats_valuation
# get_undervalued_large_caps
# tickers_dow
# tickers_ftse100
# tickers_ftse250
# tickers_ibovespa
# tickers_nasdaq
# tickers_nifty50
# tickers_niftybank
# tickers_other
# tickers_sp500

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
                    filename=dir_path + log_dir + "\\" + 'SC_Yahoo_fin_debug.txt',
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
# Read the master tracklist file into a dataframe
# -----------------------------------------------------------------------------
master_tracklist_file = "Master_Tracklist.xlsm"
master_tracklist_df = pd.read_excel(dir_path + user_dir + "\\" + master_tracklist_file, sheet_name="Main")
master_tracklist_df.sort_values('Tickers', inplace=True)
ticker_list_unclean = master_tracklist_df['Tickers'].tolist()
ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']
# -----------------------------------------------------------------------------

yahoo_earnings_calendar_df = pd.DataFrame(columns=['Ticker','Earnings_Date'])
yahoo_earnings_calendar_df.set_index('Ticker', inplace=True)

i_int = 0
# ticker_list=["AAON","ABG","ACU","ADUS","ARES","ASGN","ASML","ATHM","AVNT","AVTR","AYI","BAH","BLD","CACC","CASH","CCOI","CCS","CENT","CHE","CMBM","CNXN","CPSI","CSGS","CUTR","DCO","DKL","ECOM","EME","ENSG","ESNT","EVC","EVTC","EXP","FAF","FHI","FIX","FIZZ","FORM","FOXF","G","GDOT","GNTX","GPI","HCSG","HELE","HONE","HTH","IAA","IART","IBP","ICLR","IDCC","IEX","IIIN","IOSP","JBT","KAI","KEX","LFUS","LGIH","LHCG","LOPE","LSI","LSTR","MANT","MEDP","MIDD","MITK","MKTX","MLKN","MMS","MSEX","MTX","NMIH","NSIT","NSP","NTGR","NVT","OMCL","PFSI","PLUS","POWL","PRAA","PRI","PRIM","RBA","RRX","RUTH","SAIA","SCPL","SEM","SF","SITE","SKYW","SLGN","SMPL","SNBR","SNX","SSD","SSNC","STRL","TCBI","TDY","TFX","THRM","TKR","TNET","TPX","TRU","TSM","TTEK","TTGT","UFPI","UFPT","UNF","USPH","VIVO","WERN","WLDN","WNS","WTW","ZUMZ"]# ticker_list = ["AMT", "JAZZ", "PLNT", "LGIH", "STWD", "RHP", "IIPR", 'USPH', 'EME', 'CBRE']
for ticker_raw in ticker_list:
  ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase
  i_int += 1
  # logging.info("\nIteration : " + str(i_int) + " Processing : " + str(ticker))
  # print("\nIteration : " + str(i_int) + " Processing : " + str(ticker))
  if ticker in ["ASML", "TSM"]:
    logging.info("Iteration : " + str(i_int) + " =====> Skipping <===== : " + str(ticker) + " As Yahoo generally does not have an earnings date for it")
    continue
  try:
    earnings_date_dt = si.get_next_earnings_date(ticker)
  except (IndexError):
    logging.error("**********                                ERROR                               **********")
    logging.error("Could not download earnings date for ", ticker)
    yahoo_earnings_calendar_df.loc[ticker] = "#NA#"
    continue

  earnings_date_str = earnings_date_dt.strftime('%m/%d/%Y')
  logging.info("Iteration : " + str(i_int) + " Processed : " + str(ticker) + " Earnings Date : " + str(earnings_date_str))
  # print("Iteration : ", i_int ," Processed : ", ticker ," Earnings Date : ", earnings_date_str)
  yahoo_earnings_calendar_df.loc[ticker] = [earnings_date_str]

  now = dt.datetime.now()
  date_time = now.strftime("%Y_%m_%d")
  yahoo_earnings_calendar_logfile = "yahoo_fin_earnings_calendar_" + date_time + ".csv"
  yahoo_earnings_calendar_df.sort_values(by=['Earnings_Date', 'Ticker'], ascending=[True, True]).to_csv(dir_path + log_dir + "\\" + yahoo_earnings_calendar_logfile, sep=',', index=True, header=True)
