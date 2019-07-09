import pandas as pd
import json
from pprint import pprint
import matplotlib.pyplot as plt
from matplotlib.offsetbox import AnchoredText
from matplotlib.widgets import TextBox
import matplotlib.offsetbox as offsetbox
import numpy as np
import datetime as dt
from random import randint

from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()

historical_df = pd.read_csv("Plot_Experiment.csv")
# print ("The Historical df is \n", historical_df)
date_str_list = historical_df.Date.tolist()
# print ("The date list from historical df is ", date_str_list)
tmp_list = date_str_list[:1000]
date_str_list = tmp_list
# Truncate the datelist to 50 entries

date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in date_str_list]
# print ("The date list for historical is ", date_list, "\nit has ", len(date_list), " entries")

y = []
for i in range(len(date_str_list)):
  y.append(randint(2,2500))

yr_dates = pd.date_range(pd.to_datetime(date_str_list[len(date_str_list)-1]),
                   pd.to_datetime(date_str_list[0]) + pd.offsets.QuarterBegin(1), freq='Y')
# print (yr_dates)

qtr_dates = pd.date_range(pd.to_datetime(date_str_list[len(date_str_list)-1]),
                   pd.to_datetime(date_str_list[0]) + pd.offsets.QuarterBegin(1), freq='Q')
      # .strftime('%B %Y')
      # .tolist())
# print (qtr_dates)

yr_dates = pd.date_range(date_list[len(date_list)-1], date_list[0], freq='Y')
qtr_dates = pd.date_range(date_list[len(date_list)-1], date_list[0], freq='Q')
print ("Yearly Dates are ", yr_dates)
print ("Quarterly Dates are ", qtr_dates)

qtr_dates_df = pd.DataFrame(qtr_dates)
print ("Quarterly Dates Datafram is ", qtr_dates_df)

qtr_dates_tmp = []
yr_dates_tmp = []
for x in qtr_dates:
  print ("The original Quarterly Date is :", x)
  if (x.is_year_end is True):
    print("This quarter is also year end date. Removing ", type(x))
  if (x in yr_dates):
    print ("This quarter is also year end date. Removing ",type(x))
  else:
    qtr_dates_tmp.append(x.date().strftime('%m/%d/%Y'))

for x in yr_dates:
  print ("The original Yearly Date is :", x)
  yr_dates_tmp.append(x.date().strftime('%m/%d/%Y'))


print ("The modified qtr dates list is: ", qtr_dates)
print ("The modified qtr dates list is: ", qtr_dates_tmp)
print ("The modified yr dates list is: ", yr_dates_tmp)
# print ("Y is :", y)
# =============================================================================
# How to put the ticks and ticklabels
# =============================================================================
ax = plt.axes()
number = 217
title_str = "This is title number: " + r"$\bf{" + str(number) + "}$" +", And I am loving it"
plt.title(title_str)

ax.set_xticks(yr_dates,minor=False)
ax.set_xticks(qtr_dates_tmp, minor=True)
ax.xaxis.set_tick_params(width=5)
ax.set_xticklabels(yr_dates_tmp, rotation = 30,  fontsize=7,color='blue',minor=False)
ax.set_xticklabels(qtr_dates_tmp, rotation = 30,  fontsize=7,minor=True)
ax.grid(which='major', axis='x',linestyle='-',color='black',linewidth=1.5)
ax.grid(which='minor', linestyle='--',color='blue')
ax.grid(which='major', axis='y',linestyle='--',color='green',linewidth=1)
# =============================================================================



ax.set_yscale('linear')

# =============================================================================
# How to put acnhored text
# =============================================================================
number_of_anchored_texts = 3
for i in range(number_of_anchored_texts):
  if (i == 0):
    location = 9
    my_text = "This is a dummy comment for text box #0 \nAnything can be put here"
  elif (i == 1):
    location = 6
    my_text = "Test for Box number 2"
  else:
    location = 4
    my_text = "What do you want me to put here?"
  # a_text=offsetbox.AnchoredText(my_text, loc=location)
  a_text = AnchoredText(my_text, loc=location)
  ax.add_artist(a_text)
# =============================================================================

# Plot the main plot
plt.plot(date_list,y,label='XYZ',color="brown",linestyle='-')

# =============================================================================
# how to get legend outside of axes
# ax.legend(loc='lower left', bbox_to_anchor= (0.0, 1.01), ncol=2, borderaxespad=0, frameon=False)
# plt.legend(bbox_to_anchor=(0,1.01), loc="lower left", borderaxespad=0,fontsize = 'x-small')
plt.legend(bbox_to_anchor=(1.01,0), loc="lower left", borderaxespad=0,fontsize = 'x-small')
# =============================================================================

# Annotate outside the plot
plt.annotate('...Additional information...',
            xy=(0, 0), xytext=(0, 0),
            xycoords=('axes fraction', 'figure fraction'),
            textcoords='offset points',
            size=10, ha='left', va='bottom')


plt.annotate('...More Additional information...',
            xy=(1, 0), xytext=(0, 0),
            xycoords=('axes fraction', 'figure fraction'),
            textcoords='offset points',
            size=10, ha='right', va='bottom')


#  All of these work but it seems like a pain to get their sizes and locations correct
# # 1st number controls if the box is towards left
# # 2nd number contorls the up-down position of the box
# # the 3rd number controls the length of the box
# # the 4th number controls the height of the box
# axbox_0 = plt.axes([0.1, 0.05, 0.8, 0.075])
# tb_0 = TextBox(axbox_0, "Name:", initial="Jane Doe")
# tb_0.label.set_color('red')      # label color
# tb_0.text_disp.set_color('blue') # text inside the edit box
#
# axbox_1 = plt.axes([0,.1, .1, .75])
# tb_1 = TextBox(axbox_1, "Name:", initial="Joe Smith")
# tb_1.label.set_color('blue')      # label color
# tb_1.text_disp.set_color('red') # text inside the edit box

# plt.figure(figsize=(16,10))
# plt.tight_layout()
plt.show()