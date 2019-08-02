
import openpyxl
import os
import xlrd
import pandas as pd
import csv

# This script generates a csv - based on tracklist file - that has 4 columns
# Column 1 has the ticker name
# Column 2 - has the string that pull the company name     from yahoo based on smf fumction and the ticker from that row
# Column 3 - has the string that pull the company sector   from yahoo based on smf fumction and the ticker from that row
# Column 4 - has the string that pull the company industry from yahoo based on smf fumction and the ticker from that row
# The user can put all the ticker in the tracklist file - I put all the tickers from AAII in the tracklist file
# and then generated the csv files.


# For some reason - likely for my sharpening of the skills - that script generates the same information
# in two csv files using two different ways - one from csv write method and one dataframe to csv write method
# Both work. The csv write generated experiment_01.csv and the dataframe to csv generated experiment_00.csv

# I just saved the csv file as xlsm and put the vba macro - named iterate_over_rows - inside that xlsm
# and ran the macro - (the macro is saved as vba_iterate_over_rows.txt in the User_files dir and also inside
# Yahoo_Company_Info.xlsm in the User_files direcotry.
# The vba macro the populates the xlsm file columns with the compnay name, sector and industry and saves the
# columns values as text (instead of formula). It has been optimized


dir_path = os.getcwd()
user_dir = "\\..\\..\\" + "User_Files"
tracklist_file = "Tracklist.csv"
tracklist_file_full_path = dir_path + user_dir + "\\" + tracklist_file

tracklist_df = pd.read_csv(tracklist_file_full_path)
# print ("The Tracklist df is", tracklist_df)
ticker_list_unclean = tracklist_df['Tickers'].tolist()
ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']

# Prepare the dataframe to be populated in the loop row by row
company_info_df =  pd.DataFrame(columns = ['Ticker', 'Company_Name', 'Sector', 'Industry'])

# Generate experiment_01 the csv write way
csvFile = open('experiment_01.csv', 'w+', newline='')
writer = csv.writer(csvFile)
writer.writerow(['Ticker', 'Company_Name', 'Sector', 'Industry'])

# =============================================================================
# Loop ticker by ticker
# =============================================================================
i = 0
for ticker_raw in ticker_list:
 print ("Processing for ", ticker_raw)
 row_list = []
 tmp_str = '$A$'+str(i+2)

 # Print the row in the dataframe
 company_info_df.loc[i] = [ticker_raw,'=RCHGetElementNumber('+tmp_str+', 13863)' , '=RCHGetElementNumber('+tmp_str+', 13865)','=RCHGetElementNumber('+tmp_str+', 13867)']

 # Print the row in the csv with insert
 row_list.insert(0, ticker_raw)
 row_list.insert(1, '=RCHGetElementNumber('+tmp_str+', 13863)')
 row_list.insert(2, '=RCHGetElementNumber('+tmp_str+', 13865)')
 row_list.insert(3, '=RCHGetElementNumber('+tmp_str+', 13867)')
 writer.writerow(row_list)


 i = i+1
# =============================================================================

# =============================================================================
# After the loop write the dataframe to csv and  close the csv
# =============================================================================
company_info_df.set_index('Ticker', inplace=True)
print (company_info_df)
company_info_df.to_csv("experiment_00.csv")

csvFile.close()
# =============================================================================


