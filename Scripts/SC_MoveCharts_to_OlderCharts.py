import pandas as pd
import os
import sys
import time
import datetime as dt
import numpy as np
import re
import shutil
import glob
import logging
from dateutil.relativedelta import relativedelta

# -----------------------------------------------------------------------------
# Read the master tracklist file into a dataframe
# -----------------------------------------------------------------------------
dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
chart_dir = "\\..\\" + "Charts"
charts_latest_dir = "\\..\\" + "Latest_Charts"
older_charts_dir = "\\..\\" + "Older_Charts"
log_dir = "\\..\\" + "Logs"

master_tracklist_file = "Master_Tracklist.xlsm"
master_tracklist_df = pd.read_excel(dir_path + user_dir + "\\" + master_tracklist_file, sheet_name="Main")
master_tracklist_df.sort_values('Tickers', inplace=True)
ticker_list_unclean = master_tracklist_df['Tickers'].tolist()
ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']
master_tracklist_df.set_index('Tickers', inplace=True)
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
# Logging Levels
# Level
# CRITICAL
# ERROR
# WARNING
# INFO
# DEBUG
# NOTSET
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename=dir_path + log_dir + "\\" + 'SC_MoveCharts_to_OlderCharts_debug.txt',
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
# -----------------------------------------------------------------------------


# ---------------------------------------------------------
# Define the date for the charts to get compared - All older charts
# than this date will be moved to older_charts_dir
# Sundeep : 01/22/2023 - Now that I am creating Long Liner charts by default
# the number of charts created have doubled, so we need only last 6 months charts
# in the Charts directory (and move everything to Older_Charts).
# Otherwise the size and the number of charts in the charts directory
# increases to the extent that it becomes cumbersome to manage it.
# date_1year_ago_dt = dt.datetime.now() - relativedelta(months=12)
date_6mon_ago_dt = dt.datetime.now() - relativedelta(months=6)
# ---------------------------------------------------------

chart_styles_list = ['Linear', 'Long_Linear', 'Log']
# chart_styles_list = ['Log']
# chart_styles_list = ['Linear']

chart_annotations_list = ['Charts_With_Numbers', 'Charts_Without_Numbers']
# chart_annotations_list = ['Charts_With_Numbers']
# chart_annotations_list = ['Charts_Without_Numbers']

for chart_styles_idx in chart_styles_list:
  logging.debug("==========> Style of Charts to be Moved : " + str(chart_styles_idx) + " <==========")
  for chart_annotations_idx in chart_annotations_list:
    no_of_files_moved = 0
    logging.info("")
    logging.info("===================================================================")
    logging.info("==========> Moving files for : " + str(chart_styles_idx) + "/" + str(chart_annotations_idx))
    time.sleep(3)
    chart_styles_and_annotations = chart_styles_idx + "/" + chart_annotations_idx
    source_dir = dir_path + chart_dir + "\\" + chart_styles_idx + "\\" + chart_annotations_idx + "\\"
    dest_dir = dir_path + older_charts_dir + "\\" + chart_styles_idx + "\\" + chart_annotations_idx + "\\"


    all_chart_files_list=os.listdir(source_dir)
    logging.debug("")
    logging.debug("List of all the files in the Source Chart Directory \n" + str(source_dir) + " are : \n" + str(all_chart_files_list))

    # Get the whole list of jpg files here
    jpg_file_list = glob.glob(source_dir + "*.jpg" )
    logging.debug("The Chart files in source directory are \n" + str(jpg_file_list))

    # -----------------------------------------------------
    # Iterate through the jpg_file_list and split each filename
    # to separate the directory path from filename.
    # Then append the ticker name to the ticker_list_with_duplicates list
    # as there would be multiple files for a specific ticker (with multiple date_str)
    # -----------------------------------------------------
    logging.debug("")
    logging.debug(str(chart_styles_and_annotations) + " : Start : Now beginning to extract all the ticker names from the source directory\n")
    ticker_list_with_duplicates = []
    for filename_with_path in jpg_file_list:
      logging.debug("The full filename is " + str(filename_with_path))
      head,ticker_name_with_chart_style_and_date_str = os.path.split(filename_with_path)
      logging.debug("The ticker name string with date  : " + str(ticker_name_with_chart_style_and_date_str))
      ticker_name = ticker_name_with_chart_style_and_date_str.split('_')[0]
      logging.debug("Ticker :" + str(ticker_name))
      ticker_list_with_duplicates.append(ticker_name)

    logging.debug("")
    logging.debug("----------------------------------------------------------")
    logging.debug(str(chart_styles_and_annotations) + " : The ticker list (with potential duplicates) \n " + str(ticker_list_with_duplicates))
    # Remove duplicates from the list to get unique ticker name in the ticker_list
    ticker_list = []
    [ticker_list.append(x) for x in ticker_list_with_duplicates if x not in ticker_list]
    logging.debug(str(chart_styles_and_annotations) + " : The ticker list without duplicates \n " + str(ticker_list))
    logging.debug("----------------------------------------------------------")
    # -----------------------------------------------------


    # -----------------------------------------------------
    # Now for each ticker :
    # 1. Get the list of the all the jpg files
    # This could not have been done in the last step because
    # it is not guaranteed that filenames_with_path would be
    # sorted and even if it was sorted, it would have made the
    # last loop more complicated when the ticker name changes
    # from, say xxx to yyy and then back to xxx
    #
    # 2. For each ticker in the ticker_chart_files_list,
    # extract the date string and compare it against the date
    # that user wants to compare it against and store the ticker
    # file that have older date string in a separate list that
    # will be used to move the files
    # -----------------------------------------------------
    for ticker in ticker_list:
      display_str = ticker + " (" + chart_styles_and_annotations + ") : "
      my_regex = re.compile(re.escape(ticker) + re.escape("_") + ".*jpg")
      ticker_chart_files_list = list(filter(my_regex.match, all_chart_files_list))
      logging.debug("")
      logging.debug("------------------------------------------")
      logging.debug(str(display_str) + "ALL the chart files are \n" + str(ticker_chart_files_list))
      logging.debug(str(display_str) + "Iterating through the list to extract date and compare it against : " + str(date_6mon_ago_dt))
      ticker_chart_to_move_list = []
      logging.debug("------------------------------------------")
      for ticker_chart_filename_with_date_str in ticker_chart_files_list:
        ticker_chart_date_str = (ticker_chart_filename_with_date_str[:-4])[-10:]
        ticker_chart_date_dt = dt.datetime.strptime(ticker_chart_date_str, "%Y_%m_%d")
        logging.debug("The date string for " + str(ticker_chart_filename_with_date_str) + " is " + str(ticker_chart_date_str) + ", and the datetime is " + str(ticker_chart_date_dt))
        if (date_6mon_ago_dt >= ticker_chart_date_dt):
          logging.debug(str(ticker_chart_filename_with_date_str) + " : ***** Found Older Chart : The chart date : " + str(ticker_chart_date_dt) + ", is older than : " + str(date_6mon_ago_dt) + ", so it will be moved")
          ticker_chart_to_move_list.append(ticker_chart_filename_with_date_str)
      logging.debug("------------------------------------------")
      logging.debug(str(display_str) + "The list of files that will be moved \n" + str(ticker_chart_to_move_list))
      # -----------------------------------------------------

      # -----------------------------------------------------
      # Now do the actual move the files
      # -----------------------------------------------------
      logging.debug("------------------------------------------")
      for ticker_to_move in ticker_chart_to_move_list:
        ticker_chart_date_yr = (ticker_to_move[:-4])[-10:-6]
        # logging.debug("The year is " +str(ticker_chart_date_yr))
        source_file_with_path = source_dir + ticker_to_move
        dest_dir = dir_path + older_charts_dir + "\\" + ticker_chart_date_yr + "\\" + chart_styles_idx + "\\" + chart_annotations_idx + "\\"
        dest_file_with_path = dest_dir + ticker_to_move
        logging.info(str(display_str) + "Moving chart file " + str(ticker_to_move))
        logging.debug(str(display_str) + "Moving chart file (Full path names) \n" + source_file_with_path + " to \n" + (dest_file_with_path))
        shutil.move(source_file_with_path, dest_file_with_path)
        no_of_files_moved =   no_of_files_moved+1
        logging.debug("")

      logging.debug(str(display_str) + "Done moving the older files")
      logging.debug("------------------------------------------")
      logging.debug("")

    logging.info("")
    logging.info("==========> Moved files for : " + str(chart_styles_idx) + "/" + str(chart_annotations_idx))
    logging.info("==========> TOTAL FILES MOVED : " + str(no_of_files_moved))
    logging.info("===================================================================")

logging.info("")
logging.info(".....ALL DONE.....")
