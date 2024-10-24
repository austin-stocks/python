import logging
import os
import sys
import datetime as dt
import pandas as pd
from yahooquery import Ticker

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
  # if ticker in ["ASML", "TSM"]:
  #   logging.info("Iteration : " + f"{str(i_int) : <3}" + " =====> Skipping <===== : " + f"{str(ticker) : <6}" + " As Yahoo generally does not have an earnings date for it")
  #   continue
  ticker_calendar_events = Ticker(ticker).calendar_events
  logging.debug("The Calendear Events data is : " + str(ticker_calendar_events))
  try:
    earnings_date_str = ticker_calendar_events[ticker]['earnings']['earningsDate'][0]
  except (IndexError):
    logging.error("**********                                ERROR                               **********")
    logging.error("Could not download earnings date for ", ticker)
    yahoo_earnings_calendar_df.loc[ticker] = "#NA#"
    continue

  logging.info("Iteration : " + f"{str(i_int) : <3}" + " Processed : " + f"{str(ticker) : <6}" + " Earnings Date : " + f"{str(earnings_date_str) : <10}")
  yahoo_earnings_calendar_df.loc[ticker] = [earnings_date_str]
  if i_int == 50:
    break

now = dt.datetime.now()
date_time = now.strftime("%Y_%m_%d")
yahoo_earnings_calendar_logfile = "yahooquery_earnings_calendar_" + date_time + ".csv"
yahoo_earnings_calendar_df.sort_values(by=['Earnings_Date', 'Ticker'], ascending=[True, True]).to_csv(dir_path + log_dir + "\\" + yahoo_earnings_calendar_logfile, sep=',', index=True, header=True)
