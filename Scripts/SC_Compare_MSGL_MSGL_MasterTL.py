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
# This program read three files:
# 1. MSmith GL 250 from a directory specified by the usr (through a date)
# 2. MSmith GL 250 running file - from MSmith Parent directory 
# 3. MasterTracklist file from the user_dir 
# After reading all the three files, it
# 1. Compares the MSmith GL file specified by the date (through the tk user input) 
#     with MasterTracklist file and finds out which MSmith GL tickers are in the 
#     MasterTrackList which are not (this tells if we already have a chart for it or not)
# 2. Compares the 
# Now read all the three files
# -----------------------------------------------------------------------------
master_tracklist_file = "Master_Tracklist.xlsx"
msgl_dated_file = str(name_var.get()) + "_MarketSmith_Growth_250"
logging.info ("Reading Master Tracklist and MSGL date_str file : " + master_tracklist_file  + ", and : " + msgl_dated_file)
master_tracklist_df = pd.read_excel(dir_path + user_dir + "\\" + master_tracklist_file, sheet_name="Main")
msgl_dated_df = pd.read_csv(dir_path + msmith_dir + "\\" + str(name_var.get()) + "\\" + msgl_dated_file + ".csv")
msgl_running_tracking_df = pd.read_excel(dir_path + msmith_dir + "\\" + "MarketSmith_Growth_250_Running.xlsm", sheet_name="Tracking")

# Sundeep : todo print the full path of the MSGL date_str file
logging.debug("Master Tracklist \n\n" + master_tracklist_df.to_string())
logging.debug("\n\nMSGL date_str file : \n\n" + msgl_dated_df.to_string())
logging.debug("\n\nMSGL Running file : \n\n" + msgl_running_tracking_df.to_string())
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Now iterate through MSmith Additions df to see which tickers are in MasterTracklist
# -----------------------------------------------------------------------------
master_ticker_list = master_tracklist_df['Tickers'].tolist()
msgl_datedfile_ticker_list = msgl_dated_df['Symbol'].tolist()
msgl_running_ticker_list = msgl_running_tracking_df['Symbol'].tolist()
logging.debug("Total Number of Tickers extracted from Master Tracklist " + str(len(master_ticker_list)))
logging.debug("Total Number of Tickers extracted from MSmith date str file " + str(len(msgl_datedfile_ticker_list)))
logging.debug("Total Number of Tickers extracted from MSmith Running file " + str(len(msgl_running_ticker_list)))
logging.debug("The List of tickers extracted from Master Tacklist " + str(master_ticker_list))
logging.debug("The List of tickers extracted from MSmith date str file " + str(msgl_datedfile_ticker_list))
logging.debug("The List of tickers extracted from MSmith Running file " + str(msgl_running_ticker_list))


new_in_msgl_datedfile_list = []
for ticker_raw in msgl_datedfile_ticker_list:
  ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase
  # logging.debug("Looking for " + str(ticker) + " from Ann Trackist in Master Tracklist")
  if ticker not in msgl_running_ticker_list:
    logging.debug ("Did not find " + str(ticker) + " in MSGL Running file")
    new_in_msgl_datedfile_list.append(ticker)
  else:
    logging.debug ("Found " + str(ticker) + " in MSGL Running file")
    # in_master_ticker_list.append(ticker)
logging.info("Found : " + str(len(new_in_msgl_datedfile_list)) + " tickers only in MSGL Dated file file")
logging.debug("Found : " + str(new_in_msgl_datedfile_list) + " tickers only in MSGL Dated  file")
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# todo :
# Here if the MSGL Running file has a "Do not track" tab, then read it and delete the tickers
# from new_in_msgl_datedfile_list that are in the "Do not Track" tab
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Now prepare the dataframe that has only the new tickers from the msgl_datedfile
# -----------------------------------------------------------------------------
msgl_dated_df.set_index('Symbol', inplace=True)
new_in_msgl_datefile_df = msgl_dated_df.loc[new_in_msgl_datedfile_list, :]
# new_in_msgl_datefile_df.drop('Order', axis=1, inplace=True)
new_in_msgl_datefile_df.reset_index(inplace=True, drop=False)
logging.debug("The rows that are new in the dated file :" + new_in_msgl_datefile_df.to_string())

# -----------------------------------------------------------------------------





# Now get the columns of the two dataframes to line up
# new_in_msgl_datefile_df_again = pd.concat([msgl_running_tracking_df,new_in_msgl_datefile_df], axis=0)
cols_msgl_running_tracking_df = msgl_running_tracking_df.columns.tolist()
cols_new_in_msgl_datefile_df = new_in_msgl_datefile_df.columns.tolist()
logging.debug("The columns in msgl running file are : " + str(cols_msgl_running_tracking_df))
logging.debug("The columns in msgl date str file are : " + str(cols_new_in_msgl_datefile_df))

for col_name in cols_new_in_msgl_datefile_df:
  if col_name not in cols_msgl_running_tracking_df:
    logging.note("The col name " + str(col_name) + " is in msgl date str file but NOT in msgl running file...Please check and rerun again")

for col_name in cols_msgl_running_tracking_df:
  if col_name not in  cols_new_in_msgl_datefile_df:
    logging.debug("The column " + str(col_name) + " not found in msgl running file, adding it to msgl date str df")
    new_in_msgl_datefile_df.insert(1,col_name,"#NA#")

logging.debug("The dataframe that has the newly added tickers and same cols as msgl running file is : " + new_in_msgl_datefile_df.to_string())
new_in_msgl_datefile_df = new_in_msgl_datefile_df[cols_msgl_running_tracking_df]
logging.debug("The dataframe that has the newly added tickers IN THE SAME order as msgl running file is : " + new_in_msgl_datefile_df.to_string())


# todo
# compare the symbols to master tracklist and put a yes or no
# add the date added to the date_str
# remove the added from the "Do Not track" sheet
# Check if the symbol in newly added already exists in the running and if it more than a month old,
# and more it to a differnt dataframe
# Now print both the dataframes in the log directory
sys.exit(1)



only_in_msgl_datedfile_list = []
in_master_ticker_list = []
logging.info("")
logging.info("Looping through MSmith Dated file Tickers to see if they are found in Master Tracklist")
for ticker_raw in msgl_datedfile_ticker_list:
  ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase
  # logging.debug("Looking for " + str(ticker) + " from Ann Trackist in Master Tracklist")
  if ticker not in master_ticker_list:
    logging.debug ("Did not find " + str(ticker) + " in Master Tracklist List")
    only_in_msgl_datedfile_list.append(ticker)
  else:
    logging.debug ("Found " + str(ticker) + " in Master Tracklist List")
    in_master_ticker_list.append(ticker)
logging.info("Found : " + str(len(only_in_msgl_datedfile_list)) + " tickers only in MSmith Additions file")
logging.debug("Found : " + str(only_in_msgl_datedfile_list) + " tickers MSmith Additions file")
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Now insert, in the MSmith Additions file, whether the ticker was found in the
# master tracklist or not. Also insert a date column and populate it with the
# date of the MSmith additions file (the date the user inputted at the beginning)
# -----------------------------------------------------------------------------
msgl_dated_df.set_index('Symbol', inplace=True)
msgl_dated_df.drop('Order', axis=1, inplace=True)
# This inserts a column in the dataframe after column number 1
# msgl_dated_df.assign(In_Master_Tracklist="")
msgl_dated_df.insert(1,'In_Master_Tracklist',"#ERROR#")
date_dt = dt.datetime.strptime(str(name_var.get()), '%Y_%m_%d').date()
date_str = dt.datetime.strftime(date_dt, '%m/%d/%Y')
msgl_dated_df.insert(2,'Date_Added',date_dt)

for i_idx, row in msgl_dated_df.iterrows():
  if (i_idx in only_in_msgl_datedfile_list):
    logging.debug("Since " + str(i_idx) + " is only in the MSmith Additions file, will add \"NO\" to the column In_Master_Tracklist")
    msgl_dated_df.loc[i_idx,"In_Master_Tracklist"] = "No"
  else:
    logging.debug("Since " + str(i_idx) + " was also found Master Tracklist file, will add \"YES\" to the column In_Master_Tracklist")
    msgl_dated_df.loc[i_idx,"In_Master_Tracklist"] = "Yes"

msgl_dated_df.sort_values(by=['In_Master_Tracklist','Symbol'], ascending=[True,True], inplace=True)
logging.debug("MSmith Additions df with deleted rows that were found in Master Tracklist " + msgl_dated_df.to_string())
# -----------------------------------------------------------------------------


logging.info("\n")
logging.info("Printing all the info in log directory")
msmith_additions_sorted_csv = msgl_dated_file + "_Sorted" + ".csv"
msgl_dated_df.sort_values(by=['In_Master_Tracklist','Symbol'], ascending=[True,True]).to_csv(dir_path + log_dir + "\\" + msmith_additions_sorted_csv,sep=',', index=True, header=True)
# =============================================================================

logging.info("All Done")
