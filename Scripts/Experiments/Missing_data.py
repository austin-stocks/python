import pandas as pd
import datetime as dt
import numpy as np
import os
import time

# =============================================================================
# This script reads an input file that has 2 columns and
# =============================================================================

# Read the input file
exp_df = pd.read_csv('C:\Sundeep\Stocks_Automation\Scripts\Experiments\Data\Missing_data_in.csv')

print("\n\nReading Input Dataframe \n\n", exp_df, "\n\n")

# =============================================================================
# Case 1:
# Drop the whole row if any columns has missing data
# =============================================================================
df_drop_row_if_any_missing = exp_df.dropna()
print ("Dropping whole row if any Column is missing data\n\n\
        Output Dataframe is \n\n",\
       df_drop_row_if_any_missing)
# =============================================================================

# =============================================================================
# Case 2:
# Drop the whole row if ALL columns missing data
# =============================================================================
df_drop_row_if_all_missing = exp_df.dropna(how='all')
print ("Dropping whole row if ALL Columns are missing data\n\n\
        Output Dataframe is \n\n",\
       df_drop_row_if_all_missing)
# =============================================================================

# =============================================================================
# Case 2:
# Drop the whole row only IF Date columns has missing data
# =============================================================================
df_drop_row_if_date_is_null = exp_df[pd.notnull(exp_df['Date'])]
print ("Dropping whole row if ONLY Date Column is missing data\n\n\
        Output Dataframe is \n\n",\
       df_drop_row_if_date_is_null)

# Then interpolate on all the missing data
df_drop_row_if_date_is_null_interpolated = df_drop_row_if_date_is_null.interpolate()
print ("Interpplating on ALL Columns after dropping rows that has missing data for DATE\n\n\
        Output Dataframe is \n\n",\
       df_drop_row_if_date_is_null_interpolated)

# =============================================================================

# Drop the whole row only if it has a missing data as that is important and then interpolate all the other columns

#
# # Write the dataframe to out file
# exp_df.to_csv('C:\Sundeep\Stocks_Automation\Scripts\Experiments\Data\Moving_average_out.csv')