
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
                    filename=dir_path + log_dir + "\\" + 'SC_compare_MasterTracklist_MSmithAdditions_debug.txt',
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
# Set the various dirs and read both the Tracklists
# -----------------------------------------------------------------------------

# ---------------------------------------------------------
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
name_label = tk.Label(root, text='Date(Dir) of MarketSmit Additions file', font=('calibre', 10, 'bold'))

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
# ---------------------------------------------------------


master_tracklist_file = "Master_Tracklist.xlsx"
msmith_addtions_file = str(name_var.get()) + "_Additions"
logging.info ("Reading Master Tracklist and MSmith Additions file : " + master_tracklist_file  + ", and : " + msmith_addtions_file )
master_tracklist_df = pd.read_excel(dir_path + user_dir + "\\" + master_tracklist_file, sheet_name="Main")
msmith_additions_df = pd.read_csv(dir_path + msmith_dir + "\\" + str(name_var.get()) + "\\" + msmith_addtions_file + ".csv")

logging.debug("Master Tracklist \n\n" + master_tracklist_df.to_string())
logging.debug("MSimth Addtions file : \n\n" + msmith_additions_df.to_string())
# -----------------------------------------------------------------------------


# =============================================================================
# Now iterate through MSmith Additions df to see which tickers are in MasterTracklist
# =============================================================================
master_ticker_list = master_tracklist_df['Tickers'].tolist()
msmith_additions_ticker_list = msmith_additions_df['Symbol'].tolist()
logging.debug("Total Number of Tickers extracted from Master Tracklist " + str(len(master_ticker_list)))
logging.debug("Total Number of Tickers extracted from MSmith Additions file " + str(len(msmith_additions_ticker_list)))
logging.debug("The List of tickers extracted from Master Tacklist " + str(master_ticker_list))
logging.debug("The List of tickers extracted from MSmith Additions file " + str(msmith_additions_ticker_list))

only_in_msmith_additions_list = []
in_master_ticker_list = []
logging.info("")
logging.info("Looping through MSmith Additions Tickers to see if they are found in Master Tracklist")
for ticker_raw in msmith_additions_ticker_list:
  ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase
  # logging.debug("Looking for " + str(ticker) + " from Ann Trackist in Master Tracklist")
  if ticker not in master_ticker_list:
    logging.debug ("Did not find " + str(ticker) + " in Master Tracklist List")
    only_in_msmith_additions_list.append(ticker)
  else:
    logging.debug ("Found " + str(ticker) + " in Master Tracklist List")
    in_master_ticker_list.append(ticker)
logging.info("Found : " + str(len(only_in_msmith_additions_list)) + " tickers only in MSmith Additions file")
logging.debug("Found : " + str(only_in_msmith_additions_list) + " tickers MSmith Additions file")
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Now insert, in the MSmith Additions file, whether the ticker was found in the
# master tracklist or not. Also insert a date column and populate it with the
# date of the MSmith additions file (the date the user inputted at the beginning)
# -----------------------------------------------------------------------------
msmith_additions_df.set_index('Symbol', inplace=True)
msmith_additions_df.drop('Order', axis=1, inplace=True)
# This inserts a column in the dataframe after column number 1
# msmith_additions_df.assign(In_Master_Tracklist="")
msmith_additions_df.insert(1,'In_Master_Tracklist',"#ERROR#")
date_dt = dt.datetime.strptime(str(name_var.get()), '%Y_%m_%d').date()
date_str = dt.datetime.strftime(date_dt, '%m/%d/%Y')
msmith_additions_df.insert(2,'Date_Added',date_dt)

for i_idx, row in msmith_additions_df.iterrows():
  if (i_idx in only_in_msmith_additions_list):
    logging.debug("Since " + str(i_idx) + " is only in the MSmith Additions file, will add \"NO\" to the column In_Master_Tracklist")
    msmith_additions_df.loc[i_idx,"In_Master_Tracklist"] = "No"
  else:
    logging.debug("Since " + str(i_idx) + " was also found Master Tracklist file, will add \"YES\" to the column In_Master_Tracklist")
    msmith_additions_df.loc[i_idx,"In_Master_Tracklist"] = "Yes"

msmith_additions_df.sort_values(by=['In_Master_Tracklist','Symbol'], ascending=[True,True], inplace=True)
logging.debug("MSmith Additions df with deleted rows that were found in Master Tracklist " + msmith_additions_df.to_string())
# -----------------------------------------------------------------------------


logging.info("\n")
logging.info("Printing all the info in log directory")
msmith_additions_sorted_csv = msmith_addtions_file + "_Sorted" + ".csv"
msmith_additions_df.sort_values(by=['In_Master_Tracklist','Symbol'], ascending=[True,True]).to_csv(dir_path + log_dir + "\\" + msmith_additions_sorted_csv,sep=',', index=True, header=True)
# =============================================================================

logging.info("All Done")
