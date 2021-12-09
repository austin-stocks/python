
import pandas as pd
from yahoo_fin.stock_info import *




print ("Here I am")

# This looks like an awesome package 
#  more details about it are available at 
# http://theautomatic.net/yahoo_fin-documentation/#python_version

ticker_list=["AAON","ACU","ADUS","AME","AMP","ASGN","AUDC","AVTR","AYI","BAH","BLD","BRO","CACC","CACI","CASH","CASY","CBOE","CCK","CCMP","CCOI","CHD","CHE","CHRW","CMBM","CNXN","CPSI","CSGP","CSGS","CTAS","DCO","ECOM","EME","ENSG","ESNT","FAF","FDS","FHI","FIX","FN","FORM","FOXA","FOXF","G","GDOT","GLDD","GOOG","HCSG","HEI","HELE","HONE","HSIC","HTH","IAA","IBP","ICLR","IDCC","INOV","IOSP","ISBC","JBSS","JBT","KAI","KEX","LFUS","LGIH","LHCG","LOPE","LPLA","LSI","LSTR","MANT","MBUU","MEDP","MLKN","MMS","MRCY","MSEX","MTX","MYRG","NMIH","NSIT","NSP","NSSC","NTGR","NXST","OMCL","OSIS","OTEX","PFSI","PNTG","POWL","PRAA","PRI","RJF","SAIA","SCPL","SEM","SGC","SITE","SLGN","SMPL","SNX","SSD","SSNC","TCBI","TDY","TFX","TKR","TNET","TRU","TSM","TTGT","TXRH","TYL","UFPI","UFPT","UNF","USPH","VRSK","WAL","WLDN","WLTW","WNS"]
ticker_list=["FIZZ", "RH", "THO", "AVGO", "CIEN", "COST", "LULU", "ORCL"]

# i_int = 0
# for ticker_raw in ticker_list:
#   ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase
#   i_int += 1
#   ticker_quote_dict = get_quote_table(ticker)
#   ticker_earnings_date = ticker_quote_dict['Earnings Date']
#
#   print ("Next earnings date for : ", ticker ," is : ", ticker_earnings_date)

earnings_in_week_dict_list = get_earnings_in_date_range('12/12/2021', '12/19/2021')
print ("The earning in the week are ", earnings_in_week_dict_list)
for tmp_dict in earnings_in_week_dict_list:
    print ("Ticker : ", tmp_dict['ticker'], ", Earnings Date : " ,tmp_dict['startdatetime'])

# ticker = "gm"
# ticker_quote_dict = get_quote_table(ticker)
# ticker_holders_dict = get_holders(ticker)
#
# print ("Ticker Quote Dict is", ticker_quote_dict)
# print ("Ticker Holders  Dict is", ticker_holders_dict)
#
# ticker_1y_target_price  = ticker_quote_dict['1y Target Est']
# ticker_earnings_date = ticker_quote_dict['Earnings Date']
# ticker_curr_price = ticker_quote_dict['Quote Price']
# print ("Current Price : ", ticker_curr_price, ", 1 yr Target price is : ", ticker_1y_target_price, ", Upside : ", (ticker_1y_target_price/ticker_curr_price -1)*100, "%")
# print ("Next earnings date is : ", ticker_earnings_date)


# The following methods are supported by the module stock_info
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
