import pandas as pd
import matplotlib
import os
import math
import json
import sys
from yahoofinancials import YahooFinancials
import datetime as dt
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.offsetbox import AnchoredText
import matplotlib.dates as mdates
from mpl_finance import candlestick_ohlc

from pandas.plotting import register_matplotlib_converters

register_matplotlib_converters()





dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
chart_dir = "..\\" + "Charts"
historical_dir = "\\..\\..\\" + "Historical"

ticker = "MEDP"

# =============================================================================
# Read the Historical file for the ticker
# =============================================================================
# todo : There are certain cases (MEDP) for e.g. that has recently IPO'ed that
# have earning going back 2-3 quarters more than the historical data (in other
# words they started trading on say 08/12/2015, but their earnings are available
# from 03/30/2015). In such a case probably need to look at calendar file and extend
# the date list and adj_close list so that all the prior earnings are included.
# The back date adj_close needs to be initialized to whatever value (nan likely)
historical_df = pd.read_csv(dir_path + "\\" + historical_dir + "\\" + ticker + "_historical.csv")
print("The Historical df is \n", historical_df)
ticker_adj_close_list = historical_df.Adj_Close.tolist()
print ("Historical Adj. Prices", type(ticker_adj_close_list))
date_str_list = historical_df.Date.tolist()
print("The date list from historical df is ", date_str_list)
date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in date_str_list]
print("The date list for historical is ", date_list, "\nit has ", len(date_list), " entries")
# =============================================================================

# Get the candlesticks_df that starts from the latest date for which the prices is
# available.
historical_columns_list = list(historical_df)
print ("The columns in Historical Dataframe ", historical_columns_list)

ticker_curr_price = next(x for x in ticker_adj_close_list if not math.isnan(x))
ticker_curr_date = date_list[ticker_adj_close_list.index(ticker_curr_price)]
candlestick_df = historical_df.loc[ticker_adj_close_list.index(ticker_curr_price):]
candlestick_df.columns =  historical_columns_list
print ("Candlestick Dataframe is ",candlestick_df)

# this works - very cool stuff here
date_str_list_tmp = candlestick_df.Date.tolist()

candlestick_df['Date'] = [mdates.date2num(dt.datetime.strptime(d, '%m/%d/%Y').date()) for d in date_str_list_tmp]
# tmp_list = [d for d in candlestick_df.Date.tolist()]
# print ("Tmp List is ", tmp_list)
print ("Candlestick Dataframe is ",candlestick_df)

MA_Price_200_list = candlestick_df.MA_Price_200_day.tolist()
MA_Price_50_list = candlestick_df.MA_Price_50_day.tolist()
MA_Price_20_list = candlestick_df.MA_Price_20_day.tolist()
MA_Price_10_list = candlestick_df.MA_Price_10_day.tolist()
MA_volume_50_list = candlestick_df.MA_Volume_50_day.tolist()


quotes = [tuple(x) for x in candlestick_df[['Date', 'Open', 'High', 'Low', 'Close']].values]
date_list_tmp = candlestick_df.Date.tolist()
volume = candlestick_df.Volume.tolist()
print ("The type of quotes is",quotes)
print ("The type of volume is",volume)

# Todo :
# 1. Only one should have the x axis displayed
# 2. Volume ticks should be viewed on the left
# 3. Price ticks should be viiewed on the left
# 4. How to set the range for Price chart (probably same as the main chart)
# 5. Volume ticks should be written in Million or 100,000s
# 6. Is it possible to change the color of the bars based on up day or down day?
# 7. Make the price chart taller than the volume chart
fig=plt.figure()
ax1 = plt.subplot(211)
ax2 = plt.subplot(212, sharex = ax1)

candlestick_ohlc(ax1, quotes[0:100], width=0.6, colorup='g', colordown='r');
ax1.plot(date_list_tmp[0:100],MA_Price_200_list[0:100], color = 'black', label = 'SMA200')
ax1.plot(date_list_tmp[0:100],MA_Price_50_list[0:100], color = 'blue', label = 'SMA50')
ax1.plot(date_list_tmp[0:100],MA_Price_20_list[0:100], color = 'green', label = 'SMA20')
ax1.plot(date_list_tmp[0:100],MA_Price_10_list[0:100], color = 'pink', label = 'SMA10')

ax1.set_title('MEDP')
ax1.set_ylabel('Price')
ax1.grid(True)
ax1.xaxis_date()
plt.bar(date_list_tmp[0:100], volume[0:100], width=0.5)
ax2.plot(date_list_tmp[0:100],MA_volume_50_list[0:100], color = 'pink', label = 'SMA10')
ax2.set_ylabel('volume')
ax2.grid(True)
ax2.autoscale_view()
plt.setp(plt.gca().get_xticklabels(), rotation=30)
# plt.savefig('mpl_finance-apple.png')
plt.show()
