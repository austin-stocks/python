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

#
# Define the directories and the paths
dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
historical_dir = "\\..\\" + "Historical"
earnings_dir = "\\..\\" + "Earnings"
dividend_dir = "\\..\\" + "Dividend"
log_dir = "\\..\\" + "Logs"
analysis_dir = "\\..\\" + "Analysis"
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

  # Read the ticker AAII data yr and qtr file to start
  ticker_datain_yr_file = ticker +  "_yr_data.csv"
  ticker_datain_yr_df = pd.read_csv(dir_path + analysis_dir + "\\" + "Yearly" + "\\" + ticker_datain_yr_file)
  ticker_datain_yr_df.set_index("AAII_YR_DATA",inplace=True)
  logging.debug("The YR datain df \n" + ticker_datain_yr_df.to_string())

  # Remove the rows that are not needed, if that is ever needed
  ticker_datain_yr_df.drop(index= ['XYZ'], inplace=True)
  logging.debug("The YR datain df are removing the unwanted rows \n" + ticker_datain_yr_df.to_string())

  # ---------------------------------------------------------------------------
  # Now we have a dataframe that we need to make calculation for our 0_Analysis
  # ---------------------------------------------------------------------------
  ticker_yr_lynch_df = ticker_datain_yr_df.copy()
  logging.debug("The YR Peter Lynch df \n" + ticker_yr_lynch_df.to_string())
  col_list = ticker_yr_lynch_df.columns.tolist()
  for col_idx in range(len(col_list)-1):
    col_val = col_list[col_idx]
    col_val_prev = col_list[col_idx+1]
    logging.debug("Creating Revenue Growth % for : " + str(col_val))
    ticker_yr_lynch_df.loc['Revenue', col_val] = 100 * (ticker_datain_yr_df.loc['Revenue', col_val] - ticker_datain_yr_df.loc['Revenue', col_val_prev] ) / ticker_datain_yr_df.loc['Revenue', col_val_prev]
    ticker_yr_lynch_df.loc['Diluted_EPS', col_val] = 100 * (ticker_datain_yr_df.loc['Diluted_EPS', col_val] - ticker_datain_yr_df.loc['Diluted_EPS', col_val_prev] ) / ticker_datain_yr_df.loc['Diluted_EPS', col_val_prev]

  logging.debug("The YR Peter Lynch df \n" + ticker_yr_lynch_df.to_string())



  # ---------------------------------------------------------------------------
  ticker_yr_lynch_df.applymap(lambda x: str(int(x)) if abs(x - int(x)) < 1e-6 else str(round(x, 2)))

  fig = plt.figure()
  fig.set_size_inches(14.431, 7.639)  # Length x height

  main_plt = plt.subplot2grid((5, 6), (0, 0), colspan=5, rowspan=4)
  table1_plt = plt.subplot2grid((5, 6), (0, 5), colspan=1, rowspan=4)
  table2_plt = plt.subplot2grid((5, 6), (4, 0), colspan=6, rowspan=2)
  plt.subplots_adjust(hspace=0, wspace=0)



  main_plt.plot([1, 2, 3])

  table1_plt.set_yticks([])
  table1_plt.set_xticks([])
  # table1_plt.xaxis.set_visible(False)
  # table1_plt.yaxis.set_visible(False)

  table2_plt.set_yticks([])
  table2_plt.set_xticks([])

  table1_plt_inst = table1_plt.table(cellText=[[1, 1], [2, 2]], rowLabels=['row1', 'row2'], colLabels=['col1', 'col2'])
  # table2_plt.table(cellText=[[3, 3], [4, 4]], loc='upper center',rowLabels=['row1', 'row2'], colLabels=['col1', 'col2'])
  table1_plt.axis('off')


  table2_plt_inst = table2_plt.table(cellText=ticker_yr_lynch_df.values, rowLabels=ticker_yr_lynch_df.index,colWidths=[0.1] * len(ticker_yr_lynch_df.columns),colLabels=ticker_yr_lynch_df.columns)
            # cellLoc='center', rowLoc='center',
            # loc='bottom')
  table2_plt.axis('off')
  table2_plt_inst.auto_set_font_size(False)
  table2_plt_inst.set_fontsize(12)

  plt.show()

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
  # plt.table(cellText=ticker_yr_lynch_df.values, rowLabels=ticker_yr_lynch_df.index,colWidths=[0.25] * len(ticker_yr_lynch_df.columns),
  #           colLabels=ticker_yr_lynch_df.columns,
  #           cellLoc='center', rowLoc='center',
  #           loc='bottom')
  #
  #
  # fig = plt.gcf()
  #
  # plt.show()
  # logging.info("\nDone " + str(ticker))
  #

logging.debug("All Done")
