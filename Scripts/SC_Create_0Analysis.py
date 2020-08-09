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
# Maybe start with 5 quarters and see if that makes sense...we can inrease it to 8 quaters too.
# Zebras like Market Smith -- for EPS and Revenue for 5 quarters
# Share count Diluted  - 5 quarters -- Maybe add in the yr_dataframe too
# Number of Employees - 5 quarters
# Inventory Change - 5 Quarters
# Institutional Shares Sold vs Institutional Shares Purchased - 5 quarters
# Insiders buying / selling?  (Net Insiders buy Insiders-net shares purchased or Net Insider Buys % Shares Out or Net Insider Buys % Shares Out.) - 5 quarters

# Key Statistic
# Equity to Debt
# Current Ratio - Just this quarter
# Debt to equity - Just this quarter
# price to sales - Just this quarter

# Phil Town Stuff -- Are these growth numbers?
# Free Cash flow per share Growth  - 10 years
# ROIC Growth  - 10 years


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
ticker_list = ['MED']
for ticker_raw in ticker_list:

  ticker = ticker_raw.replace(" ", "").upper()  # Remove all spaces from ticker_raw and convert to uppercase
  logging.info("========================================================")
  logging.info("Processing for " + ticker)
  logging.info("========================================================")
  if (ticker in ["QQQ"]):
    logging.debug(str(ticker) + " is NOT in AAII df or is QQQ (etf). Will skip inserting EPS Projections..")
    continue

  # Read the ticker AAII data yr and qtr file to start
  ticker_datain_yr_file = ticker +  "_yr_data.csv"
  ticker_datain_yr_df = pd.read_csv(dir_path + analysis_dir + "\\" + "Yearly" + "\\" + ticker_datain_yr_file)
  ticker_datain_yr_df.set_index("AAII_YR_DATA",inplace=True)
  logging.debug("The YR datain df \n" + ticker_datain_yr_df.to_string())

  # Remove the rows that are not needed, if that is ever needed
  # ticker_datain_yr_df.drop(index= ['XYZ'], inplace=True)
  logging.debug("The YR datain df are removing the unwanted rows \n" + ticker_datain_yr_df.to_string())

  # ===========================================================================
  # Now we have a dataframe that we need to make calculation for our 0_Analysis
  # Various dateframes can be generated off the dataframes that we have read in.
  # Those generated dataframes can be reprensed as tables and or used to create
  # graphs later on
  # ===========================================================================

  # ---------------------------------------------------------------------------
  # Yearly numbers dataframe
  # ---------------------------------------------------------------------------
  ticker_yr_numbers_df = ticker_datain_yr_df.copy()
  logging.debug("The YR Peter Lynch df \n" + ticker_yr_numbers_df.to_string())
  col_list = ticker_yr_numbers_df.columns.tolist()

  # These rows are not needed for now
  ticker_yr_numbers_df.drop(index= ['Current_Assets'], inplace=True)
  ticker_yr_numbers_df.drop(index= ['Dividend'], inplace=True)
  ticker_yr_numbers_df.drop(index= ['Short_Term_Debt'], inplace=True)
  # The rearragne to row to your liking
  ticker_yr_numbers_df = ticker_yr_numbers_df.loc[['Revenue', 'Diluted_EPS', 'BV_Per_Share', 'LT_Debt'], :]
  # First convert the numbers raw numbers (like the revenue is in millions etc)
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

  col_list = ticker_yr_numbers_df.columns.tolist()
  desired_growth_rate = .1
  base_growth_numbers_list = []
  for col_idx in range(len(col_list)):
    base_growth_numbers_list.append(float('nan'))
    if (col_idx == 0):
      base_growth_numbers_list[col_idx] = 1
    else:
      base_growth_numbers_list[col_idx] = base_growth_numbers_list[col_idx-1]*(1+desired_growth_rate)
  # Reverse the list
  # base_growth_numbers_list = base_growth_numbers_list[::-1]
  logging.debug("The base growth numbers list is " + str(base_growth_numbers_list))
  ticker_yr_growth_df = ticker_yr_growth_df.append(pd.Series(base_growth_numbers_list, index=ticker_yr_growth_df.columns, name='Base_Growth'))
  # Add token growth rate rows -- these will be populated properly below
  ticker_yr_growth_df = ticker_yr_growth_df.append(pd.Series(base_growth_numbers_list, index=ticker_yr_growth_df.columns, name='Revenue_Growth'))
  ticker_yr_growth_df = ticker_yr_growth_df.append(pd.Series(base_growth_numbers_list, index=ticker_yr_growth_df.columns, name='Diluted_EPS_Growth'))
  ticker_yr_growth_df = ticker_yr_growth_df.append(pd.Series(base_growth_numbers_list, index=ticker_yr_growth_df.columns, name='BV_Per_Share_Growth'))

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

  ticker_yr_growth_df = ticker_yr_growth_df.loc[['Base_Growth', 'Revenue_Growth', 'Diluted_EPS_Growth', 'BV_Per_Share_Growth'], :]
  logging.debug("The YR Growth dataframe now is \n" + ticker_yr_growth_df.to_string())
  # ---------------------------------------------------------------------------



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
  fig = plt.figure()
  fig.set_size_inches(14.431, 7.639)  # Length x height

  main_plt = plt.subplot2grid((5, 6), (0, 0), rowspan=3,colspan=5)
  table1_plt = plt.subplot2grid((5, 6), (0, 5), rowspan=3, colspan=1)
  table2_plt = plt.subplot2grid((5, 6), (4, 0), rowspan=1, colspan=6)
  plt.subplots_adjust(hspace=0, wspace=.35)
  fig.suptitle("Analysis for " + ticker)
  main_plt.title.set_text("Maybe some Chart")
  table1_plt.title.set_text("Key Numbers")
  table2_plt.set_title("Yearly Table",color='Blue')

  main_plt.set_facecolor("lightgrey")
  table1_plt.set_facecolor("lightgrey")
  table2_plt.set_facecolor("black")

  # ---------------------------------------------------------------------------
  # Main plt with grwoth rates
  # ---------------------------------------------------------------------------
  # Some plotting numbers for main plot - can be replaced by actual data later
  # main_plt.plot([1, 2, 3])
  # main_plt.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
  # main_plt.set_ylim(qtr_eps_lim_lower, qtr_eps_lim_upper)
  # main_plt.tick_params(axis="y", direction="in", pad=-22)
  # main_plt.set_yscale(chart_type_idx)
  # main_plt_inst = main_plt.plot(date_list[0:plot_period_int], qtr_eps_expanded_list[0:plot_period_int], label='Q EPS', color="deeppink", marker='.', markersize='10')

  main_plt_lim_lower = 0
  main_plt_lim_upper = 3
  main_plt.set_ylim(main_plt_lim_lower, main_plt_lim_upper)
  main_plt.tick_params(axis="y", direction="in", pad=-22)
  # main_plt.set_yscale(Linear)
  col_list = ticker_yr_growth_df.columns.tolist()

  # Extract the various growth numbers here
  yr_revenue_growth_rate = ticker_yr_growth_df.loc["Revenue_Growth"]
  main_plt_inst = main_plt.plot(ticker_yr_growth_df.columns.tolist(), base_growth_numbers_list, label='Q EPS', color="deeppink", marker='.', markersize='24')
  main_plt_inst = main_plt.plot(ticker_yr_growth_df.columns.tolist(), ticker_yr_growth_df.loc["Revenue_Growth"], label='Q EPS', color="green", marker='.', markersize='10')
  main_plt_inst = main_plt.plot(ticker_yr_growth_df.columns.tolist(), ticker_yr_growth_df.loc["Diluted_EPS_Growth"], label='Q EPS', color="blue", marker='.', markersize='10')
  main_plt_inst = main_plt.plot(ticker_yr_growth_df.columns.tolist(), ticker_yr_growth_df.loc["BV_Per_Share_Growth"], label='Q EPS', color="brown", marker='.', markersize='10')
  # ---------------------------------------------------------------------------



  # ---------------------------------------------------------------------------
  # Plot the first table
  # ---------------------------------------------------------------------------
  table1_plt.set_yticks([])
  table1_plt.set_xticks([])
  table1_plt_inst = table1_plt.table(cellText=[[1,5,9], [2,4,8]], rowLabels=['row1', 'row2'], colLabels=['col1', 'col2','col3'],loc="upper center")
  # table2_plt.table(cellText=[[3, 3], [4, 4]], loc='upper center',rowLabels=['row1', 'row2'], colLabels=['col1', 'col2'])
  table1_plt_inst[(1,0)].set_facecolor("#56b5fd")
  table1_plt.axis('off')
  # ---------------------------------------------------------------------------


  # ---------------------------------------------------------------------------
  # Plot the 2nd table
  # ---------------------------------------------------------------------------
  table2_plt.set_yticks([])
  table2_plt.set_xticks([])

  table2_plt_inst = table2_plt.table(cellText=ticker_yr_numbers_df.values, rowLabels=ticker_yr_numbers_df.index,colWidths=[0.1] * len(ticker_yr_numbers_df.columns),colLabels=ticker_yr_numbers_df.columns,loc="upper center")

  logging.debug("")
  logging.debug("Will now set the appropriate cell colors in the dataframe")

  # Get the row numbers for various row headings. These can be used later to format the data
  # in the respective rows
  lt_debt_row_idx =  ticker_yr_numbers_df.index.get_loc('LT_Debt') + 1
  # current_assets_row_idx =  ticker_yr_numbers_df.index.get_loc('Current_Assets') + 1
  revenue_row_idx =  ticker_yr_numbers_df.index.get_loc('Revenue') + 1
  # logging.debug("The row_idx corresponding to index Current_Assets is " + str(current_assets_row_idx))
  # The column header starts with (0, 0)...(0, n - 1).The row header starts with (1, -1)...(n, -1)
  for key, cell in table2_plt_inst.get_celld().items():
    row_idx = key[0]
    col_idx = key[1]
    cell_val = cell.get_text().get_text()
    logging.debug("Row idx " + str(row_idx) + " Col idx " + str(col_idx) + " Value " + str(cell_val))

    if (row_idx % 2 == 0):
      table2_plt_inst[(row_idx, col_idx)].set_facecolor('seashell')
    else:
      table2_plt_inst[(row_idx, col_idx)].set_facecolor('azure')

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
        table2_plt_inst[(row_idx, col_idx)].set_facecolor('lightpink')

  table2_plt.axis('off')
  # ---------------------------------------------------------------------------


  plt.show()

  logging.debug("All Done")



















  # table_props = table2_plt_inst.properties()
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
  #       table2_plt_inst[(row_idx+1, col_idx)].set_facecolor('grey')


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

