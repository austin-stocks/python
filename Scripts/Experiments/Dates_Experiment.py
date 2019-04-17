import pandas as pd
import matplotlib
import datetime as dt
import numpy as np
import matplotlib.pyplot as plt


stock_market_calendar = pd.read_csv('Calendar.csv')
print ("The type of Calendar is ", type(stock_market_calendar))
# print ("The Stock Market Calendar is ", stock_market_calendar)
years_list = stock_market_calendar.columns.tolist()
print ("The Columns are ", years_list)

# This code will put the individual columns in series
for year in years_list:
  # print  ("The Calendar for year ", year, "is\n", stock_market_calendar.loc[:,year], " ", type(stock_market_calendar.loc[:,year]))
  cal_year_series = "cal_"+year

  cal_year_series = stock_market_calendar.loc[:,year]
  print ("The Calendar for ", year , " is \n", cal_year_series)

# Now look for a date
for i, v in cal_year_series.items():
  print ("Index ", i, "Value ", v, "Type of value ", type(v))


# This works
date = dt.datetime(1971, 1, 1)
dates = [dt.datetime(1969, 12, 31), dt.datetime(1970, 1, 1),  dt.datetime(1970, 1, 2), dt.datetime(1970, 1, 3)]
match_date = min(dates, key=lambda d: abs(d - date))
print ("The matching date is ", match_date)