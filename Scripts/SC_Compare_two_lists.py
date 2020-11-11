
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


#
# Define the directories and the paths
dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
log_dir = "\\..\\" + "Logs"
# ---------------------------------------------------------------------------
# Set Logging
# critical, error, warning, info, debug
# set up logging to file - see previous section for more details
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename=dir_path + log_dir + "\\" + 'SC_compare_two_lists_debug.txt',
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
input_file = "file_that_has_two_lists.xlsx"

logging.info ("Reading the input file")
start = time.process_time()
input_file_df = pd.read_excel(dir_path + user_dir + "\\" + input_file, sheet_name="Main")

list_01 = input_file_df['List_01'].tolist()
list_02 = input_file_df['List_02'].tolist()
only_in_list_01 = []
only_in_list_02 = []
common_in_list_01_02 = []

for element in list_01:
  logging.debug("List_01: Looking for " + str(element) + " in List_02")
  if element in list_02:
    logging.debug("List_01: Found " + str(element) + " in List_02")
    common_in_list_01_02.append(element)
  else:
    logging.debug("List_01: NOT Found " + str(element) + " in List_02")
    only_in_list_01.append(element)

for element in list_02:
  logging.debug("List_02: Looking for " + str(element) + " in List_02")
  if element in list_01:
    logging.debug("List_02: Found " + str(element) + " in List_02")
    common_in_list_01_02.append(element)
  else:
    logging.debug("List_02: NOT Found " + str(element) + " in List_02")
    only_in_list_02.append(element)

# Now remove duplicates from the common list
tmp_list = []
[tmp_list.append(x) for x in common_in_list_01_02 if x not in tmp_list]
common_in_list_01_02 = tmp_list.copy()

# print those dateframes in a file
logging.info("\n")
logging.info("Printing all the info in log directory")
only_in_list_01_logfile = "Elements_Only_In_List_01.txt"
only_in_list_02_logfile = "Elements_Only_In_List_02.txt"
common_in_list_01_list_02_logfile = "Elements_Common_In_List_01_List_02.txt"

pd.DataFrame(only_in_list_01).to_csv(dir_path + log_dir + "\\" + only_in_list_01_logfile,sep=' ', index=False, header=False)
pd.DataFrame(only_in_list_02).to_csv(dir_path + log_dir + "\\" + only_in_list_02_logfile,sep=' ', index=False, header=False)
pd.DataFrame(common_in_list_01_02).to_csv(dir_path + log_dir + "\\" + common_in_list_01_list_02_logfile,sep=' ', index=False, header=False)
# =============================================================================

logging.info("All Done")
