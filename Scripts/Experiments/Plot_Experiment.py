import pandas as pd
import json
from pprint import pprint
import matplotlib.pyplot as plt
import numpy as np
import datetime as dt
from random import randint

from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()

historical_df = pd.read_csv("Plot_Experiment.csv")
# print ("The Historical df is \n", historical_df)
date_str_list = historical_df.Date.tolist()
# print ("The date list from historical df is ", date_str_list)
tmp_list = date_str_list[:400]
date_str_list = tmp_list
# Truncate the datelist to 50 entries

date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in date_str_list]
# print ("The date list for historical is ", date_list, "\nit has ", len(date_list), " entries")

y = []
for i in range(len(date_str_list)):
  y.append(randint(2,2500))

yr_dates = pd.date_range(pd.to_datetime(date_str_list[len(date_str_list)-1]),
                   pd.to_datetime(date_str_list[0]) + pd.offsets.QuarterBegin(1), freq='Y')
print (yr_dates)

qtr_dates = pd.date_range(pd.to_datetime(date_str_list[len(date_str_list)-1]),
                   pd.to_datetime(date_str_list[0]) + pd.offsets.QuarterBegin(1), freq='Q')
      # .strftime('%B %Y')
      # .tolist())
print (qtr_dates)

yr_dates = pd.date_range(date_list[len(date_list)-1], date_list[0], freq='Y')
qtr_dates = pd.date_range(date_list[len(date_list)-1], date_list[0], freq='Q')
print ("Yearly Dates are ", yr_dates)
print ("Quarterly Dates are ", qtr_dates)

qtr_dates_tmp = []
yr_dates_tmp = []
for x in qtr_dates:
  print ("The original Quarterly Date is :", x)
  qtr_dates_tmp.append(x.date().strftime('%m/%d/%Y'))
for x in yr_dates:
  print ("The original Yearly Date is :", x)
  yr_dates_tmp.append(x.date().strftime('%m/%d/%Y'))

print ("The modifed qtr dates list is: ", qtr_dates_tmp)
# print ("Y is :", y)
ax = plt.axes()
ax.set_xticks(yr_dates)
ax.set_xticks(qtr_dates, minor=True)
ax.set_xticklabels(yr_dates_tmp, rotation = 15, minor=False)
ax.set_xticklabels(qtr_dates_tmp, rotation = 15, minor=True)
ax.grid(which='major', linestyle='-')
ax.grid(which='minor', linestyle='--',color='blue')

ax.set_yscale('linear')
plt.plot(date_list,y,color="brown",linestyle='-')

plt.show()