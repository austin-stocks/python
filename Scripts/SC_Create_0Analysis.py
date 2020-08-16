import csv
import openpyxl
from openpyxl.styles import PatternFill
import os
import xlrd
import sys
import time
import pandas as pd
import datetime as dt
from yahoofinancials import YahooFinancials
import time
import logging
import xlsxwriter
import matplotlib.pyplot as plt


def color_negative_red(val):
  """
  Takes a scalar and returns a string with
  the css property `'color: red'` for negative
  strings, black otherwise.
  """
  color = 'red' if val < 10 else 'black'
  return 'color: %s' % color

def human_format(num, precision=2, suffixes=['', 'K', 'M', 'B', 'T', 'P']):
  m = sum([abs(num / 1000.0 ** x) >= 1 for x in range(1, len(suffixes))])
  return f'{num / 1000.0 ** m:.{precision}f} {suffixes[m]}'

# ---------------------------------------------------------------------------
# Define the directories and the paths
# ---------------------------------------------------------------------------
dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
historical_dir = "\\..\\" + "Historical"
earnings_dir = "\\..\\" + "Earnings"
dividend_dir = "\\..\\" + "Dividend"
log_dir = "\\..\\" + "Logs"
analysis_dir = "\\..\\" + "Analysis"
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Set Logging
# critical, error, warning, info, debug
# set up logging to file - see previous section for more details
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename=dir_path + log_dir + "\\" + 'SC_Create_0Analysis_debug.txt',
                    filemode='w')
# define a Handler which writes INFO messages or higher to the sys.stderr
console = logging.StreamHandler()
console.setLevel(logging.INFO)
# set a format which is simpler for console use
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
# tell the handler to use this format
console.setFormatter(formatter)
# add the handler to the root logger
logging.getLogger('').addHandler(console)

# Disnable and enable global level logging
logging.disable(sys.maxsize)
logging.disable(logging.NOTSET)
# ---------------------------------------------------------------------------

# Sundeep thoughts on what to do for 0_Analysis
# Maybe start with 5 quarters and see if that makes sense...we can increase it to 8 quarters too.
# Zebras like Market Smith -- for EPS and Revenue for 5 quarters
# Share count Diluted  - 5 quarters -- Maybe add in the yr_dataframe too
# Number of Employees - 5 quarters
# Inventory Change - 5 Quarters
# Institutional Shares Sold vs Institutional Shares Purchased - 5 quarters
# Insiders buying / selling?  (Net Insiders buy Insiders-net shares purchased or Net Insider Buys % Shares Out or Net Insider Buys % Shares Out.) - 5 quarters
# Get the projected Revenue and Diluted EPS growth rates

# Key Statistics
# Debt the Equity - Just this quarter
# Current Ratio - Just this quarter
# Debt to equity - Just this quarter
# price to sales - Just this quarter
# PEG Ratio - how to find that out (May need to read the earnings and find TTM earning
#   and also to find out projected earnings (deal with the case if there are only 3 quarters
#   worth of future projected earnings data available -- maybe say not available). Find the PE from
#   TTM earnings and growth rate from projected earnings...(even though the projected earnings are not
#   always diluted earnings...but that is the best thing available right now


# Phil Town Stuff -- Are these growth numbers?
# Free Cash flow per share Growth  - 10 years
# ROIC Growth  - 10 years

# todo
# Create a quarterly xls and dataframe
#   Earnings
#   Revenue
#   # of Employees (only available in 10-K?). So do it annually??
#   Share Count Diluted
#   Inventory
#   Institutional Ownership
#   Insider buy/sell
#   Projected Revenue and EPS for next 2 quarters (where to put it? -- Maybe add two rows for the current quarter)
#   Debt
#   Shareholders Equity
#   Current Ratio (Should I calculate or should it be directly downloaded from AAII - This is also a philosophical question in general)
#
# todo : Maybe add a one row table at the top - with has
# Price, PB, PS, ROE, PEG, Current Ratio, Expected Growth, it can also list some past trends in one word - etc...think about more
# todo : Save the fis in a loop - just like for Earnings chart

# Save the jpg in the loop - just like the earnings chart
# See for how many years do we want to prepare the dataframe and chart - This feature will be needed later.
# Print the date of latest price and what is the price (read the historical)

# -----------------------------------------------------------------------------
# Set the various dirs and read the AAII file
# -----------------------------------------------------------------------------
qtr_str_list = ['Q1', 'Q2', 'Q3', 'Q4', 'Q5', 'Q6', 'Q7', 'Q8']
yr_str_list = ['Y1', 'Y2', 'Y3', 'Y4', 'Y5', 'Y6', 'Y7']

tracklist_file = "Tracklist.csv"
tracklist_file_full_path = dir_path + user_dir + "\\" + tracklist_file
configuration_file = "Configurations.csv"
configurations_file_full_path = dir_path + user_dir + "\\" + configuration_file
tracklist_df = pd.read_csv(tracklist_file_full_path)


ticker_list_unclean = tracklist_df['Tickers'].tolist()
ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']
# #############################################################################
#                   MAIN LOOP FOR TICKERS
# #############################################################################
ticker_list = ['NATI']
for ticker_raw in ticker_list:

  ticker = ticker_raw.replace(" ", "").upper()  # Remove all spaces from ticker_raw and convert to uppercase
  logging.info("========================================================")
  logging.info("Processing for " + ticker)
  logging.info("========================================================")
  if (ticker in ["QQQ"]):
    logging.debug(str(ticker) + " is NOT in AAII df or is QQQ (etf). Will skip inserting EPS Projections..")
    continue

  # ===========================================================================
  # Read the ticker AAII data qtr file to start
  # ===========================================================================
  # After reading make a copy of the dataframe - it is really not needed but for now it is what it is
  # Maybe at a later stage don't make a copy and work on the dataframe that is read in directly
  # Once that dateframe is copied - then the new rows (that are used to store the growth) are added.

  ticker_datain_qtr_file = ticker +  "_qtr_data.csv"
  ticker_datain_qtr_df = pd.read_csv(dir_path + analysis_dir + "\\" + "Quarterly" + "\\" + ticker_datain_qtr_file)
  ticker_datain_qtr_df.set_index("AAII_QTR_DATA",inplace=True)
  logging.debug("The QTR datain df \n" + ticker_datain_qtr_df.to_string())
  logging.info("Starting to process QTR data")

  # Start working with the dataframe to generate various numbers
  ticker_qtr_numbers_df = ticker_datain_qtr_df.copy()
  #   Earnings
  #   Revenue
  #   # of Employees (only available in 10-K?). So do it annually??
  #   Share Count Diluted
  #   Inventory
  #   Institutional Ownership
  #   Insider buy/sell
  #   Projected Revenue and EPS for next 2 quarters (where to put it? -- Maybe add two rows for the current quarter)
  #   Debt
  #   Shareholders Equity
  #   Current Ratio (Should I calculate or should it be directly downloaded from AAII - This is also a philosophical question in general)

  # Add the rows for Revenue growth, EPS growth
  col_list = ticker_qtr_numbers_df.columns.tolist()
  qtr_eps_growth_list = []
  qtr_revenue_growth_list = []
  for col_idx in range(len(col_list)):
    qtr_eps_growth_list.append(float('nan'))
    qtr_revenue_growth_list.append(float('nan'))
  ticker_qtr_numbers_df = ticker_qtr_numbers_df.append(pd.Series(qtr_eps_growth_list, index=ticker_qtr_numbers_df.columns, name='EPS_Growth'))
  ticker_qtr_numbers_df = ticker_qtr_numbers_df.append(pd.Series(qtr_revenue_growth_list, index=ticker_qtr_numbers_df.columns, name='Revenue_Growth'))
  logging.debug("The QTR  df after adding rows \n" + ticker_qtr_numbers_df.to_string())

  # Now calculate the EPS and sales grwoth and put them in just added rows
  col_list = ticker_qtr_numbers_df.columns.tolist()
  no_of_qts_to_calculate_growth_rate_for = 4
  for col_idx in range(0, no_of_qts_to_calculate_growth_rate_for):
    # Only calculate the qtrs for which the back data is available...this will get better are more date becomes available.
    if (col_idx+4 <= len(col_list)-1):
      col_val = col_list[col_idx]
      col_val_same_qtr_last_year = col_list[col_idx+4]
      logging.debug("The col_idx is " + str(col_idx) + " and the value is " + col_val)
      eps_this_qtr = ticker_qtr_numbers_df.loc['Diluted_EPS', col_val]
      eps_same_qtr_last_year = ticker_qtr_numbers_df.loc['Diluted_EPS', col_val_same_qtr_last_year]
      # if eps last year was negative then don't do anything as that grwoth rate cannot be calculated
      if (eps_same_qtr_last_year > 0):
        ticker_qtr_numbers_df.loc['EPS_Growth', col_val] = 100*((eps_this_qtr/eps_same_qtr_last_year)-1)

      ticker_qtr_numbers_df.loc['Revenue_Growth', col_val] = 100*((ticker_qtr_numbers_df.loc['Revenue', col_val]/ticker_qtr_numbers_df.loc['Revenue', col_val_same_qtr_last_year])-1)
  logging.debug("The QTR  df after calculation grwoth rates for Revenue and EPS  \n" + ticker_qtr_numbers_df.to_string())
  # Now that dataframe is ready - It will be modified in the chart section -- Read there to find out more

  # ===========================================================================

  # ===========================================================================
  # Read the ticker AAII data yr file
  # ===========================================================================
  ticker_datain_yr_file = ticker +  "_yr_data.csv"
  ticker_datain_yr_df = pd.read_csv(dir_path + analysis_dir + "\\" + "Yearly" + "\\" + ticker_datain_yr_file)
  ticker_datain_yr_df.set_index("AAII_YR_DATA",inplace=True)
  logging.debug("The YR datain df \n" + ticker_datain_yr_df.to_string())


  # ---------------------------------------------------------------------------
  # Now we have a dataframe that we need to make calculation for our 0_Analysis
  # Various dateframes can be generated off the dataframes that we have read in.
  # Those generated dataframes can be reprensed as tables and or used to create
  # graphs later on
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Yearly numbers dataframe
  # ---------------------------------------------------------------------------
  logging.info("Starting to process YR data")
  ticker_yr_numbers_df = ticker_datain_yr_df.copy()
  logging.debug("The YR df \n" + ticker_yr_numbers_df.to_string())
  col_list = ticker_yr_numbers_df.columns.tolist()

  # These rows are not needed / Remove the unwanted rows 
  ticker_yr_numbers_df.drop(index= ['Current_Assets'], inplace=True)
  ticker_yr_numbers_df.drop(index= ['Dividend'], inplace=True)
  ticker_yr_numbers_df.drop(index= ['Short_Term_Debt'], inplace=True)
  # The rearragne to row to your liking
  ticker_yr_numbers_df = ticker_yr_numbers_df.loc[['Revenue', 'Diluted_EPS', 'BV_Per_Share', 'LT_Debt'], :]
  logging.debug("The YR datain df are removing the unwanted rows \n" + ticker_yr_numbers_df.to_string())
  # First convert the numbers to raw numbers (like the revenue is in millions etc)
  for col_idx in range(len(col_list)):
    col_val = col_list[col_idx]
    ticker_yr_numbers_df.loc['Revenue', col_val] = 1000000 * (ticker_datain_yr_df.loc['Revenue', col_val])
    ticker_yr_numbers_df.loc['LT_Debt', col_val] = 1000000 * (ticker_datain_yr_df.loc['LT_Debt', col_val])

    # col_val_prev = col_list[col_idx+1]
    # logging.debug("Creating Revenue Growth % for : " + str(col_val))
    # ticker_yr_numbers_df.loc['Revenue', col_val] = 100 * (ticker_datain_yr_df.loc['Revenue', col_val] - ticker_datain_yr_df.loc['Revenue', col_val_prev] ) / ticker_datain_yr_df.loc['Revenue', col_val_prev]
    # ticker_yr_numbers_df.loc['Diluted_EPS', col_val] = 100 * (ticker_datain_yr_df.loc['Diluted_EPS', col_val] - ticker_datain_yr_df.loc['Diluted_EPS', col_val_prev] ) / ticker_datain_yr_df.loc['Diluted_EPS', col_val_prev]

  # This reverses the dataframe by columns - Both of these work
  # tmp_df = ticker_yr_numbers_df[ticker_yr_numbers_df.columns[::-1]]
  tmp_df = ticker_yr_numbers_df.iloc[:, ::-1]
  ticker_yr_numbers_df = tmp_df.copy()
  logging.debug("The dataframe now is \n" + ticker_yr_numbers_df.to_string())
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Yearly dataframe that is used to store the growth numbers
  # ---------------------------------------------------------------------------
  ticker_yr_growth_df = ticker_datain_yr_df.copy()

  ticker_yr_growth_df.drop(index= ['Current_Assets'], inplace=True)
  ticker_yr_growth_df.drop(index= ['Dividend'], inplace=True)
  ticker_yr_growth_df.drop(index= ['Short_Term_Debt'], inplace=True)
  ticker_yr_growth_df.drop(index= ['LT_Debt'], inplace=True)

  # Reverse the Dataeframe
  tmp_df = ticker_yr_growth_df.iloc[:, ::-1]
  ticker_yr_growth_df = tmp_df.copy()

  col_list = ticker_yr_growth_df.columns.tolist()
  base_growth_rate_percent_10 = .1
  base_growth_rate_percent_20 = .2
  base_growth_10_percent_list = []
  base_growth_20_percent_list = []
  for col_idx in range(len(col_list)):
    base_growth_10_percent_list.append(float('nan'))
    base_growth_20_percent_list.append(float('nan'))
    if (col_idx == 0):
      base_growth_10_percent_list[col_idx] = 1
      base_growth_20_percent_list[col_idx] = 1
    else:
      base_growth_10_percent_list[col_idx] = base_growth_10_percent_list[col_idx-1]*(1+base_growth_rate_percent_10)
      base_growth_20_percent_list[col_idx] = base_growth_20_percent_list[col_idx-1]*(1+base_growth_rate_percent_20)
  # Reverse the list
  # base_growth_10_percent_list = base_growth_10_percent_list[::-1]
  logging.debug("The base growth 10% list is " + str(base_growth_10_percent_list))
  logging.debug("The base growth 20% list is " + str(base_growth_20_percent_list))
  ticker_yr_growth_df = ticker_yr_growth_df.append(pd.Series(base_growth_10_percent_list, index=ticker_yr_growth_df.columns, name='Base_Growth_10'))
  ticker_yr_growth_df = ticker_yr_growth_df.append(pd.Series(base_growth_20_percent_list, index=ticker_yr_growth_df.columns, name='Base_Growth_20'))
  # Add token growth rate rows -- these will be populated properly below
  ticker_yr_growth_df = ticker_yr_growth_df.append(pd.Series(base_growth_10_percent_list, index=ticker_yr_growth_df.columns, name='Revenue_Growth'))
  ticker_yr_growth_df = ticker_yr_growth_df.append(pd.Series(base_growth_10_percent_list, index=ticker_yr_growth_df.columns, name='Diluted_EPS_Growth'))
  ticker_yr_growth_df = ticker_yr_growth_df.append(pd.Series(base_growth_10_percent_list, index=ticker_yr_growth_df.columns, name='BV_Per_Share_Growth'))

  logging.debug("The YR Growth dataframe now is \n" + ticker_yr_growth_df.to_string())

  for col_idx in range(len(col_list)):
    col_val = col_list[col_idx]
    if (col_idx == 0):
      ticker_yr_growth_df.loc['Revenue_Growth', col_val] = 1
      ticker_yr_growth_df.loc['Diluted_EPS_Growth', col_val] = 1
      ticker_yr_growth_df.loc['BV_Per_Share_Growth', col_val] = 1
    else:
      col_val_starting = col_list[0]
      # ticker_yr_growth_df.loc['Revenue_Growth', col_val] = (ticker_datain_yr_df.loc['Revenue', col_val]/ticker_datain_yr_df.loc['Revenue', col_val_starting])**(1/col_idx)
      # ticker_yr_growth_df.loc['Diluted_EPS_Growth', col_val] = (ticker_datain_yr_df.loc['Diluted_EPS', col_val]/ticker_datain_yr_df.loc['Diluted_EPS', col_val_starting])**(1/col_idx)
      # ticker_yr_growth_df.loc['BV_Per_Share_Growth', col_val] = (ticker_datain_yr_df.loc['BV_Per_Share', col_val]/ticker_datain_yr_df.loc['BV_Per_Share', col_val_starting])**(1/col_idx)
      ticker_yr_growth_df.loc['Revenue_Growth', col_val] = (ticker_datain_yr_df.loc['Revenue', col_val]/ticker_datain_yr_df.loc['Revenue', col_val_starting])
      ticker_yr_growth_df.loc['Diluted_EPS_Growth', col_val] = (ticker_datain_yr_df.loc['Diluted_EPS', col_val]/ticker_datain_yr_df.loc['Diluted_EPS', col_val_starting])
      ticker_yr_growth_df.loc['BV_Per_Share_Growth', col_val] = (ticker_datain_yr_df.loc['BV_Per_Share', col_val]/ticker_datain_yr_df.loc['BV_Per_Share', col_val_starting])

  logging.debug("The YR Growth dataframe now is \n" + ticker_yr_growth_df.to_string())

  ticker_yr_growth_df = ticker_yr_growth_df.loc[['Base_Growth_10', 'Base_Growth_10','Revenue_Growth', 'Diluted_EPS_Growth', 'BV_Per_Share_Growth'], :]
  logging.debug("The YR Growth dataframe now is \n" + ticker_yr_growth_df.to_string())
  # ===========================================================================



  # ---------------------------------------------------------------------------
  # ticker_yr_numbers_df.applymap(lambda x: str(int(x)) if abs(x - int(x)) < 1e-6 else str(round(x, 2)))

  # #############################################################################
  # #############################################################################
  # #############################################################################
  # ###########                                                        ##########
  # ###########                                                        ##########
  # ###########                    NOW PLOT EVERYTHING                 ##########
  # ###########                                                        ##########
  # ###########                                                        ##########
  # #############################################################################
  # #############################################################################
  # #############################################################################
  logging.debug("=========================================================")
  logging.info("Starting to plot the data now...")
  logging.debug("=========================================================")
  fig = plt.figure()
  fig.set_size_inches(14.431, 7.639)  # Length x height
  # This sets the background color of the whole figure
  fig.patch.set_facecolor('#E0E0E0')
  fig.patch.set_alpha(0.7)

  qtr_table_plt = plt.subplot2grid((6, 6), (0, 0), rowspan=2,colspan=3)
  yr_growth_plt = plt.subplot2grid((6, 6), (0, 3), rowspan=4,colspan=3)
  key_numbers_plt = plt.subplot2grid((6, 6), (2, 0), rowspan=2, colspan=3)
  yr_table_plt = plt.subplot2grid((6, 6), (4, 0), rowspan=2, colspan=6)
  plt.subplots_adjust(hspace=.1, wspace=.15)
  fig.suptitle("Analysis for " + ticker)


  # ---------------------------------------------------------------------------
  # Plot the Growth Chart
  # ---------------------------------------------------------------------------
  # todo : Get the x axis labels shorter (like Dec-19)and invward -- if that is asethetically pleasing
  # todo : Get the ticklines (both x axis and y axis)
  # todo : Print the values on Blue line, if you want
  # todo : Print the legend for various lines - inside the ax
  yr_growth_plt.title.set_text("Yearly Growth Chart")
  yr_growth_plt.set_facecolor("lightgrey")

  yr_growth_plt_lim_lower = 0
  yr_growth_plt_lim_upper = 3.5
  # Extract the various growth numbers and set the upper limit, if greater than 3.5 (set by default up)
  tmp_max = max(ticker_yr_growth_df.loc["Diluted_EPS_Growth"])
  logging.debug("The max value in Diluted EPS Growth List is "  + str(tmp_max))
  if (tmp_max > yr_growth_plt_lim_upper):
    yr_growth_plt_lim_upper = int(round(tmp_max))+.5

  tmp_max = max(ticker_yr_growth_df.loc["Revenue_Growth"])
  logging.debug("The max value in Diluted Revenue Growth List is " + str(tmp_max))
  if (tmp_max > yr_growth_plt_lim_upper):
    yr_growth_plt_lim_upper = int(round(tmp_max))+.5

  tmp_max = max(ticker_yr_growth_df.loc["BV_Per_Share_Growth"])
  logging.debug("The max value in Diluted BVPS Growth List is " + str(tmp_max))
  if (tmp_max > yr_growth_plt_lim_upper):
    yr_growth_plt_lim_upper = int(round(tmp_max))+.5

  logging.debug("The upper limit for the Growth Plot is set to " + str(yr_growth_plt_lim_upper))

  yr_growth_plt.set_ylim(yr_growth_plt_lim_lower, yr_growth_plt_lim_upper)
  yr_growth_plt.tick_params(axis="y", direction="in", pad=-22)

  yr_growth_plt_inst_00 = yr_growth_plt.plot(ticker_yr_growth_df.columns.tolist(), base_growth_10_percent_list, label='Base_Growth_10', linestyle='--',color='blue',marker="*",markersize='12')
  yr_growth_plt_inst_01 = yr_growth_plt.plot(ticker_yr_growth_df.columns.tolist(), base_growth_20_percent_list, label='Base_Growth_20', linestyle='--',color='blue',marker="*",markersize='12')
  yr_growth_plt_inst_02 = yr_growth_plt.plot(ticker_yr_growth_df.columns.tolist(), ticker_yr_growth_df.loc["Diluted_EPS_Growth"], label='EPS', color="deeppink", marker='.', markersize='10')
  yr_growth_plt_inst_03 = yr_growth_plt.plot(ticker_yr_growth_df.columns.tolist(), ticker_yr_growth_df.loc["Revenue_Growth"], label='Rev', color="green", marker='.', markersize='10')
  yr_growth_plt_inst_04 = yr_growth_plt.plot(ticker_yr_growth_df.columns.tolist(), ticker_yr_growth_df.loc["BV_Per_Share_Growth"], label='BVPS', color="brown", marker='.', markersize='10')

  # Maybe need to adjust if the plot gets moved???
  lns = yr_growth_plt_inst_02+yr_growth_plt_inst_03+yr_growth_plt_inst_04
  labs = [l.get_label() for l in lns]
  logging.debug("The Labels are" + str(labs))
  yr_growth_plt.legend(lns, labs, bbox_to_anchor=(.2, 1.02), loc="upper right", borderaxespad=2, fontsize='x-small')
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Plot the Quarterly Table
  # ---------------------------------------------------------------------------
  qtr_table_plt.title.set_text("Quarterly Numbers")
  qtr_table_plt.set_yticks([])
  qtr_table_plt.set_xticks([])

  # Extract the desired rows out of the dataframe in tmp_df
  tmp_df  = pd.DataFrame()
  desired_indices = ['Revenue','Revenue_Growth','Diluted_EPS','EPS_Growth']
  tmp_df = ticker_qtr_numbers_df.loc[desired_indices]
  logging.debug("The QTR df with only desired indices extracted out : \n" + tmp_df.to_string())

  # Now keep only the first 4 columns of the dataframe as these are the date that we want to display - this can get
  # exteneded if user desires later on..
  tmp_df_1 = tmp_df.iloc[:, : 4]
  logging.debug("The QTR df with only first 4 quarters of data  \n" + tmp_df_1.to_string())

  # Now reverse the dataframe - so that the older dates are first in the column
  tmp_df_2 = tmp_df_1.iloc[:, ::-1]
  logging.debug("The QTR df with only first 4 quarters of data now reversed  \n" + tmp_df_2.to_string())
  # Finally transpose  the  dataframe so that it can be displayed vertically
  tmp_df = tmp_df_2.transpose().copy()
  logging.debug("The QTR df with only first 4 quarters of data reversed and now transposed \n" + tmp_df.to_string())

  # Now plot the dataframe
  # qtr_table_plt_inst = qtr_table_plt.table(cellText=tmp_df.values, rowLabels=tmp_df.index,colWidths=[0.1] * len(tmp_df.columns),colLabels=tmp_df.columns,loc="upper center")
  qtr_table_plt_inst = qtr_table_plt.table(cellText=tmp_df.values, rowLabels=tmp_df.index,colLabels=tmp_df.columns,loc="upper center")

  # iterate through the table and set the fonts etc to desired values
  logging.debug("Iterating through the QTR table to reformat for the text etc...")
  eps_col_idx = tmp_df.columns.get_loc("Diluted_EPS")
  eps_growth_col_idx = tmp_df.columns.get_loc("EPS_Growth")
  revenue_col_idx = tmp_df.columns.get_loc("Revenue")
  revenue_growth_col_idx = tmp_df.columns.get_loc("Revenue_Growth")
  logging.debug("The column index for EPS_Growth is " + str(eps_growth_col_idx))
  logging.debug("The column index for Revenue_Growth is " + str(revenue_growth_col_idx))
  # The column header starts with (0, 0)...(0, n - 1).The row header starts with (1, -1)...(n, -1)
  for key, cell in qtr_table_plt_inst.get_celld().items():
    row_idx = key[0]
    col_idx = key[1]
    cell_val = cell.get_text().get_text()
    logging.debug("Row idx " + str(row_idx) + " Col idx " + str(col_idx) + " Value " + str(cell_val))

    # -----------------------------------------------------
    # Set the row headers and columns to bold
    # -----------------------------------------------------
    if ((row_idx == 0) or (col_idx < 0)):
      cell.get_text().set_fontweight('bold')
    # -----------------------------------------------------

    # -----------------------------------------------------
    # Set the colors every alternating rows
    # -----------------------------------------------------
    if (row_idx % 2 == 0):
      qtr_table_plt_inst[(row_idx, col_idx)].set_facecolor('seashell')
    else:
      qtr_table_plt_inst[(row_idx, col_idx)].set_facecolor('azure')
    # -----------------------------------------------------

    # -----------------------------------------------------
    # Change the Date format to be shorter
    # -----------------------------------------------------
    if (col_idx == -1):
      x_date = dt.datetime.strptime(cell_val,'%m/%d/%Y').date()
      x = dt.datetime.strftime(x_date, '%m/%y')
      logging.debug("The date is " + str(x))
      cell.get_text().set_text(x)
    # -----------------------------------------------------

    # -----------------------------------------------------
    # Change the heading of the various row according to the liking of the user
    # -----------------------------------------------------
    if (row_idx == 0):
      if (col_idx == revenue_col_idx):
        x = "Rev #"
      if (col_idx == revenue_growth_col_idx):
        x = "Rev %"
      if (col_idx == eps_col_idx):
        x = "EPS #"
        cell.get_text().set_text(x)
      if (col_idx == eps_growth_col_idx):
        x = "EPS %"
      cell.get_text().set_text(x)
    # -----------------------------------------------------

    # -----------------------------------------------------
    # Change
    # -----------------------------------------------------
    if (((col_idx == eps_growth_col_idx) or (col_idx == revenue_growth_col_idx)) and (row_idx > 0)):
      if (cell_val == 'nan'):
        x = "-"
        cell.get_text().set_text(x)
      else:
        x =  f'{float(cell.get_text().get_text()):.1f}'
        x = x + "%"
        cell.get_text().set_text(x)
      # if (row_idx == current_assets_row_idx):
      #   x = f'{int(float(cell_val)):,}'
        # This works - for now comment out as I try to think whether to have % here or not
        # if (row_idx == revenue_row_idx):
          # x = x + "%"
    # -----------------------------------------------------

    # -----------------------------------------------------
    # -----------------------------------------------------
    # -----------------------------------------------------
    if ((col_idx == revenue_col_idx) and (row_idx > 0 ) and (col_idx > -1)):
      if (cell_val == 'nan'):
        x = "-"
        cell.get_text().set_text(x)
      else:
        x_int = int(float(cell_val))
        x = human_format(x_int)
        cell.get_text().set_text(x)
    if ((col_idx == eps_col_idx) and (row_idx > 0 ) and (col_idx > -1)):
      if (cell_val == 'nan'):
        x = "-"
        cell.get_text().set_text(x)
      else:
        x =  f'{float(cell.get_text().get_text()):.2f}'
        cell.get_text().set_text(x)
        cell.get_text().set_text(x)
      # -----------------------------------------------------
      # else:
      #   x =  f'{float(cell.get_text().get_text()):.2f}'


    # if float(cell_val) < 0:
    #   cell.get_text().set_color('Red')
    #   cell.get_text().set_fontstyle('italic')
    #   qtr_table_plt_inst[(row_idx, col_idx)].set_facecolor('lightpink')

  qtr_table_plt.axis('off')
  logging.info("Done with plotting QTR table...")
  # ---------------------------------------------------------------------------


  # ---------------------------------------------------------------------------
  # Plot the Key Numbers table
  # ---------------------------------------------------------------------------
  key_numbers_plt.title.set_text("Key Numbers")
  key_numbers_plt.set_facecolor("lightgrey")
  key_numbers_plt.set_yticks([])
  key_numbers_plt.set_xticks([])
  key_numbers_plt_inst = key_numbers_plt.table(cellText=[[1,5,9], [2,4,8]], rowLabels=['row1', 'row2'], colLabels=['col1', 'col2','col3'],loc="upper center")
  # yr_table_plt.table(cellText=[[3, 3], [4, 4]], loc='upper center',rowLabels=['row1', 'row2'], colLabels=['col1', 'col2'])
  key_numbers_plt_inst[(1,0)].set_facecolor("#56b5fd")
  key_numbers_plt.axis('off')
  # ---------------------------------------------------------------------------


  # ---------------------------------------------------------------------------
  # Plot the Yearly Numbers table
  # ---------------------------------------------------------------------------
  yr_table_plt.set_title("Yearly Table",color='Blue')
  yr_table_plt.set_facecolor("black")
  yr_table_plt.set_yticks([])
  yr_table_plt.set_xticks([])

  # fixme : todo : Maybe remove the rows here and only keep the rows that we
  #  want to display rather than creating two different dataframes
  # or crate the separate dataframe here as a subset of the yr_df
  yr_table_plt_inst = yr_table_plt.table(cellText=ticker_yr_numbers_df.values, rowLabels=ticker_yr_numbers_df.index,colWidths=[0.1] * len(ticker_yr_numbers_df.columns),colLabels=ticker_yr_numbers_df.columns,loc="upper center")

  logging.debug("")
  logging.debug("Will now set the appropriate cell colors in the dataframe")

  # Get the row numbers for various row headings. These can be used later to format the data
  # in the respective rows
  lt_debt_row_idx =  ticker_yr_numbers_df.index.get_loc('LT_Debt') + 1
  # current_assets_row_idx =  ticker_yr_numbers_df.index.get_loc('Current_Assets') + 1
  revenue_row_idx =  ticker_yr_numbers_df.index.get_loc('Revenue') + 1
  # logging.debug("The row_idx corresponding to index Current_Assets is " + str(current_assets_row_idx))
  # The column header starts with (0, 0)...(0, n - 1).The row header starts with (1, -1)...(n, -1)
  for key, cell in yr_table_plt_inst.get_celld().items():
    row_idx = key[0]
    col_idx = key[1]
    cell_val = cell.get_text().get_text()
    logging.debug("Row idx " + str(row_idx) + " Col idx " + str(col_idx) + " Value " + str(cell_val))

    if (row_idx % 2 == 0):
      yr_table_plt_inst[(row_idx, col_idx)].set_facecolor('seashell')
    else:
      yr_table_plt_inst[(row_idx, col_idx)].set_facecolor('azure')

    if ((row_idx == 0) or (col_idx < 0)):
      cell.get_text().set_fontweight('bold')
    elif (cell_val == 'nan'):
      x = "-"
      cell.get_text().set_text(x)
    else:
      # if (row_idx == current_assets_row_idx):
      #   x = f'{int(float(cell_val)):,}'
        # This works - for now comment out as I try to think whether to have % here or not
        # if (row_idx == revenue_row_idx):
          # x = x + "%"
      if ((row_idx == revenue_row_idx) or (row_idx == lt_debt_row_idx)):
        x_int = int(float(cell_val))
        x = human_format(x_int)
      else:
        x =  f'{float(cell.get_text().get_text()):.2f}'

      cell.get_text().set_text(x)

      if float(cell_val) < 0:
        cell.get_text().set_color('Red')
        cell.get_text().set_fontstyle('italic')
        yr_table_plt_inst[(row_idx, col_idx)].set_facecolor('lightpink')

  yr_table_plt.axis('off')
  logging.info("Done with plotting YR table...")
  # ---------------------------------------------------------------------------


  plt.show()

  logging.debug("All Done")



















  # table_props = yr_table_plt_inst.properties()
  # logging.debug("The dictionary of table properties is \n" + str(table_props))
  # table_cells = table_props['child_artists']
  # for cell in table_cells:
  #   cell_val = cell.get_text()
  #   logging.debug("The cell is " + str(cell) + " and the value is " + str(cell_value) + " and the color is " + str(cell_val.get_color()))
  #   # cell_val.set_color('green')
  #   cell_val.set_text("HAHA")
  #   logging.debug("The cell is " + str(cell) + " and the value is " + str(cell_val) + " and the color is " + str(cell_val.get_color()))
  #   # logging.debug("Now the color is " + str(cell_val.get_color()))


  # for row_idx in range(len(ticker_yr_numbers_df.values)):
  #   logging.debug("\nThe row idx is " + str(row_idx) + " and the row value is " + str(ticker_yr_numbers_df.index[row_idx]))
  #   row_val_list = ticker_yr_numbers_df.iloc[row_idx]
  #   logging.debug("The columns corresponding to the row idx " + str(row_idx) + " are\n" + str(row_val_list))
  #   for col_idx in range(len(row_val_list)):
  #     logging.debug("The col idx is " + str(col_idx) + " and the value is " + str(row_val_list[col_idx]))
  #     if (row_val_list[col_idx] < 0):
  #       yr_table_plt_inst[(row_idx+1, col_idx)].set_facecolor('grey')


  # https://pandas.pydata.org/pandas-docs/stable/user_guide/visualization.html
  # https://stackoverflow.com/questions/32137396/how-do-i-plot-only-a-table-in-matplotlib
  # https: // stackoverflow.com / questions / 28681782 / create - table - in -subplot
  # https://stackoverflow.com/questions/41151165/how-to-add-a-table-that-only-contains-strings-to-a-matplotlib-graph
  # https://stackoverflow.com/questions/11623056/matplotlib-using-a-colormap-to-color-table-cell-background
  # https://matplotlib.org/api/_as_gen/matplotlib.pyplot.table.html

  # dc = pd.DataFrame({'A': [1, 2, 3, 4], 'B': [4, 3, 2, 1], 'C': [3, 4, 2, 2]})
  #
  # plt.plot(dc)
  # plt.legend(dc.columns)
  # dcsummary = pd.DataFrame([dc.mean(), dc.sum()], index=['Mean', 'Total'])
  #
  # plt.table(cellText=ticker_yr_numbers_df.values, rowLabels=ticker_yr_numbers_df.index,colWidths=[0.25] * len(ticker_yr_numbers_df.columns),
  #           colLabels=ticker_yr_numbers_df.columns,
  #           cellLoc='center', rowLoc='center',
  #           loc='bottom')
  #
  #
  # fig = plt.gcf()
  #
  # plt.show()
  # logging.info("\nDone " + str(ticker))
  #

