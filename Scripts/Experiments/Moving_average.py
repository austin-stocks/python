import pandas as pd
import datetime as dt
import numpy as np
import os

# Read the input Yahoo Historical csv
historical_df = pd.read_csv('C:\Sundeep\Stocks_Automation\Historical\AAPL_Historical.csv')
# Drop any row that has nan values
historical_df.dropna(inplace=True)



historical_df['10_day_MA'] = historical_df.rolling(window=10)['Adj_Close'].mean().shift(-9)
historical_df['20_day_MA'] = historical_df.rolling(window=20)['Adj_Close'].mean().shift(-19)
print("Historical Dataframe ", historical_df)