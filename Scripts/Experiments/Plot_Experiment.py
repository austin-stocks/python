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
print ("The Historical df is \n", historical_df)
date_str_list = historical_df.Date.tolist()
print ("The date list from historical df is ", date_str_list)
tmp_list = date_str_list[:400]
date_str_list = tmp_list
# Truncate the datelist to 50 entries

date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in date_str_list]
print ("The date list for historical is ", date_list, "\nit has ", len(date_list), " entries")

y = []
for i in range(len(date_str_list)):
  y.append(randint(2,20))

print ("Y is :", y)

plt.plot(date_list,y,color="brown",linestyle='-')
plt.show()