import csv
import datetime
import openpyxl
import os
import xlrd
import datetime as dt
import time
import pandas as pd
from termcolor import colored, cprint
# ##############################################################################

# =============================================================================
# Define the various File names and Directory Paths to be used and set the
# start and end dates
# =============================================================================
dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
earnings_dir = "\\..\\" + "Earnings"
tracklist_file = "Tracklist.csv"
tracklist_file_full_path = dir_path + user_dir + "\\" + tracklist_file
# =============================================================================


# ##############################################################################
# Simple script to create a windows command line to open excel files
# I use this when I need to open earnings file to edit them to update earnings or
# update earnings projections...Doing it this way saves me time to open the earnings
# csv files by first going to the windows explorer and then going through the
# list of 400 odd files to open my 15 files
# This also has the advantage that there is no apparent limitation on the number
# of files that I can open (going through the windows explorer had the limitation
# of being able to open only 15 files at a time.
# This also has the advantage that the files open in the order that I have specified
# rather than some pseudo random order that excel/windows decide when I open them
# through windows explorer
# ##############################################################################

# Read the trracklist and convert the read tickers into a list
tracklist_df = pd.read_csv(tracklist_file_full_path)
# print ("The Tracklist df is", tracklist_df)
ticker_list_unclean = tracklist_df['Tickers'].tolist()
ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']
## ticker_list.sort()
## ticker_list.sort(reverse=False)
## print("The sorted tickers are : ", ticker_list)
# =============================================================================


# =============================================================================
# Go through each ticker and create a str.
# Then print that string in the powershell scripts file
# =============================================================================
script_file = open(dir_path + earnings_dir + "\\" + "open_excel.sh", "w")
# filelist_str = "start-process " + "\"" + "C:\Program Files\Microsoft Office\\root\Office16\Excel.EXE" +  "\" \" "
filelist_str = "start-process " + "\"" + "C:\Program Files (x86)\Microsoft Office\\root\Office16\Excel.EXE" + "\" \" "
filelist_str_01 = "start-process " + "\"" + "C:\Program Files\Microsoft Office\Office16\Excel.EXE" +  "\" \" "

for ticker_raw in ticker_list:
  ticker = ticker_raw.replace(" ", "").upper() # Remove all spaces from ticker_raw and convert to uppercase
  earnings_filename = ticker + "_earnings.csv"
  filelist_str = filelist_str + earnings_filename + " "
  filelist_str_01 = filelist_str_01 + earnings_filename + " "

filelist_str = filelist_str + "\""
filelist_str_01 = filelist_str_01 + "\""
print ("The command to open the excel files in "+ tracklist_file + " : \n", filelist_str)
print ("The command to open the excel files in "+ tracklist_file + " : \n", filelist_str_01)
script_file.write(filelist_str)
script_file.write(filelist_str_01)
script_file.close()

# text = colored('Hello, World!', 'red', attrs=['reverse', 'blink'])

print ("")
print ("You can either copy the line above, paste it at " + colored("Windows Powershell", 'red', attrs=['blink', 'bold']) + " prompt, press enter OR")
print ("Open the scripts file : " , script_file.name)
print ("And copy the line in it (it should be the same line as above), paste at " + colored("Windows Powershell", 'red', attrs=['bold']) + " prompt, press enter ")
