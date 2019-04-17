import pandas as pd
import matplotlib
import datetime as dt
import numpy as np
import matplotlib.pyplot as plt

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

'''
fig, host = plt.subplots()
t = np.arange(0.01, 10.0, 0.01) # Returns a numpy.ndarray

s1 = np.exp(t) # Returns numpy.ndarray
host.plot(t, s1, 'b-') # Plots blue with solid line
host.set_xlabel('time (s)')
# Make the y-axis label, ticks and tick labels match the line color.
host.set_ylabel('exp', color='b')
host.tick_params('y', colors='b')

par1 = host.twinx() # Create a twin Axes sharing the xaxis
s2 = np.sin(2 * np.pi * t)
par1.plot(t, s2, 'r.')
par1.set_ylabel('sin', color='r')
par1.tick_params('y', colors='r')

fig.tight_layout()
plt.show()
'''

# ================================================================
# My stuff starts here
# ================================================================
historical_df = pd.read_csv('AAPL_historical.csv')
qtr_eps_df = pd.read_csv('AAPL_earnings.csv')
date_str_list = historical_df.Date.tolist()
adj_close_list = historical_df.Adj_Close.tolist()
qtr_eps_col_list = qtr_eps_df.columns.tolist()

print (date_str_list)
print (adj_close_list)
print (qtr_eps_col_list)


date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in date_str_list]
qtr_eps_date_str_list = qtr_eps_df.Date.tolist()
# print (qtr_eps_date_str_list)
qtr_eps_list = qtr_eps_df.Q_EPS.tolist()
print (qtr_eps_list)
qtr_eps_date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in qtr_eps_date_str_list]

# Find the closet date here - This work. Now need to have a list of dates from
# the earnings projection stuff sundeep is here
date_2_search =dt.datetime.strptime("12/13/1981", '%m/%d/%Y').date()
match_date = min(date_list, key=lambda d: abs(d - date_2_search))
print ("The matching date is ", match_date)

exit()


# del qtr_eps_date_str_list[0]
# del qtr_eps_list[0]



clean_qtr_eps_list = [x for x in qtr_eps_list if str(x) != 'nan']
print ("Clean QTR EPS List ", clean_qtr_eps_list)
max_earnings = max(clean_qtr_eps_list)
min_eanrings = min (clean_qtr_eps_list)
print ("Min Earnings", min_eanrings)
print ("Max Earnings", max_earnings)

# find the average of 4 quarters in the list
print ("Number of Quarterly Earnings available ", len(clean_qtr_eps_list))

# ===================================================================================================
# Create the Clean Annual EPS list
# ===================================================================================================
i_int = 0
clean_annual_eps_list = list()
while (i_int < (len(clean_qtr_eps_list)-3)):
  annual_average_eps = (clean_qtr_eps_list[i_int] +     \
                        clean_qtr_eps_list[i_int + 1] + \
                        clean_qtr_eps_list[i_int + 2] + \
                        clean_qtr_eps_list[i_int + 3])/4
  '''
  print ("Iteration #, Quartely EPS, Annual EPS", i_int, \
                                                  clean_qtr_eps_list[i_int], \
                                                  clean_qtr_eps_list[i_int+1],\
                                                  clean_qtr_eps_list[i_int+2],\
                                                  clean_qtr_eps_list[i_int+3], \
                                                  annual_average_eps)
  '''
  clean_annual_eps_list.append(annual_average_eps)
  i_int += 1
print ("Clean Annual EPS List ", clean_annual_eps_list)
# ===================================================================================================

# ===================================================================================================
# Initialize the annual_eps_list with qtr_eps_list
# ===================================================================================================
annual_eps_list = qtr_eps_list.copy()
print ("# of Elements in Quarterly EPS", len(qtr_eps_list))
i_int = 0
while (i_int <= len(qtr_eps_list)):
  print ("Quarter EPS List", qtr_eps_list[i_int:i_int+16])
  i_int += 16


i_int = 0
while (i_int < (len(qtr_eps_list)-1)):
  # print ("Iteration #, Quarter EPS", i_int, qtr_eps_list[i_int])
  if (str(qtr_eps_list[i_int]) != 'nan'):
    if (len(clean_annual_eps_list) > 0):
      # print ("Quater EPS: , Annual EPS ",qtr_eps_list[i_int], clean_annual_eps_list[0])
      annual_eps_list[i_int] = clean_annual_eps_list.pop(0)
  i_int += 1

print ("# of Elements in Annual EPS", len(annual_eps_list))
i_int = 0
while (i_int <= len(qtr_eps_list)):
  print ("Annual EPS List", annual_eps_list[i_int:i_int+16])
  i_int += 16
# ===================================================================================================



# l_clean = [1,2,7]
# l_indices = [2,5,9]
#
# l_len = len(l)
# print ("Length of the list is ", l_len)
#
# i_int = 0
# while (i_int < len(l_clean)-1):
#   print ("Clean List index:", i_int, ", Clean List value:", l_clean[i_int], ", Corresponding List index:", l_indices[i_int])
#   step = (l_clean[i_int]-l_clean[i_int+1])/(l_indices[i_int+1]-l_indices[i_int])
#   start_index = l_indices[i_int]
#   stop_index = l_indices[i_int+1]
#   print ("The step is ", step, "Start and Stop Indices are ", start_index, stop_index)
#   j_int = start_index +1
#   while (j_int < stop_index):
#     l[j_int] = float(l[j_int-1]) - step
#     print("Updating index", j_int, "to ",l[j_int])
#     j_int += 1
#   i_int += 1
#
# print ("Modified List is", l)
# l = ['nan', 'nan', 1, 'nan', 'nan', 2, 'nan', 'nan', 'nan', 7, 'nan']
# l_mod = smooth_list(l)





# ===================================================================================================
# Create the Guide lines
# ===================================================================================================
guide_line_upper_list_unclean = [eps+.5 for eps in annual_eps_list]
guide_line_upper_list = smooth_list(guide_line_upper_list_unclean)
print ("The upper Guide is ", guide_line_upper_list)
# guide_line_upper_list_clean = [0 if str(x) == 'nan' else x for x in guide_line_upper_list ]
# guide_line_upper_list_clean = [x for x in guide_line_upper_list if str(x) != 'nan']
# print ("The upper guild clean is" ,guide_line_upper_list_clean)
# guide_line_upper_list_array = np.array(guide_line_upper_list)
# guide_line_upper_list_np = pd.DataFrame(np.array(guide_line_upper_list))
# guide_line_upper_list_np_fill = guide_line_upper_list_np.fillna(method='bfill')
# print ("The upper Guide np ", guide_line_upper_list_np)

guide_line_lower_list_unclean = [eps-.5 for eps in annual_eps_list]
guide_line_lower_list = smooth_list(guide_line_lower_list_unclean)
print ("The upper Guide is ", guide_line_lower_list)
# ===================================================================================================

#  Find out how many years need to be plotted
# Need to write a small procedure to find that out
plot_period_str = "10Y"
plot_period_int = 252*10


# Now plot Everything
fig, main_plt = plt.subplots()
fig.set_size_inches(12,8)
main_plt.set_facecolor("lightgrey")
fig.subplots_adjust(right=0.75)

price_plt = main_plt.twinx()
annual_eps_plt = main_plt.twinx()
upper_channel_plt = main_plt.twinx()
lower_channel_plt = main_plt.twinx()

print ("Type of fig ", type(fig), \
       "\nType of main_plt ", type(main_plt), \
       "\nType of price_plt: ", type(price_plt), \
       "\nType of annual_eps_plt: ", type(annual_eps_plt), \
       "\nType of upper_channel_plt: ", type(upper_channel_plt))

# -----------------------------------------------------------------------------
# Main Plot - This is the Q EPS vs Date
# -----------------------------------------------------------------------------
main_plt.set_title("Stock Chart for AAPL")
main_plt.set_xlabel('Date')
main_plt.set_ylabel('Q EPS')
main_plt.set_ylim(0, 6)
main_plt_inst = main_plt.plot(date_list[0:plot_period_int],qtr_eps_list[0:plot_period_int], label = 'Q EPS',color="deeppink",marker='.', markersize='8')

# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Historical Price Plot
# -----------------------------------------------------------------------------
price_plt.set_ylabel('Price', color='k')
price_plt.set_ylim(0,300)
price_plt_inst = price_plt.plot(date_list[0:plot_period_int], adj_close_list[0:plot_period_int], label = 'Price',color="brown",linestyle='-')
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Average Annual EPS Plot
# -----------------------------------------------------------------------------
# annual_eps_plt.set_ylabel('Avg. Annual Earnings', color='k')
# annual_eps_plt.spines["right"].set_position(("axes", 1.1))
annual_eps_plt.set_ylim(0,6)
annual_eps_plt.set_yticks([])
annual_eps_plt_inst = annual_eps_plt.plot(date_list[0:plot_period_int], annual_eps_list[0:plot_period_int], label = 'Annual EPS',color="black",marker='D',markersize='4')
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Uppoer Price Channel Plot
# -----------------------------------------------------------------------------
# upper_channel_plt.set_ylabel('Upper_guide', color = 'b')
# upper_channel_plt.spines["right"].set_position(("axes", 1.2))
upper_channel_plt.set_ylim(0,6)
upper_channel_plt.set_yticks([])
upper_channel_plt_inst = upper_channel_plt.plot(date_list[0:plot_period_int], guide_line_upper_list[0:plot_period_int],label= 'Upper Channel', color="blue",linestyle = '-')
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Lower Price Channel Plot
# -----------------------------------------------------------------------------
# upper_channel_plt.set_ylabel('Upper_guide', color = 'b')
# upper_channel_plt.spines["right"].set_position(("axes", 1.2))
lower_channel_plt.set_ylim(0,6)
lower_channel_plt.set_yticks([])
lower_channel_plt_inst = lower_channel_plt.plot(date_list[0:plot_period_int], guide_line_lower_list[0:plot_period_int],label= 'Upper Channel', color="blue",linestyle = '-')
# -----------------------------------------------------------------------------

#  Set the Minor and Major ticks and then show the gird
# Sundeep is here
xstart,xend = main_plt.get_xlim()
ystart,yend = main_plt.get_ylim()
print ("The xlimit Start: ", xstart, " End: ", xend )
print ("The ylimit Start: ", ystart, " End: ", yend )
#
# i_int = 0
# for i_int in range(xstart,xend,2):
#   xticks.append(i_int)
#

main_plt.xaxis.grid(True)
main_plt.yaxis.grid(True)

# To Do : fixme
# Plot the lines that emcompass the earnings (the distance from Earnings parameterizable)
# Limit the length of the graph to 5 years (parameterizable)
# Grid lines
# What format the file should be save
# New file format for earnings
# Legends in the plot
# Dividends in the plot
# Get the code debug friendly
# How to create other subplots that have the book value etc
#   Maybe use subplots for it
# How to use earnings projections
# The turcosie and yellow earning growth lines (parameterizable)

# plt.legend((main_plt_inst,price_plt_inst,annual_eps_plt_inst,upper_channel_plt_inst),\
#            ("Q EPS","Price","Annual EPS","UpperChannel"))
# main_plt.legend(loc='upper left')
# price_plt.legend(loc='upper left')
# fig.legend((main_plt_inst, price_plt_inst), ('Q EPS', 'Price'), 'upper left')
# fig.legend()



fig.savefig('myfig.jpg',dpi=200)
plt.show()
# ================================================================
# My Stuff Ends here
# ================================================================
'''
Somehow reading with col_names did not work??
# col_names = ["Date", "Open", "High", "Low", "Close", "Adj_Close", "Volume"]
# historical_df = pd.read_csv('AMZN_historical.csv', names=col_names)
'''

'''
historical_df = pd.read_csv('AAPL_historical.csv')
col_list = historical_df.columns.tolist()
# print (col_list)
# print (historical_df)
date_str_list = historical_df.Date.tolist()
adj_close_list = historical_df.Adj_Close.tolist()

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

qtr_eps_df = pd.read_csv('AAPL_earnings.csv')
qtr_eps_col_list = qtr_eps_df.columns.tolist()
print (qtr_eps_col_list)

qtr_eps_date_str_list = qtr_eps_df.Date.tolist()
qtr_eps_list = qtr_eps_df.Q_EPS.tolist()

print (qtr_eps_date_str_list)
print (qtr_eps_list)

del qtr_eps_date_str_list[0]
del qtr_eps_list[0]

qtr_eps_date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in qtr_eps_date_str_list]



plt.scatter(qtr_eps_date_list,qtr_eps_list)
plt.grid(which='major')

plt.show

# ----------------------------------------------------------------------------------------------------

plt.figure(figsize=(3,2))

x = np.linspace(-np.pi, np.pi,300)
C,S = np.cos(x),np.sin(x)

plt.plot(x,C)
plt.plot(x,S)

plt.show()
'''