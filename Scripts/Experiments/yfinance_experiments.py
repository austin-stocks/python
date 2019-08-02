
import yfinance as yf

ticker = 'HD'
ticker_yf = yf.Ticker(ticker)
print (ticker_yf.info)
print (ticker_yf.dividends)
print (ticker_yf.splits)
# print (ticker_yf.history(period="max"))