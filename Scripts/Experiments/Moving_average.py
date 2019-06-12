import pandas as pd
import datetime as dt
import numpy as np
import os
import time

# Read the input file
exp_df = pd.read_csv('C:\Sundeep\Stocks_Automation\Scripts\Experiments\Moving_average_in.csv')
# Drop any row that has nan values
exp_df.dropna(inplace=True)
print("\n\nInput Dataframe \n\n", exp_df, "\n\n")
print ("============================================")
print("Will create\n1. 10 day Price Moving Average.\n2. 20 Day price moving average Reversed order.\n3. 5 Day Volume Moving average Reversed Order")
print ("Sleeping for 5 sec")
print ("============================================")
time.sleep(5)

# Add empty columns to put between the original data and the moving averages
exp_df["Empty_Column_1"] = ""
exp_df["Empty_Column_2"] = np.nan
# Add the moving averages - They are added as columns
exp_df['10_day_Price_MA'] = exp_df.rolling(window=20)['Adj_Close'].mean()
exp_df['20_day_Price_MA_Reversed'] = exp_df.rolling(window=10)['Adj_Close'].mean().shift(-9)
exp_df['10_day_Volume_MA_Reversed'] = exp_df.rolling(window=5)['Volume'].mean().shift(-4)

print("\n\nOutput Dataframe \n\n", exp_df, "\n\n")

# Write the dataframe to out file
exp_df.to_csv('C:\Sundeep\Stocks_Automation\Scripts\Experiments\Moving_average_out.csv')