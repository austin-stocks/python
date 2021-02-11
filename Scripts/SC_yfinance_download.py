
import yfinance as yf
import os
import sys
import logging

def human_format(num, precision=2, suffixes=['', 'K', 'M', 'B', 'T', 'P']):
  m = sum([abs(num / 1000.0 ** x) >= 1 for x in range(1, len(suffixes))])
  return f'{num / 1000.0 ** m:.{precision}f} {suffixes[m]}'


dir_path = os.getcwd()
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
                    filename=dir_path + log_dir + "\\" + 'SC_yfinance_download_debug.txt',
                    filemode='w')
# define a Handler which writes INFO messages or higher to the sys.stderr
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
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

ticker_list = ['XLB','XLC','XLE','XLF','XLI','XLK', 'XLP','XLRE','XLU','XLV','XLY']

# https://www.cnbc.com/sector-etfs/
# https://etfdb.com/etfs/

# sector_etf_df =
# XLE	Energy Select Sector SPDR Fund
# XLF	Financial Select Sector SPDR Fund
# XLU	Utilities Select Sector SPDR Fund
# XLI	Industrial Select Sector SPDR Fund
# XLK	Technology Select Sector SPDR Fund
# XLV	Health Care Select Sector SPDR Fund
# XLY	Consumer Discretionary Select Sector SPDR Fund
# XLP	Consumer Staples Select Sector SPDR Fund
# XLB	Materials Select Sector SPDR Fund


# GDX	VanEck Vectors Gold Miners ETF
# XOP	Spdr S&P Oil & Gas Exploration & Production Etf
# IYR	iShares U.S. Real Estate ETF
# XHB	Spdr S&P Homebuilders Etf
# ITB	iShares U.S. Home Construction ETF
# VNQ	Vanguard Real Estate Index Fund ETF Shares
# GDXJ	VanEck Vectors Junior Gold Miners ETF
# IYE	iShares U.S. Energy ETF
# OIH	VanEck Vectors Oil Services ETF
# XME	SPDR S&P Metals & Mining ETF
# XRT	Spdr S&P Retail Etf
# SMH	VanEck Vectors Semiconductor ETF
# IBB	iShares Nasdaq Biotechnology ETF
# KBE	SPDR S&P Bank ETF
# KRE	SPDR S&P Regional Banking ETF
# XTL	SPDR S&P Telecom ETF

print(yf.__version__)
i_itr = 1
for ticker in ticker_list :
  # ticker = 'XLE'

  logging.debug("Iteration : " + str(i_itr) + " : " + ticker)

  console.setLevel(logging.INFO)
  ticker_yf = yf.Ticker(ticker)
  ticker_name = ticker_yf.info['longName']
  ticker_market_cap = ticker_yf.info['totalAssets']
  console.setLevel(logging.DEBUG)

  # logging.debug(ticker_yf.info)
  logging.debug("Long Name  : " + ticker_name)
  logging.debug("Market Cap : " + str(human_format(ticker_market_cap)))

  # -------------------------------------------------------
  # Both of these work - research and then see which one you want to use
  # historical_df = ticker_yf.history(period="1y", interval="1d")
  console.setLevel(logging.INFO)
  # historical_df = ticker_yf.history(start = "2017-01-01", end = "2017-04-30", interval="1d")
  console.setLevel(logging.DEBUG)
  # -------------------------------------------------------

  # close_0_days_ago = historical_df['Close'][0]
  # logging.debug("The historical df is :\n" + historical_df.to_string())
  # logging.debug("\n")
  # logging.debug("The last close price :" + str(close_0_days_ago))

  logging.debug("")
  i_itr = i_itr+1