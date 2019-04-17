import pandas
import matplotlib
import datetime as dt
import numpy as np
import matplotlib.pyplot as plt



fig, ax1 = plt.subplots()
t = np.arange(0.01, 10.0, 0.01) # Returns a numpy.ndarray

s1 = np.exp(t) # Returns numpy.ndarray
ax1.plot(t, s1, 'b-') # Plots blue with solid line
ax1.set_xlabel('time (s)')
# Make the y-axis label, ticks and tick labels match the line color.
ax1.set_ylabel('exp', color='b')
ax1.tick_params('y', colors='b')

ax2 = ax1.twinx() # Create a twin Axes sharing the xaxis
s2 = np.sin(2 * np.pi * t)
ax2.plot(t, s2, 'r.')
ax2.set_ylabel('sin', color='r')
ax2.tick_params('y', colors='r')

fig.tight_layout()
plt.show()


'''
Somehow reading with col_names did not work??
# col_names = ["Date", "Open", "High", "Low", "Close", "Adj_Close", "Volume"]
# stock_historical = pandas.read_csv('AMZN_historical.csv', names=col_names)
'''

stock_historical = pandas.read_csv('AAPL_historical.csv')
col_list = stock_historical.columns.tolist()
# print (col_list)
# print (stock_historical)
date_str_list = stock_historical.Date.tolist()
adj_close_list = stock_historical.Adj_Close.tolist()

# print (date_str_list)
# print (adj_close_list)

# There is no need to delete the first element now
del date_str_list[0]
del adj_close_list[0]

print (date_str_list)
print (adj_close_list)


date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in date_str_list]


# ax.yaxis.set_label_position("right")

plt.plot(date_list,adj_close_list)


plt.show()


# ----------------------------------------------------------------------------------------------------
# Get the Earnings
# ----------------------------------------------------------------------------------------------------

stock_earnings = pandas.read_csv('AAPL_earnings.csv')
earnings_col_list = stock_earnings.columns.tolist()
print (earnings_col_list)

earnings_date_str_list = stock_earnings.Date.tolist()
earnings_list = stock_earnings.Q_EPS.tolist()

print (earnings_date_str_list)
print (earnings_list)

del earnings_date_str_list[0]
del earnings_list[0]

earnings_date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in earnings_date_str_list]



plt.scatter(earnings_date_list,earnings_list)
plt.grid(which='major')

plt.show

# ----------------------------------------------------------------------------------------------------

plt.figure(figsize=(3,2))

x = np.linspace(-np.pi, np.pi,300)
C,S = np.cos(x),np.sin(x)

plt.plot(x,C)
plt.plot(x,S)

plt.show()
