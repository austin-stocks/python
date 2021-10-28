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
import tkinter as tk


#
# Define the directories and the paths
dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
msmith_dir  = "\\..\\IBD\MarketSmith"
log_dir = "\\..\\" + "Logs"
# ---------------------------------------------------------------------------
# Set Logging
# critical, error, warning, info, debug
# set up logging to file - see previous section for more details
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename=dir_path + log_dir + "\\" + 'SC_compare_MSGL_MSGL_MasterTL_debug.txt',
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
# Read the MS Growth List Date string
# -----------------------------------------------------------------------------
root = tk.Tk()

# setting the windows size
root.geometry("600x400")
# declaring string variable for storing name and password
name_var = tk.StringVar()

# defining a function that will get the name and password and print them on the screen
def submit():
  name = name_var.get()
  print("The name is : " + name)

# creating a label for name using widget Label
name_label = tk.Label(root, text='Date(Dir) of MarketSmith GL file', font=('calibre', 10, 'bold'))

# creating a entry for input name using widget Entry
name_entry = tk.Entry(root, textvariable=name_var, font=('calibre', 10, 'normal'))

# creating a button using the widget Button that will call the submit function
sub_btn = tk.Button(root, text='Submit', command=submit)

# placing the label and entry in the required position using grid method
name_label.grid(row=0, column=0)
name_entry.grid(row=0, column=1)
sub_btn.grid(row=1, column=1)

# performing an infinite loop
# for the window to display
root.mainloop()
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# msgl == Market Smith Growth List
# This program read three files:
# 1. msgl 250 from a directory specified by the usr (through a date string
#    that is ready by tk box). This file is updated weekly in Market Smith
#    and sundeep tries to get it every week
# 2. msgl 250 running file - from MSmith root(home) dir in IBD dir
# 3. MasterTracklist file  
# After reading all the three files, it
# 1. Compares the tickers present in the msgl file specified by the date_str (through
#    the tk user input) with the tickers present in the msgl running file and finds
#    out which tickers are new in the msgl date_str and so need to be potentially added
#    to the msgl running file (not all tickers may not be added, as the msgl running
#    file can have a sheet that will have tickers that sundeep has already analyzed
#    and figured that they do not need to be analyzed further (and tracked further)
#    So they, even though could be new in the msgl date_str file, would be excluded from
#    getting added to the running file)
# 2. Once it find out which tickers can be potentially added, it puts them in a df and
#    lines up the columns (makes the columns same, both the number of columns and the
#    order of columns) with the msgl running file top row. This step is needed
#    because sundeep could have (almost certainly has) added columns to the msgl running
#    file to capture more information about the stocks that he is analyzing (like whether
#    we need to make a chart for the ticker, what are his "notes" about the ticker etc).
#    Doing this step enables the newly added tickers to be just "copied and pasted" from
#    the output file that is spit out from this program, into msgl running file
# 3. Once the columns are lined up, it then compares the tickers in the dataframe
#    with the tickers in the MasterTracklist file and finds out which ones are
#    we already tracking in the MasterTracklist. Ones that we are tracked are tagged
#    with a "Yes" in the "Wheat" column of the dataframe, otherwise they are tagged "No"
# 4. Now - since we have the dataframe that has all the potential tickers that can be
#    added, and that df is in the right format (has the same number and order of columns
#    as the msgl running file) we can go to step of excluding the tickers that are in the
#    "exclude" list. So - now the dataframe is split into two df (filtered based on
#    the tickers in the exclude list). One df will just have the tickers that are
#    in the exclude list. There is potentially nothing that needs to be done with
#    the df right now (until I think of something). That df is printed out as csv
#    in the logs directory. The onther df has all the newly added tickers that are
#    NOT in the exclude list. So this is our guy - the df that is printed out as
#    csv in the logs directory and can be copied and pasted in the msgl running file.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Print out the various files paths and read them into respective dateaframes
# -----------------------------------------------------------------------------
msgl_date_str_raw = str(name_var.get())
master_tracklist_file = "Master_Tracklist.xlsx"
msgl_dated_file = str(name_var.get()) + "_MarketSmith_Growth_250"
logging.info ("Reading Master Tracklist : " + master_tracklist_file)
logging.info ("Reading msg date_str file : " + dir_path + msmith_dir + "\\" + str(name_var.get()) + "\\" + msgl_dated_file)
logging.info ("Reading msgl running file : " + dir_path + msmith_dir + "\\" + "MarketSmith_Growth_250_Running.xlsm")
master_tracklist_df = pd.read_excel(dir_path + user_dir + "\\" + master_tracklist_file, sheet_name="Main")
msgl_dated_df = pd.read_csv(dir_path + msmith_dir + "\\" + str(name_var.get()) + "\\" + msgl_dated_file + ".csv")
msgl_running_tracking_df = pd.read_excel(dir_path + msmith_dir + "\\" + "MarketSmith_Growth_250_Running.xlsm", sheet_name="Tracking")
msgl_exclude_tickers_df = pd.read_excel(dir_path + msmith_dir + "\\" + "MarketSmith_Growth_250_Running.xlsm", sheet_name="Do_Not_Track")

logging.debug("Master Tracklist \n\n" + master_tracklist_df.to_string())
logging.debug("\n\nMSGL date_str file : \n\n" + msgl_dated_df.to_string())
logging.debug("\n\nMSGL Running file - Sheet Tracking : \n\n" + msgl_running_tracking_df.to_string())
logging.debug("\n\nMSGL Running file - Sheet Exclude List : \n\n" + msgl_exclude_tickers_df.to_string())

master_ticker_list = master_tracklist_df['Tickers'].tolist()
msgl_datefile_ticker_list = msgl_dated_df['Symbol'].tolist()
msgl_running_ticker_list = msgl_running_tracking_df['Symbol'].tolist()
msgl_exclude_ticker_list = msgl_exclude_tickers_df['Symbol'].tolist()

logging.debug("Total Number of Tickers extracted from Master Tracklist " + str(len(master_ticker_list)))
logging.debug("Total Number of Tickers extracted from msgl date str file " + str(len(msgl_datefile_ticker_list)))
logging.debug("Total Number of Tickers extracted from msgl Running file - Tracking " + str(len(msgl_running_ticker_list)))
logging.debug("Total Number of Tickers extracted from msgl Running file - Exclude List " + str(len(msgl_exclude_ticker_list)))
logging.debug("The List of tickers extracted from Master Tacklist " + str(master_ticker_list))
logging.debug("The List of tickers extracted from msgl date str file " + str(msgl_datefile_ticker_list))
logging.debug("The List of tickers extracted from msgl Running file - Tracking " + str(msgl_running_ticker_list))
logging.debug("The List of tickers extracted from msgl Running file - Exclude List " + str(msgl_exclude_ticker_list))
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# iterate through msgl_dated file and see which tickers are NOT in
# msgl_running file and put those tickers in a list. If the ticker is
# not found in the msgl running list - which means it can be potentially
# new, but is found in the exclude ticker list, then add it to that list
# it as weil. This new_in_msgl_but_in_exclude_list will be used later to
# divide/filter the running_df into two dfs
# -----------------------------------------------------------------------------
logging.info("")
logging.info("Looping through msgl date_str and msgl running file to see which tickers are only present in msgl date_str file")
new_in_msgl_datefile_list = []
new_in_msgl_but_in_exclude_list = []
for ticker_raw in msgl_datefile_ticker_list:
  ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase
  # logging.debug("Looking for " + str(ticker) + " from Ann Trackist in Master Tracklist")
  if ticker not in msgl_running_ticker_list:
    logging.debug ("Did not find " + str(ticker) + " in MSGL Running file")
    new_in_msgl_datefile_list.append(ticker)
    if ticker in msgl_exclude_ticker_list:
      new_in_msgl_but_in_exclude_list.append(ticker)
      logging.debug("Did not find " + str(ticker) + " in MSGL Running file, but found it in exclude list")
  else:
    logging.debug ("Found " + str(ticker) + " in MSGL Running file")

logging.info("Found : " + str(len(new_in_msgl_datefile_list)) + " new tickers that were not in the msgl running file (and are ONLY present in msgl date_str file)")
logging.info("Found : " + str(len(new_in_msgl_but_in_exclude_list)) + " tickers out of those that are also in the exclude list (in msgl running file)")
logging.info("So, only ==> " + str(len(new_in_msgl_datefile_list) - len(new_in_msgl_but_in_exclude_list)) + " <== tickers will be added to msgl running file")
logging.debug("Found : " + str(new_in_msgl_datefile_list) + " tickers only in msgl date  file")
logging.debug("Found : " + str(new_in_msgl_but_in_exclude_list) + " tickers only in msgl date file that were also in exclude list")
logging.info("")

# Warn if either all the potentially new tickers found were in the exclude list or
# if there were no new ticker found in comparing the two msgl files
# This is highly unusual - and would result in empty csv file that lists tickers
# to be added to msgl running file...
if ((len(new_in_msgl_datefile_list) == len(new_in_msgl_but_in_exclude_list)) or (len(new_in_msgl_datefile_list) == 0)):
  logging.warning("============>      <============")
  logging.warning("Either no new tickers were found while comparing msgl date_str file with msgl running file OR...")
  logging.warning("All the potentially new tickers found were also in the exclude list")
  logging.warning("This is not necessarily an error, but highly unusual...Please check what is happening from the message above")
  logging.warning("============>      <============")
  logging.warning("")
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Based on the list of tickers that can be potentially added, prepare a new
# dataframe (starting from msgl_datefile_df) that ONLY has the tickers that
# can be potentially added eventually to msgl running file.
# (the list of tickers that need to be are in new_in_msgl_datefile_list from above)
# -----------------------------------------------------------------------------
msgl_dated_df.set_index('Symbol', inplace=True)
new_in_msgl_datefile_df = msgl_dated_df.loc[new_in_msgl_datefile_list, :]
# new_in_msgl_datefile_df.drop('Order', axis=1, inplace=True)
new_in_msgl_datefile_df.reset_index(inplace=True, drop=False)
logging.debug("The rows that are new in the dated file :" + new_in_msgl_datefile_df.to_string())
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Now get the columns newly of the newly created dataframe to line up (both the
# the number and the order of columns) with the columns in the msgl_running
# file. This is needed because sundeep could have deleted/added some columns
# (almost certainly has). This is also needed so that the new df - when printed
# out as csv can be simply copied and pasted into the msgl running file, rather
# than trying to line up the columns at that time
# -----------------------------------------------------------------------------
cols_msgl_running_tracking_df = msgl_running_tracking_df.columns.tolist()
cols_new_in_msgl_datefile_df = new_in_msgl_datefile_df.columns.tolist()
logging.debug("The columns in msgl running file are : " + str(cols_msgl_running_tracking_df))
logging.debug("The columns in msgl date str file are : " + str(cols_new_in_msgl_datefile_df))

# todo
# Need to check this scenario if msgl date_str df has a column that is not
# present in the msgl running file - this means that there was  column that
# sundeep deleted from msgl running file - and that can happen (right now that
# case does not exist and so the error and sys.exit).
# If that case arises tomorrow - say Sundeep deletes 200 day ma or avg. volume
# from msgl running file (as he sees no need for it) then modify the code below
# and allow that col. to be deleted from msgl data_str df as well
# (We can have a list of columns that need to be deleted and still then check
# But again - right now that case does not exist
for col_name in cols_new_in_msgl_datefile_df:
  if col_name not in cols_msgl_running_tracking_df:
    logging.error("The col name " + str(col_name) + " is in msgl date str file but NOT in msgl running file...Please check and rerun again")
    sys.exit(1)
for col_name in cols_msgl_running_tracking_df:
  if col_name not in cols_new_in_msgl_datefile_df:
    logging.debug("The column " + str(col_name) + " not found in msgl running file, adding it to msgl date str df")
    new_in_msgl_datefile_df.insert(1,col_name,"#NA#")

logging.debug("The dataframe that has the newly added tickers and same cols as msgl running file is : " + new_in_msgl_datefile_df.to_string())
new_in_msgl_datefile_df = new_in_msgl_datefile_df[cols_msgl_running_tracking_df]
logging.debug("The dataframe that has the newly added tickers IN THE SAME order as msgl running file is : " + new_in_msgl_datefile_df.to_string())
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# todo
# Check if the symbol in newly added already exists in the running and if it was
# added / worked upon more than a month ago, then maybe create another df that
# has all the recent information from msgl date_str file, but preserves the other
# columns (like notes, CNBC, profitspi etc from msgl running file...and put it
# in a separate csv...that way, sundeep have a choice to take that csv and replace
# those rows in the msgl running file with the update information from MarketSmith
# (needs more thinking...)
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Compare the tickers from the dataframe with the tickers in the masterTracklist
# If a ticker is found in MasterTracklist, then put a "Yes" in the "Wheat" column
# otherwise, put a "No"
# -----------------------------------------------------------------------------
# Insert the date from the tk input into the appropriate col in the dataframe
# This will help keep track on when a particular ticker was added to the msgl
# running file
date_dt = dt.datetime.strptime(msgl_date_str_raw, '%Y_%m_%d').date()
msgl_date_str_mm_dd_yyyy = dt.datetime.strftime(date_dt, '%m/%d/%Y')
new_in_msgl_datefile_df['Date Added'] = msgl_date_str_mm_dd_yyyy

new_in_msgl_datefile_list = new_in_msgl_datefile_df['Symbol'].tolist()
new_in_msgl_datefile_df.set_index('Symbol', inplace=True)
logging.info("Looping through newly found tickers from msgl date_str file to check if they are found in Master Tracklist")
i_int = 0
for ticker_raw in new_in_msgl_datefile_list:
  ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase
  if ticker not in master_ticker_list:
    logging.debug ("Did not find " + str(ticker) + " in Master Tracklist List")
    new_in_msgl_datefile_df.loc[ticker,'Wheat'] = "No"
    i_int = i_int+1
  else:
    logging.debug ("Found " + str(ticker) + " in Master Tracklist List")
    new_in_msgl_datefile_df.loc[ticker,'Wheat'] = "Yes"
logging.info("Out of " + str(len(new_in_msgl_datefile_list)) + " tickers (newly found), " + str(i_int) + " tickers were not in Master Tracklist")
new_in_msgl_datefile_df.reset_index(inplace=True, drop=False)
new_in_msgl_datefile_df = new_in_msgl_datefile_df[cols_msgl_running_tracking_df]
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Now make two datafames by filtering out the new_in_msgl_datefile_df -
# One that has the symbols to track that are NOT in the exclude list
#   These are the tickers that can be copied and pasted into the msgl running file
#   from the csv that gets created in the logs directory
# The other that has the symbols that are ONLY in the exclude list
#   At this time, these are for information only, telling the user that I found
#   these tickers that were new in the msgl date_str file, but will not put them
#   in the first dateframe, because they were also found in the exclude list.
# -----------------------------------------------------------------------------
logging.info("")
logging.info("Now splitting the dataframe for tickers to be potentially added into two dataframes")
logging.info("One dataframe would ONLY have tickers that need to be added (and are not in exclude list)")
logging.info("Second dataframe would ONLY have tickers that are in the exclude list")
new_in_msgl_datefile_df.set_index('Symbol', inplace=True)
new_in_msgl_datefile_and_track_list = [x for x in new_in_msgl_datefile_list if x not in new_in_msgl_but_in_exclude_list]

new_in_msgl_datefile_and_track_df = new_in_msgl_datefile_df.loc[new_in_msgl_datefile_and_track_list, :]
new_in_msgl_datefile_and_exclude_df = new_in_msgl_datefile_df.loc[new_in_msgl_but_in_exclude_list, :]

new_in_msgl_datefile_and_track_df.reset_index(inplace=True, drop=False)
new_in_msgl_datefile_and_exclude_df.reset_index(inplace=True, drop=False)

new_in_msgl_datefile_and_track_df = new_in_msgl_datefile_and_track_df[cols_msgl_running_tracking_df]
new_in_msgl_datefile_and_exclude_df = new_in_msgl_datefile_and_exclude_df[cols_msgl_running_tracking_df]

logging.debug("The dataframe that ONLY has tickers to be added : " + new_in_msgl_datefile_and_track_df.to_string())
logging.debug("The dataframe that ONLY has tickers that are excluded : " + new_in_msgl_datefile_and_exclude_df.to_string())

logging.info("")
logging.info("Printing all the info in log directory")
new_in_msgl_datefile_and_track_df_csv = msgl_date_str_raw + "_MarketSmith_Growth_250_Newly_Added" + ".csv"
new_in_msgl_datefile_and_exclude_df_csv = msgl_date_str_raw + "_MarketSmith_Growth_250_Exclude" + ".csv"

new_in_msgl_datefile_and_track_df.sort_values(by=['Symbol'], ascending=[True]).to_csv(dir_path + log_dir + "\\" + new_in_msgl_datefile_and_track_df_csv,sep=',', index=False, header=True)
new_in_msgl_datefile_and_exclude_df.sort_values(by=['Symbol'], ascending=[True]).to_csv(dir_path + log_dir + "\\" + new_in_msgl_datefile_and_exclude_df_csv,sep=',', index=False, header=True)

logging.info("Created : " + str(new_in_msgl_datefile_and_track_df_csv))
logging.info("Created : " + str(new_in_msgl_datefile_and_exclude_df_csv))

logging.info("All Done")
# -----------------------------------------------------------------------------

# Good example on how to insert a col. in dataframe
# msgl_dated_df.insert(1,'In_Master_Tracklist',"#ERROR#")
# msgl_dated_df.insert(2,'Date_Added',date_dt)
#
# Good example on how to iterate though a dataframe
# for i_idx, row in msgl_dated_df.iterrows():
#   if (i_idx in only_in_msgl_datedfile_list):
#     logging.debug("Since " + str(i_idx) + " is only in the MSmith Additions file, will add \"NO\" to the column In_Master_Tracklist")
#     msgl_dated_df.loc[i_idx,"In_Master_Tracklist"] = "No"
#   else:
#     logging.debug("Since " + str(i_idx) + " was also found Master Tracklist file, will add \"YES\" to the column In_Master_Tracklist")
#     msgl_dated_df.loc[i_idx,"In_Master_Tracklist"] = "Yes"
