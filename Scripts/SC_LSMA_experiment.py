
import pandas as pd
import os
import sys

# ---------------------------------------------------------
def lsma(data, l1=25):
  pl = [];
  lr = [];
  for i in range(len(data)):
    pl.append(float(data[i]));
    if (len(pl) >= l1):
      sum_x = 0.0;
      sum_y = 0.0;
      sum_xy = 0.0;
      sum_xx = 0.0;
      sum_yy = 0.0;
      for a in range(1, len(pl) + 1):
        sum_x += a;
        sum_y += pl[a - 1];
        sum_xy += (pl[a - 1] * a);
        sum_xx += (a * a);
        sum_yy += (pl[a - 1] * pl[a - 1]);
      m = ((sum_xy - sum_x * sum_y / l1) / (sum_xx - sum_x * sum_x / l1));
      b = sum_y / l1 - m * sum_x / l1;
      lr.append(m * l1 + b);
      pl = pl[1:];
  return lr;
# ---------------------------------------------------------

#------------------------------------------------------------------------------
# Start of the main program
#------------------------------------------------------------------------------
ticker = "TQQQ"
dir_path = os.getcwd()
backtest_file = dir_path + "\\..\\Back_Testing" + "\\" + "TQQQ_yahoo_historical.csv"
historical_df = pd.read_csv(backtest_file)
historical_df.reset_index(inplace=True)
print (historical_df)

historical_df = historical_df[:3471]
print (historical_df)

ticker_close_list = historical_df['Close'].tolist()
print ("The Closing Price is ", ticker_close_list)

length = 10 # default = 25
lsma_val = lsma(ticker_close_list[::-1],length)
print ("The regression line is ", lsma_val[::-1])
historical_df.loc[:,'RL10'] = pd.Series(lsma_val[::-1])
print("DF now is ", historical_df)

data = [44.18,44.4,43.89,44.7,43.16,43.13,43.06,42.94,40.4,40.77,38.22,39.15,39.08,38.01,37.58,36.3,34.47,32.78,32.31,31.3,30.86,32.77,35.36,3.39,34.09,35.7,36.68,38.3,38.67,37.41,38.88,39.34,38.52,37.9,37.35,35.56,35.94,34.54,36.47,35.62,35.54,34.7,34.49]
print ("The data is ", data)

length = 10 # default = 25
lsma_val = lsma(data[::-1],length)
print ("The regression line is ", lsma_val[::-1])
historical_df.loc[:,'RL10_Experiment'] = pd.Series(lsma_val[::-1])
print("DF now is ", historical_df)

historical_df.set_index('Date',inplace=True)
historical_df.to_csv('debug1.csv')
