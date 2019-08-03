import pandas as pd
from mpl_finance import candlestick_ohlc
import matplotlib

# matplotlib.use('Agg')  # Bypass the need to install Tkinter GUI framework
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Avoid FutureWarning: Pandas will require you to explicitly register matplotlib converters.
from pandas.plotting import register_matplotlib_converters

register_matplotlib_converters()

# Load data from CSV file.
##########################
my_headers = ['date', 'open', 'high', 'low', 'close', 'volume']
my_dtypes = {'date': 'str', 'open': 'float', 'high': 'float', 'low': 'float',
             'close': 'float', 'volume': 'int'}
my_parse_dates = ['date']
loaded_data = pd.read_csv('AAPL_Historical.csv', sep=',', header=1, names=my_headers,
                          dtype=my_dtypes, parse_dates=my_parse_dates)

# Convert 'Timestamp' to 'float'.
#   candlestick_ohlc needs time to be in float days format - see date2num().
loaded_data['date'] = [mdates.date2num(d) for d in loaded_data['date']]

# Re-arrange data so that each row contains values of a day: 'date','open','high','low','close'.
quotes = [tuple(x) for x in loaded_data[['date', 'open', 'high', 'low', 'close']].values]

# Plot candlestick.
##########################
fig, ax = plt.subplots()
candlestick_ohlc(ax, quotes, width=0.5, colorup='g', colordown='r');

# Customize graph.
##########################
plt.xlabel('Date')
plt.ylabel('Price')
plt.title('Apple')

# Format time.
ax.xaxis_date()
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))

plt.gcf().autofmt_xdate()  # Beautify the x-labels
plt.autoscale(tight=False)


# Save graph to file.
plt.savefig('mpl_finance-apple.png')
plt.show()

'''
From yet another 
from matplotlib.finance import *

data = parse_yahoo_historical(fetch_historical_yahoo('CKSW', (2013,1,1), (2013, 6, 1)))

ds, opens, closes, highs, lows, volumes = zip(*data)

# Create figure
fig = plt.figure()
ax1 = fig.add_subplot(111)
# Plot the candlestick
candles = candlestick2(ax1, opens, closes, highs, lows,
                       width=1, colorup='g')

# Add a seconds axis for the volume overlay
ax2 = ax1.twinx()

# Plot the volume overlay
bc = volume_overlay(ax2, opens, closes, volumes, colorup='g', alpha=0.5, width=1)
ax2.add_collection(bc)
plt.show()
'''

'''
From another answer to share the candles and volume
ax1 = plt.subplot2grid((6,1), (0,0), rowspan=5, colspan=1)
ax2 = plt.subplot2grid((6,1), (5,0), rowspan=1, colspan=1, sharex=ax1)
'''


'''
https://www.techtrekking.com/author/pravin/page/11/

################################################################################################
#	name:	timeseries_OHLC_with_SMA.py
#	desc:	creates OHLC graph with overlay of simple moving averages
#	date:	2018-06-15
#	Author:	conquistadorjd
################################################################################################
import pandas as pd
# import pandas_datareader as datareader
import matplotlib.pyplot as plt
import datetime
from matplotlib.finance import candlestick_ohlc
# from mpl_finance import candlestick_ohlc
import matplotlib.dates as mdates

print('*** Program Started ***')

df = pd.read_csv('15-06-2016-TO-14-06-2018HDFCBANKALLN.csv')

# ensuring only equity series is considered
df = df.loc[df['Series'] == 'EQ']

# Converting date to pandas datetime format
df['Date'] = pd.to_datetime(df['Date'])
df["Date"] = df["Date"].apply(mdates.date2num)

# Creating required data in new DataFrame OHLC
ohlc= df[['Date', 'Open Price', 'High Price', 'Low Price','Close Price']].copy()
# In case you want to check for shorter timespan
# ohlc =ohlc.tail(60)
ohlc['SMA50'] = ohlc["Close Price"].rolling(50).mean()


f1, ax = plt.subplots(figsize = (10,5))

# plot the candlesticks
candlestick_ohlc(ax, ohlc.values, width=.6, colorup='green', colordown='red')
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

# Creating SMA columns
ohlc['SMA5'] = ohlc["Close Price"].rolling(5).mean()
ohlc['SMA10'] = ohlc["Close Price"].rolling(10).mean()
ohlc['SMA20'] = ohlc["Close Price"].rolling(20).mean()
ohlc['SMA50'] = ohlc["Close Price"].rolling(50).mean()
ohlc['SMA100'] = ohlc["Close Price"].rolling(100).mean()
ohlc['SMA200'] = ohlc["Close Price"].rolling(200).mean()

#Plotting SMA columns
# ax.plot(ohlc['Date'], ohlc['SMA5'], color = 'blue', label = 'SMA5')
# ax.plot(ohlc['Date'], ohlc['SMA10'], color = 'blue', label = 'SMA10')
# ax.plot(ohlc['Date'], ohlc['SMA20'], color = 'blue', label = 'SMA20')
ax.plot(ohlc['Date'], ohlc['SMA50'], color = 'green', label = 'SMA50')
# ax.plot(ohlc.index, df['SMA100'], color = 'blue', label = 'SMA100')
ax.plot(ohlc['Date'], ohlc['SMA200'], color = 'blue', label = 'SMA200')

# Saving image
plt.savefig('OHLC with SMA HDFC.png')

# In case you dont want to save image but just displya it

# ohlc.to_csv('ohlc.csv')
# plt.show()
print('*** Program ended ***')








import numpy as np
import matplotlib
import matplotlib.pyplot as plt
# from matplotlib.finance import candlestick
# from matplotlib.finance import volume_overlay3
# finance module is no longer part of matplotlib
# see: https://github.com/matplotlib/mpl_finance
from mpl_finance import candlestick_ochl as candlestick
from mpl_finance import volume_overlay3
from matplotlib.dates import num2date
from matplotlib.dates import date2num
import matplotlib.mlab as mlab
import datetime
import pandas as pd
import matplotlib

matplotlib.use('Agg')  # Bypass the need to install Tkinter GUI framework
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Avoid FutureWarning: Pandas will require you to explicitly register matplotlib converters.
from pandas.plotting import register_matplotlib_converters

register_matplotlib_converters()


datafile = 'data.csv'
# r = mlab.csv2rec(datafile, delimiter=';')
r = pd.read_csv('data.csv', delimiter=';')
print ("Read file is : ",r)

# the dates in my example file-set are very sparse (and annoying) change the dates to be sequential
# for i in range(len(r)-1):
#     r['date'][i+1] = r['date'][i] + datetime.timedelta(days=1)
# candlesticks = zip(date2num(r['date']),r['open'],r['close'],r['max'],r['min'],r['volume'])

r['date'] = [mdates.date2num(d) for d in r['date']]
candlesticks = [tuple(x) for x in r[['date','open','high','low','close']].values]

fig = plt.figure()
ax = fig.add_subplot(1,1,1)


ax.set_ylabel('Quote ($)', size=20)
candlestick(ax, candlesticks,width=1,colorup='g', colordown='r')

# shift y-limits of the candlestick plot so that there is space at the bottom for the volume bar chart
pad = 0.25
yl = ax.get_ylim()
ax.set_ylim(yl[0]-(yl[1]-yl[0])*pad,yl[1])

# create the second axis for the volume bar-plot
ax2 = ax.twinx()


# set the position of ax2 so that it is short (y2=0.32) but otherwise the same size as ax
ax2.set_position(matplotlib.transforms.Bbox([[0.125,0.1],[0.9,0.32]]))

# get data from candlesticks for a bar plot
dates = [x[0] for x in candlesticks]
dates = np.asarray(dates)
volume = [x[5] for x in candlesticks]
volume = np.asarray(volume)

# make bar plots and color differently depending on up/down for the day
pos = r['open']-r['close']<0
neg = r['open']-r['close']>0
ax2.bar(dates[pos],volume[pos],color='green',width=1,align='center')
ax2.bar(dates[neg],volume[neg],color='red',width=1,align='center')

#scale the x-axis tight
ax2.set_xlim(min(dates),max(dates))
# the y-ticks for the bar were too dense, keep only every third one
yticks = ax2.get_yticks()
ax2.set_yticks(yticks[::3])

ax2.yaxis.set_label_position("right")
ax2.set_ylabel('Volume', size=20)

# format the x-ticks with a human-readable date.
xt = ax.get_xticks()
new_xticks = [datetime.date.isoformat(num2date(d)) for d in xt]
ax.set_xticklabels(new_xticks,rotation=45, horizontalalignment='right')

plt.ion()
plt.show()
'''