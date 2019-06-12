import pandas as pd
import datetime as dt
import numpy as np
import os
import time

# Read the input file
exp_df = pd.read_csv('C:\Sundeep\Stocks_Automation\Scripts\Experiments\Moving_average_in.csv')
# Drop any row that has nan values
exp_df.dropna(inplace=True)
print("\n\nReading Input Dataframe \n\n", exp_df, "\n\n")
print ("============================================")
print("Will create Additional Columns (add to the existing Columns from Input file)in the Output file\n\
        1. Empty_Column_1\n\
        2. Empty_Column_2\n\
        3. 10 day Price Moving Average.\n\
        4. 20 Day price moving average Reversed order.\n\
        5. 5 Day Volume Moving average Reversed Order")
print ("Sleeping for 5 sec to give user to read all the above :-)")
print ("============================================")
time.sleep(5)

# Add empty columns to put between the original data and the moving averages
exp_df["Empty_Column_1"] = ""
exp_df["Empty_Column_2"] = np.nan
# Add the moving averages - They are added as columns after Empty Columns
exp_df['10_day_Price_MA'] = exp_df.rolling(window=20)['Adj_Close'].mean()
exp_df['20_day_Price_MA_Reversed'] = exp_df.rolling(window=10)['Adj_Close'].mean().shift(-9)
exp_df['10_day_Volume_MA_Reversed'] = exp_df.rolling(window=5)['Volume'].mean().shift(-4)

print("\n\nWriting Output Dataframe \n\n", exp_df, "\n\n")

# Write the dataframe to out file
exp_df.to_csv('C:\Sundeep\Stocks_Automation\Scripts\Experiments\Moving_average_out.csv')