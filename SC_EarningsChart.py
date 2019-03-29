import pandas as pd
import matplotlib
import os
import math
import datetime as dt
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.offsetbox import AnchoredText

from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()
# =============================================================================
# User defined function
# This function takes in a list that has nan in between numeric values and
# replaces the nan in the middle with a step so that the 'markers' can be
#  converted to a line while plotting
# # =============================================================================
def smooth_list (l):

  i_int = 0
  l_mod = l.copy()
  l_clean = []
  l_indices = []

  while (i_int < len(l) - 1):
    if (str(l_mod[i_int]) != 'nan'):
      l_clean.append(l[i_int])
      l_indices.append(i_int)

    i_int += 1

  print ("The original List is ", l)
  print("The clean List is ", l_clean)
  print("The indices of non non values is ", l_indices)

  i_int = 0
  while (i_int < len(l_clean) - 1):
    print("Clean List index:", i_int, ", Clean List value:", l_clean[i_int], ", Corresponding List index:", l_indices[i_int])
    step = (l_clean[i_int] - l_clean[i_int + 1]) / (l_indices[i_int + 1] - l_indices[i_int])
    start_index = l_indices[i_int]
    stop_index = l_indices[i_int + 1]
    print("The step is ", step, "Start and Stop Indices are ", start_index, stop_index)
    j_int = start_index + 1
    while (j_int < stop_index):
      l_mod[j_int] = float(l_mod[j_int - 1]) - step
      print("Updating index", j_int, "to ", l_mod[j_int])
      j_int += 1

    i_int += 1

  print("Modified List is", l_mod)
  return (l_mod)
# =============================================================================


# =============================================================================
# Define the various filenames and Directory Paths to be used
# =============================================================================
dir_path = os.getcwd()
user_dir = "User Files"
chart_dir = "Charts"
historical_dir = "Historical"
earnings_dir= "Earnings"
log_dir = "Logs"
tracklist_file = "Tracklist.csv"
tracklist_file_full_path = dir_path + "\\" + user_dir + "\\" + tracklist_file
yahoo_hist_in_dir = dir_path + "\\Download\YahooHistorical"
yahoo_hist_out_dir = dir_path + "\\Historical"
# =============================================================================



# todo : Should read from the Tracklist file and save the charts in the charts directory
ticker = "MU"

# Open the Log file in write mode
logfile = dir_path + "\\" + log_dir + "\\" + ticker + "_log.csv"

# =============================================================================
# Read the Earnings file for the ticker
# =============================================================================
qtr_eps_df = pd.read_csv(dir_path + "\\" + earnings_dir + "\\" + ticker + "_earnings.csv")
print ("The Earnings df is \n", qtr_eps_df)
# Todo : Error out if any elements in the date_list are nan except the trailing (this includes
# Todo : leading nan and any nan in the list itself
qtr_eps_date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in qtr_eps_df.Date.dropna().tolist()]
qtr_eps_list = qtr_eps_df.Q_EPS.tolist()
print ("The date list for qtr_eps is ", qtr_eps_date_list, "\nand the number of elements are", len(qtr_eps_date_list))
print ("The Earnings list for qtr_eps is ", qtr_eps_list)

# Set the length of qtr_eps_list to same as date_list...this gets rid of nan at the end
# of the qtr_eps_list
len_qtr_eps_date_list = len(qtr_eps_date_list)
len_qtr_eps_list = len(qtr_eps_list)
if (len_qtr_eps_date_list < len_qtr_eps_list):
  del qtr_eps_list[len_qtr_eps_date_list:]
print ("The Earnings list for qtr_eps is ", qtr_eps_list)

# Check if now the qtr_eps_list still has any undefined elements...flag an error and exit
# This will indicate any empty cells are either the beginning or in the middle of the eps
# column in the csv
# todo : Get this as proper python exception
if (sum(math.isnan(x) for x in qtr_eps_list) > 0):
  print ("ERROR : There are some undefined EPS numbers in the Earnings file, Please correct and rerun")
  exit()

# So - if we are successful till this point - we have made sure that
# 1. There are no nan in the date list (todo : This needs to be done)
# 2. There are no nan in the eps list
# 3. Number of elements in the qtr_eps_date_list are equal to the number of
#    element in the qtr_eps_list
# =============================================================================

# =============================================================================
# Read the Historical file for the ticker
# =============================================================================
historical_df = pd.read_csv(dir_path + "\\" + historical_dir + "\\" + ticker + "_historical.csv")
print ("The Historical df is \n", historical_df)
adj_close_list = historical_df.Adj_Close.tolist()
date_str_list = historical_df.Date.tolist()
print ("The date list from historical df is ", date_str_list)
date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in date_str_list]
print ("The date list for historical is ", date_list, "\nit has ", len(date_list), " entries")
# =============================================================================

# ===================================================================================================
# Create the Annual EPS list from the Quarter EPS list.
# The last 3 elemnts of the annual EPS are going to be blank because the last annual EPS corresponds
# the the last but 4th Quarter EPS
# ===================================================================================================
i_int = 0
yr_eps_list = list()
while (i_int < (len(qtr_eps_list)-3)):
  annual_average_eps = (qtr_eps_list[i_int] +     \
                        qtr_eps_list[i_int + 1] + \
                        qtr_eps_list[i_int + 2] + \
                        qtr_eps_list[i_int + 3])/4

  print ("Iteration #, ", i_int, " Quartely EPS, Annual EPS", \
                                                  qtr_eps_list[i_int], \
                                                  qtr_eps_list[i_int+1],\
                                                  qtr_eps_list[i_int+2],\
                                                  qtr_eps_list[i_int+3], \
                                                  annual_average_eps)
  yr_eps_list.append(annual_average_eps)
  i_int += 1
print ("Annual EPS List ", yr_eps_list, "\nand the number of elements are", len(yr_eps_list))
yr_eps_list_tmp = yr_eps_list
yr_eps_list_tmp.append('Not_calculated')
yr_eps_list_tmp.append('Not_calculated')
yr_eps_list_tmp.append('Not_calculated')

# print ("The Earnings DF is ", earnings_df)
earnings_df = pd.DataFrame(np.column_stack([qtr_eps_date_list, qtr_eps_list, yr_eps_list_tmp]),
                               columns=['Date', 'Q EPS', 'Annual EPS'])
earnings_df.to_csv(logfile)
# ===================================================================================================


# =============================================================================
# Create a qtr_eps_expanded list
# We are here trying to create the list that has the same number of elements
# as the historical date_list and only the elements that have the Quarter EPS
# have valid values, other values in the expanded list are nan
# =============================================================================
qtr_eps_expanded_list = []
for i in range(len(date_list)):
  # 17th march : sundeep was here
  # qtr_eps_expanded_list.append(str('nan'))
  qtr_eps_expanded_list.append(float('nan'))

for qtr_eps_date in qtr_eps_date_list:
  curr_index = qtr_eps_date_list.index(qtr_eps_date)
  print ("Looking for ", qtr_eps_date)
  match_date = min(date_list, key=lambda d: abs(d - qtr_eps_date))
  print ("The matching date is ", match_date, " at index ",date_list.index(match_date))
  qtr_eps_expanded_list[date_list.index(match_date)] = qtr_eps_list[curr_index]

print ("The expanded qtr eps list is ", qtr_eps_expanded_list, "\nand the number of elements are", len(qtr_eps_expanded_list))
# =============================================================================

# =============================================================================
# Create annual eps date list and then create
# Expanded annual EPS list just like the expanded Quarter EPS list was created
# However the expanded Annual EPS list is really three lists...to create a different
# series in the plot/graph later
# yr_eps_expanded_list
# annual_past_eps_expanded_list - contains
# annual_projected_eps_expanded_list
# =============================================================================
# Remove the last 3 dates from the qtr_eps_date_list to create yr_eps_date_list
yr_eps_date_list = qtr_eps_date_list[0:len(qtr_eps_date_list)-3]

yr_eps_expanded_list = []
annual_past_eps_expanded_list = []
annual_projected_eps_expanded_list = []
for i in range(len(date_list)):
  yr_eps_expanded_list.append(float('nan'))
  annual_past_eps_expanded_list.append(float('nan'))
  annual_projected_eps_expanded_list.append(float('nan'))

for yr_eps_date in yr_eps_date_list:
  curr_index = yr_eps_date_list.index(yr_eps_date)
  print ("Looking for ", yr_eps_date)
  match_date = min(date_list, key=lambda d: abs(d - yr_eps_date))
  print ("The matching date is ", match_date, " at index ",date_list.index(match_date))
  yr_eps_expanded_list[date_list.index(match_date)] = yr_eps_list[curr_index]
  # Check if the matching data is in the past or in the future
  if (match_date < dt.date.today()):
    print ("The matching date is in the past")
    annual_past_eps_expanded_list[date_list.index(match_date)] = yr_eps_list[curr_index]
  else:
    print ("The matching date is in the future")
    annual_projected_eps_expanded_list[date_list.index(match_date)] = yr_eps_list[curr_index]
# =============================================================================



# todo : Needs to be gotten from config file
date_for_yr_eps_growth_projection = ""
growth_proj_start_index = 14

yr_eps_02_5_growth_list = []
yr_eps_05_0_growth_list = []
yr_eps_10_0_growth_list = []
yr_eps_20_0_growth_list = []
for i in range(len(yr_eps_date_list)):
  yr_eps_02_5_growth_list.append(float('nan'))
  yr_eps_05_0_growth_list.append(float('nan'))
  yr_eps_10_0_growth_list.append(float('nan'))
  yr_eps_20_0_growth_list.append(float('nan'))

yr_eps_02_5_growth_list[growth_proj_start_index] = yr_eps_list[growth_proj_start_index]
yr_eps_05_0_growth_list[growth_proj_start_index] = yr_eps_list[growth_proj_start_index]
yr_eps_10_0_growth_list[growth_proj_start_index] = yr_eps_list[growth_proj_start_index]
yr_eps_20_0_growth_list[growth_proj_start_index] = yr_eps_list[growth_proj_start_index]

for i in reversed(range(0, growth_proj_start_index)):
  print ("Updating for index", i)
  yr_eps_02_5_growth_list[i] = 1.025*float(yr_eps_02_5_growth_list[i+1])
  yr_eps_05_0_growth_list[i] = 1.05*float(yr_eps_05_0_growth_list[i+1])
  yr_eps_10_0_growth_list[i] = 1.10*float(yr_eps_10_0_growth_list[i+1])
  yr_eps_20_0_growth_list[i] = 1.20*float(yr_eps_20_0_growth_list[i+1])

print ("The Annual eps list", yr_eps_list)
print ("The 2.5% growth rate eps list", yr_eps_02_5_growth_list)
print ("The   5% growth rate eps list", yr_eps_05_0_growth_list)
print ("The  10% growth rate eps list", yr_eps_10_0_growth_list)
print ("The  20% growth rate eps list", yr_eps_20_0_growth_list)


yr_eps_02_5_growth_expanded_list_unsmooth = []
yr_eps_05_0_growth_expanded_list_unsmooth = []
yr_eps_10_0_growth_expanded_list_unsmooth = []
yr_eps_20_0_growth_expanded_list_unsmooth = []
for i in range(len(date_list)):
  yr_eps_02_5_growth_expanded_list_unsmooth.append(float('nan'))
  yr_eps_05_0_growth_expanded_list_unsmooth.append(float('nan'))
  yr_eps_10_0_growth_expanded_list_unsmooth.append(float('nan'))
  yr_eps_20_0_growth_expanded_list_unsmooth.append(float('nan'))


for yr_eps_date in yr_eps_date_list:
  curr_index = yr_eps_date_list.index(yr_eps_date)
  print ("Looking for ", yr_eps_date)
  match_date = min(date_list, key=lambda d: abs(d - yr_eps_date))
  print ("The matching date is ", match_date, " at index ",date_list.index(match_date))
  yr_eps_02_5_growth_expanded_list_unsmooth[date_list.index(match_date)] = yr_eps_02_5_growth_list[curr_index]
  yr_eps_05_0_growth_expanded_list_unsmooth[date_list.index(match_date)] = yr_eps_05_0_growth_list[curr_index]
  yr_eps_10_0_growth_expanded_list_unsmooth[date_list.index(match_date)] = yr_eps_10_0_growth_list[curr_index]
  yr_eps_20_0_growth_expanded_list_unsmooth[date_list.index(match_date)] = yr_eps_20_0_growth_list[curr_index]

yr_eps_02_5_growth_expanded_list = smooth_list(yr_eps_02_5_growth_expanded_list_unsmooth)
yr_eps_05_0_growth_expanded_list = smooth_list(yr_eps_05_0_growth_expanded_list_unsmooth)
yr_eps_10_0_growth_expanded_list = smooth_list(yr_eps_10_0_growth_expanded_list_unsmooth)
yr_eps_20_0_growth_expanded_list = smooth_list(yr_eps_20_0_growth_expanded_list_unsmooth)




# =============================================================================
# Read the config file and decide all the parms that are needed for plot
# =============================================================================
config_df = pd.read_csv(user_dir + "\\Configurations.csv")
config_df.set_index('Ticker', inplace=True)
print ("The configuration df", config_df)
if ticker in config_df.index:
  ticker_config_series = config_df.loc[ticker]
  print("Then configurations for ", ticker, " is ", ticker_config_series)
else:
  # Todo : Create a default series with all nan so that it can be cleaned up in the next step
  print("Configuration Entry for ", ticker, " not found...continuing with default values")

# ---------------------------------------------------------
# Find out how many years need to be plotted
# ---------------------------------------------------------
# todo : what if someone puts a string like "Max" in there?
if (math.isnan(ticker_config_series['Linear Chart Years'])):
  plot_period_int = 252 * 10
  print("Will Plot the Chart for 10 years")
else:
  print("Will Plot the Chart for ", int(ticker_config_series['Linear Chart Years']), " years")
  plot_period_int = 252*int(ticker_config_series['Linear Chart Years'])
# ---------------------------------------------------------


# ---------------------------------------------------------
# Get the upper and lower guide lines separation from the annual EPS
# ---------------------------------------------------------
# todo : what if the eps is negative then the multiplication makes it more negative
if (math.isnan(ticker_config_series['Upper Price Channel'])):
  guide_line_upper_list_unsmooth = [float(eps)+ .5*float(eps) for eps in yr_eps_expanded_list]
else:
  upper_price_channel_separation = float(ticker_config_series['Upper Price Channel'])
  guide_line_upper_list_unsmooth = [float(eps)+ upper_price_channel_separation for eps in yr_eps_expanded_list]

if (math.isnan(ticker_config_series['Lower Price Channel'])):
  guide_line_lower_list_unsmooth = [float(eps) - .5*float(eps) for eps in yr_eps_expanded_list]
else:
  lower_price_channel_separation = float(ticker_config_series['Lower Price Channel'])
  guide_line_lower_list_unsmooth = [float(eps)- lower_price_channel_separation for eps in yr_eps_expanded_list]

guide_line_upper_list = smooth_list(guide_line_upper_list_unsmooth)
guide_line_lower_list = smooth_list(guide_line_lower_list_unsmooth)
print ("The upper Guide is ", guide_line_upper_list, "\nand the number of element is ", len(guide_line_upper_list))
print ("The upper Guide is ", guide_line_lower_list, "\nand the number of element is ", len(guide_line_lower_list))
# ---------------------------------------------------------


# ---------------------------------------------------------
# Create the lower and upper Price limit
# ---------------------------------------------------------
if (math.isnan(ticker_config_series['Price Scale - Low'])):
  price_lim_lower = 0
  print("Price Scale - Low is set to 0")
else:
  price_lim_lower = int(ticker_config_series['Price Scale - Low'])
  print("Price Scale - Low from Config file is ", price_lim_lower)

if (math.isnan(ticker_config_series['Price Scale - High'])):
  adj_close_list_nonan = [x for x in adj_close_list if math.isnan(x) is False]
  price_lim_upper = 1.25 * max(adj_close_list_nonan)
  print("Price Scale - High from historical adj_close_list is ", price_lim_upper)
else:
  price_lim_upper = int(ticker_config_series['Price Scale - High'])
  print("Price Scale - High from Config file is ", price_lim_upper)
# ---------------------------------------------------------

# ---------------------------------------------------------
# Create the Upper and Lower EPS Limit
# ---------------------------------------------------------
if (math.isnan(ticker_config_series['Earnings Scale - High'])):
  if (max(qtr_eps_list) > 0):
    qtr_eps_lim_upper = 1.25 * max(qtr_eps_list)
  else:
    qtr_eps_lim_upper = max(qtr_eps_list) / 1.25
  print("EPS Scale - Low from Earnings List is ", qtr_eps_lim_upper)
else:
  qtr_eps_lim_upper = ticker_config_series['Earnings Scale - High']
  print("EPS Scale - High from Config file ", qtr_eps_lim_upper)

if (math.isnan(ticker_config_series['Earnings Scale - Low'])):
  if (min(qtr_eps_list) < 0):
    qtr_eps_lim_lower = 1.25 * min(qtr_eps_list)
  else:
    qtr_eps_lim_lower = min(qtr_eps_list) / 1.25
  print("EPS Scale - Low from Earnings List is ", qtr_eps_lim_lower)
else:
  qtr_eps_lim_lower = ticker_config_series['Earnings Scale - Low']
  print("EPS Scale - Low from Config file ", qtr_eps_lim_lower)
# =============================================================================



# todo :
# Get the earnings projections line - 2.5% etc
# See how you can add comments
# Legends
# Minor grids
# Dividends
# What format the file should be save
# Get the code debug friendly
# How to create other subplots that have the book value etc
#   Maybe use subplots for it
# How to use earnings projections
# Move the annual two quarters over
# Test out the values from the file
# How to show values when you click

# #############################################################################
# ###########                    Now plot Everything                 ##########
# #############################################################################
fig, main_plt = plt.subplots()
fig.set_size_inches(12,8)
fig.subplots_adjust(right=0.75)
fig.autofmt_xdate()
main_plt.set_facecolor("lightgrey")
main_plt.set_title("Stock Chart for " + ticker)


# Various plots that share the same x axis(date)
price_plt = main_plt.twinx()
annual_past_eps_plt = main_plt.twinx()
annual_projected_eps_plt = main_plt.twinx()
upper_channel_plt = main_plt.twinx()
lower_channel_plt = main_plt.twinx()
yr_eps_02_5_plt = main_plt.twinx()
yr_eps_05_0_plt = main_plt.twinx()
yr_eps_10_0_plt = main_plt.twinx()
yr_eps_20_0_plt = main_plt.twinx()

print ("Type of fig ", type(fig), \
       "\nType of main_plt ", type(main_plt), \
       "\nType of price_plt: ", type(price_plt), \
       "\nType of yr_eps_plt: ", type(annual_past_eps_plt), \
       "\nType of upper_channel_plt: ", type(upper_channel_plt))
# -----------------------------------------------------------------------------
# Main Plot - This is the Q EPS vs Date
# -----------------------------------------------------------------------------
main_plt.set_xlabel('Date')
main_plt.set_ylabel('Q EPS')
main_plt.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
main_plt_inst = main_plt.plot(date_list[0:plot_period_int],qtr_eps_expanded_list[0:plot_period_int],label = 'Q EPS',color="deeppink",marker='.')
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Historical Price Plot
# -----------------------------------------------------------------------------
price_plt.set_ylabel('Price', color='k')
price_plt.set_ylim(price_lim_lower,price_lim_upper)
price_plt_inst = price_plt.plot(date_list[0:plot_period_int], adj_close_list[0:plot_period_int], label = 'Adj Close',color="brown",linestyle='-')
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Average Annual EPS Plot
# -----------------------------------------------------------------------------
annual_past_eps_plt.set_ylim(qtr_eps_lim_lower,qtr_eps_lim_upper)
annual_past_eps_plt.set_yticks([])
annual_past_eps_plt_inst = annual_past_eps_plt.plot(date_list[0:plot_period_int], annual_past_eps_expanded_list[0:plot_period_int], label = '4 qtrs/4',color="black",marker='D',markersize='4')
for i in range(len(yr_eps_date_list)):
  print ("The Date is ", yr_eps_date_list[i], " Corresponding EPS ", yr_eps_list[i])
  x = float("{0:.2f}".format(yr_eps_list[i]))
  main_plt.text(yr_eps_date_list[i],yr_eps_list[i],x,)
  # main_plt.text(yr_eps_date_list[i],yr_eps_list[i],x, bbox={'facecolor':'white'})


annual_projected_eps_plt.set_ylim(qtr_eps_lim_lower,qtr_eps_lim_upper)
annual_projected_eps_plt.set_yticks([])
annual_projected_eps_plt_inst = annual_projected_eps_plt.plot(date_list[0:plot_period_int], annual_projected_eps_expanded_list[0:plot_period_int], label = '4 qtrs/4',color="White",marker='D',markersize='4')

yr_eps_02_5_plt.set_ylim(qtr_eps_lim_lower,qtr_eps_lim_upper)
yr_eps_02_5_plt.set_yticks([])
yr_eps_02_5_plt_inst = yr_eps_02_5_plt.plot(date_list[0:plot_period_int], yr_eps_02_5_growth_expanded_list[0:plot_period_int], label = 'Q 2.5%',color="Cyan",linestyle = '-', linewidth=1)

yr_eps_05_0_plt.set_ylim(qtr_eps_lim_lower,qtr_eps_lim_upper)
yr_eps_05_0_plt.set_yticks([])
yr_eps_05_0_plt_inst = yr_eps_05_0_plt.plot(date_list[0:plot_period_int], yr_eps_05_0_growth_expanded_list[0:plot_period_int], label = 'Q 5%',color="Yellow",linestyle = '-', linewidth=1)

yr_eps_10_0_plt.set_ylim(qtr_eps_lim_lower,qtr_eps_lim_upper)
yr_eps_10_0_plt.set_yticks([])
yr_eps_10_0_plt_inst = yr_eps_10_0_plt.plot(date_list[0:plot_period_int], yr_eps_10_0_growth_expanded_list[0:plot_period_int], label = 'Q 10%',color="Cyan",linestyle = '-', linewidth=1)

yr_eps_20_0_plt.set_ylim(qtr_eps_lim_lower,qtr_eps_lim_upper)
yr_eps_20_0_plt.set_yticks([])
yr_eps_20_0_plt_inst = yr_eps_20_0_plt.plot(date_list[0:plot_period_int], yr_eps_20_0_growth_expanded_list[0:plot_period_int], label = 'Q 20%',color="Yellow",linestyle = '-', linewidth=1)
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Upper Price Channel Plot
# -----------------------------------------------------------------------------
# upper_channel_plt.set_ylabel('Upper_guide', color = 'b')
# upper_channel_plt.spines["right"].set_position(("axes", 1.2))
upper_channel_plt.set_ylim(qtr_eps_lim_lower,qtr_eps_lim_upper)
upper_channel_plt.set_yticks([])
upper_channel_plt_inst = upper_channel_plt.plot(date_list[0:plot_period_int], guide_line_upper_list[0:plot_period_int],label= 'top', color="blue",linestyle = '-')
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Lower Price Channel Plot
# -----------------------------------------------------------------------------
# upper_channel_plt.set_ylabel('Upper_guide', color = 'b')
# upper_channel_plt.spines["right"].set_position(("axes", 1.2))
lower_channel_plt.set_ylim(qtr_eps_lim_lower,qtr_eps_lim_upper)
lower_channel_plt.set_yticks([])
lower_channel_plt_inst = lower_channel_plt.plot(date_list[0:plot_period_int], guide_line_lower_list[0:plot_period_int],label= 'bot', color="blue",linestyle = '-')
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Collect the labels for the subplots and then create the legends
# -----------------------------------------------------------------------------
lns = main_plt_inst + \
      yr_eps_20_0_plt_inst + yr_eps_10_0_plt_inst + \
      yr_eps_05_0_plt_inst + yr_eps_02_5_plt_inst + \
      annual_past_eps_plt_inst + upper_channel_plt_inst + \
      lower_channel_plt_inst + price_plt_inst
labs = [l.get_label() for l in lns]
main_plt.legend(lns, labs, loc="upper left", fontsize = 'x-small')
# This works if we don't have defined the inst of the plots. In this case we
# collect the things manually and then put them in legend
# h1,l1 = main_plt.get_legend_handles_labels()
# h2,l2 = price_plt.get_legend_handles_labels()
# main_plt.legend(h1+h2, l1+l2, loc=2)
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# If there is an Text box that needs to be inserted then
# insert it here...There can be multiple of them inserted
# The locations for AnchoredText at
# https://matplotlib.org/api/offsetbox_api.html
# -----------------------------------------------------------------------------
a_text = AnchoredText("Analysts are Pretty \nDarn Accurate", loc=9)
main_plt.add_artist(a_text)
# a_text1 = AnchoredText("Analysts are Pretty Darn Accurate Text1", loc=3)
# main_plt.add_artist(a_text1)
# -----------------------------------------------------------------------------




#  Set the Minor and Major ticks and then show the gird
xstart,xend = price_plt.get_xlim()
ystart,yend = price_plt.get_ylim()
xstart_date = matplotlib.dates.num2date(xstart)
xend_date = matplotlib.dates.num2date(xend)



# This works but needs more research
# Date to annotate
date_to_annotate = "2017-03-29"
date_to_annotate_datetime = dt.datetime.strptime(date_to_annotate, '%Y-%m-%d').date()
# date_to_annoate_num = matplotlib.dates.date2num(date_to_annotate)
match_date = min(date_list, key=lambda d: abs(d - date_to_annotate_datetime))
print("The matching date is ", match_date, " at index ", date_list.index(match_date), " and the price is " ,adj_close_list[date_list.index(match_date)])

price_plt.annotate('UK Referendom for Brexit',xy= (date_list[date_list.index(match_date)],adj_close_list[date_list.index(match_date)]),
                   arrowprops=dict(facecolor='black', width=1))
# xytext=(50, 30),textcoords='offset points', arrowprops=dict(facecolor='black', width=1))

print ("The xlimit Start: ", xstart_date, " End: ", xend_date, "Starting year", xstart_date.year )
print ("The ylimit Start: ", ystart, " End: ", yend )

# main_plt.xaxis.grid(True)


main_plt.xaxis.grid(b=True,which='major')
main_plt.xaxis.grid(b=True,which='minor',linestyle='--')
main_plt.minorticks_on()
main_plt.yaxis.grid(True)

# -----------------------------------------------------------------------------
# Save the Chart with the date and time as prefix
# -----------------------------------------------------------------------------
# This works too instead of two line
# date_time =  dt.datetime.now().strftime("%Y_%m_%d_%H_%M")
now = dt.datetime.now()
date_time = now.strftime("%Y_%m_%d_%H_%M")
fig.savefig(chart_dir + "\\" + ticker + "_" + date_time + ".jpg",dpi=200)
plt.show()
# -----------------------------------------------------------------------------


