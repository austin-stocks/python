# ##############################################################################
# Download the historical data into individual csv
# ##############################################################################

import csv
import datetime as dt
import os
import logging
import sys
import pandas as pd
# ##############################################################################


dir_path = os.getcwd()
user_dir = "\\..\\" + "User_Files"
log_dir = "\\..\\" + "Logs"

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
                    filename=dir_path + log_dir + "\\" + 'SC_Extract_GeneralCompany_Info_debug.txt',
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

# -----------------------------------------------------------------------------
# Read the tracklist file into a dataframe
# -----------------------------------------------------------------------------
tracklist_file = "Tracklist.csv"
tracklist_file_full_path = dir_path + user_dir + "\\" + tracklist_file
tracklist_df = pd.read_csv(tracklist_file_full_path)
ticker_list_unclean = tracklist_df['Tickers'].tolist()
ticker_list = [x.upper() for x in ticker_list_unclean if str(x) != 'nan']
# -----------------------------------------------------------------------------

# Read the aaii company information
aaii_company_info_df = pd.read_excel(dir_path + user_dir + "\\" + 'AAII_GeneralCompany_Info.xlsx', sheet_name="General_Info")
logging.info("Read the AAII General Company Info file")
aaii_ticker_list = aaii_company_info_df['Ticker'].tolist()

logging.info("Extracting information for " + str(len(ticker_list)) + " tickers from AAII General Company Info file")
# -----------------------------------------------------------------------------
# Compare the ticker list from tracklist with the ticker list from AAII file and
# if there are tickers that are NOT FOUND in the aaii file, then flag an error
# for the user, with some suggestions, to correct the problem before rerunning
# -----------------------------------------------------------------------------
# Sundeep : This is good : Neat way to compare two lists
tickers_missing_list = list(set(ticker_list) - set(aaii_ticker_list))
if len(tickers_missing_list) > 0:
  logging.info("")
  logging.info("The following tickers were NOT found in the AAII Company Info file : " + str(tickers_missing_list))
  logging.info("1. You may want to check the tickers in the tracklist file to make sure")
  logging.info("   that the above tickers are spelled correctly.")
  logging.info("2. Sometimes the tickers maybe spelled correctly, but then AAII will have")
  logging.info("   Class A shares in their database(with a different symbol - like NWS is listed as NWSA)")
  logging.info("   while you are trying to get non-A shares etc")
  logging.info("3. Sometimes the tickers in the tracklist are spelled correctly")
  logging.info("   and there is no class A or class B ticker name discrepancy")
  logging.info("   In that case, AAII does not have information for them (why do they not have it, don't ask :-( )")
  logging.info("")
  logging.info("Whatever the case maybe (out of the above 3) - IT NEEDS TO BE CORRECTED BEFORE PROCEEDING")
  logging.info("Many a times it is #2 above - the tickers exist but it is Class A/B name discrepancy")
  logging.info("In that case, you should change the Tickers (if possible, do it in the file where the")
  logging.info("orignial tickerlist came from) and run the program again")
  logging.info("In general, that is a good solution as CNBC also would have projections for AAII tickers")
  logging.info("If, after checking the tickers for their spellings and their Class A/B discrepancy,")
  logging.info("and you did not find any errors/discrepancy there, then the case is the AAII is not")
  logging.info("tracking them, you should delete the tickers (again, if possible, in the file from which")
  logging.info("the original tickerlist came from and run again)")
  logging.info("**********     IMPORTANT     **********")
  logging.info("After correcting the above problem(s), you need to make sure that if you are")
  logging.info("planning to copy and paste the info generated by this script in some csv file that had")
  logging.info("the original ticker list, then the ouput file generated now is not going to match the original")
  logging.info("ticker order (deleted/modified (for Class Discrepancy) tickers are going to create holes/confusion)")
  logging.info("So BE AWARE OF IT BEFORE COPYING AND PASTING THE OUTPUT OF THIS SCRIPT INTO SOME FILE")
  logging.info("1. Probably best, if possible, to modify the original tickerlist based on #1, #2 or #3 above")
  logging.info("   and then re-copy the tickerlist into tracklist.csv file")
  logging.info("2. If that is not possible, then best to put the missing tickers (from the list above) at the end of")
  logging.info("   the tickerlist in the original file and then recopy the tickerlist in tracklist.csv file")
  logging.info("   and run again")
  logging.info("")
  logging.info("Please correct the above problem(s) and rerun")
  logging.info("Exiting without running the script to completion...")
  sys.exit(1)
# -----------------------------------------------------------------------------

aaii_company_info_df.set_index('Ticker', inplace=True)
# Sundeep : This is good - it extracts the rows - that are in the ticker_list
# from the aaii_company_info_df and puts them in a separate dataframe
extracted_company_info_df = aaii_company_info_df.loc[ticker_list, :]

logging.debug("The dataframe for tickers is " + extracted_company_info_df.to_string())
company_info_logfile = "SC_AAII_company_info.csv"
extracted_company_info_df.to_csv(dir_path + log_dir + "\\" + company_info_logfile,sep=',', index=True, header=True)
logging.info("Printed the company info for tickers from tracklist in the file (in log directory) : " + str(company_info_logfile))
logging.info("All Done")
logging.info("")
logging.info("A word of caution before you proceed :")
logging.info("1. Please make sure that when you open the " + str(company_info_logfile) + " the number of")
logging.info("   tickers, for which the information has been extracted, matches the number of tikers in the original list")
logging.info("2. Once you make sure that number of tickers match, do a spot check for a few tickers")
logging.info("   (say 1st ticker, then 50th ticker, then 200th ticker and maybe last ticker) to make sure")
logging.info("   that the information extracted matches (corresponds) to the ticker")
logging.info("   I do this by matching the compnay name and/or reading the business for the ticker")
logging.info("   and see if that matches...")
logging.info("   Once you have done this spot checking and are satisfied, then the information is ready to be copied and pasted")
# ##############################################################################



