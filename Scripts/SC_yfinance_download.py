
import yfinance as yf

# https://www.cnbc.com/sector-etfs/
# https://etfdb.com/etfs/

# sector_etf_df =
# XLE	Energy Select Sector SPDR Fund
# XLF	Financial Select Sector SPDR Fund
# XLU	Utilities Select Sector SPDR Fund
# XLI	Industrial Select Sector SPDR Fund
# GDX	VanEck Vectors Gold Miners ETF
# XLK	Technology Select Sector SPDR Fund
# XLV	Health Care Select Sector SPDR Fund
# XLY	Consumer Discretionary Select Sector SPDR Fund
# XLP	Consumer Staples Select Sector SPDR Fund
# XLB	Materials Select Sector SPDR Fund
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
for ticker in ['MSFT', 'XLY', '^GSPC', 'XLE']:
  # ticker = 'XLE'
  print ("Getting the data for ", ticker)
  ticker_yf = yf.Ticker(ticker)
  # print (ticker_yf.info)
  # print (ticker_yf.dividends)
  # print (ticker_yf.splits)
  # print (ticker_yf.history(period="1year"))

  # Both of these work - research and then see which one you want to use
  # historical_df = ticker_yf.history(period="1y", interval="1d")
  historical_df = ticker_yf.history(start = "2017-01-01", end = "2017-04-30", interval="1d")

  close_0_days_ago = historical_df['Close'][0]
  print ("The historical df is :\n", historical_df)
  print ("\n")
  print ("The last close price :", close_0_days_ago)
