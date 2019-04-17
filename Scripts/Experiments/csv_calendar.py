import pandas as pd
import matplotlib
import datetime as dt
import numpy as np
import matplotlib.pyplot as plt
import os

# =============================================================================
# Code to concatenate two csv files
# =============================================================================
# Remove the file. Supress the error if the file does not exist
try:
  os.remove('concatenate.csv')
except OSError:
  pass

fout = open("concatenate.csv", "a")

# Write the fist file
for line in open('Calendar.csv'):
  # print ("The Line is ", line)
  fout.write(line)
# Write the second file
for line in open('AAPL_historical_new.csv'):
  # print("The Line is ", line)
  fout.write(line)
# =============================================================================

# =============================================================================
# Now create two dataframes (they could have been created from reading the files
# =============================================================================
data1 = {'state': ['ny', 'tx'],
         'year': ['2001', '2002']}

data2 = {'date': ['0', '1', '2'],
         'price': ['10', '11', '12'],
         'ticker': ['ibm', 'aapl', 'uve']}

df1 = pd.DataFrame(data1)
df2 = pd.DataFrame(data2)
print("Dataframe 1\n", df1)
print("Dataframe 2\n", df2)

num_cols = len(df2.columns)
num_rows = len(df2.index)
print("Number of rows in df2 are ", num_rows, " and number of cols are", num_cols)
i = 0
while (i < num_rows):
  j = 0
  while (j < num_cols):
    print("Value at row ", i, " and col ", j, " is ", df2.iat[i, j])
    j = j + 1
  i = i + 1

# This coverts the row in dataframe to a comma separated list and that list
# can then be written to csv
x = df1.to_string(header=False, index=False, index_names=False).split('\n')
row_list = [','.join(ele.split()) for ele in x]
for x in row_list:
  fout.write(x + '\n')

x = df2.to_string(header=False, index=False, index_names=False).split('\n')
row_list = [','.join(ele.split()) for ele in x]
for x in row_list:
  fout.write(x + '\n')

# =============================================================================

# =============================================================================
# Experiments with the Dataframes
# =============================================================================
# df_append = df1.append(df2, ignore_index=True, sort=False)
# print ("Appended dataframe \n", df_append)
# df_append.to_csv('tmp.csv', index=False)
#
# df_concat = pd.concat([df1,df2],ignore_index=True,sort=False)
# print ("Concatenated Dataframe\n", df_concat)
# df_concat.to_csv('tmp.csv', index=False)
#
# df_join = df1.join(df2)
# print ("Joined Dataframe\n", df_join)
# =============================================================================

# this all works - Sundeep
# To do
#  Read the real calendar and Historical file and experiment
calendar_df = pd.read_csv('Calendar.csv', header=None)
print("The Calendar is", calendar_df)
# Get the Column 0 from the dataframe and convert to datetime
calendar_date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in calendar_df.iloc[:, 0]]
print("The Calendar Date list is", calendar_date_list)

historical_df = pd.read_csv('AAPL_historical_new.csv')
print("Historical Dataframe ", historical_df)
historical_date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in historical_df.iloc[:, 0]]
historical_col_str = ', '.join(historical_df.columns.tolist())
print("The Historical Columns are", historical_col_str)

# Match the first date in historical to the dates in calendar
match_date = min(calendar_date_list, key=lambda d: abs(d - historical_date_list[0]))
print("The matching date is ", match_date, " at index ", calendar_date_list.index(match_date))

# Delete everything after - and including - the match index
calendar_date_list_mod = calendar_date_list[:calendar_date_list.index(match_date)]
print("The modified Calendar list is ", calendar_date_list_mod)

# =============================================================================
# Now write the Data in csv

# First write the Columns
fout.write(str(historical_col_str + '\n'))

# Then write the modified list of Calendar
for x in calendar_date_list_mod:
  fout.write(str(x) + '\n')

# Then write the historical Data
x = historical_df.to_string(header=False, index=False, index_names=False).split('\n')
row_list = [','.join(ele.split()) for ele in x]
for x in row_list:
  fout.write(x + '\n')

fout.close()
# =============================================================================
