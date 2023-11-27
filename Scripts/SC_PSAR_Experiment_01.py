from collections import deque
import os
import pandas as pd
import matplotlib.pyplot as plt

class PSAR:

  def __init__(self, init_af=0.02, max_af=0.2, af_step=0.02):
    self.max_af = max_af
    self.init_af = init_af
    self.af = init_af
    self.af_step = af_step
    self.extreme_point = None
    self.high_price_trend = []
    self.low_price_trend = []
    self.high_price_window = deque(maxlen=2)
    self.low_price_window = deque(maxlen=2)

    # Lists to track results
    self.psar_list = []
    self.af_list = []
    self.ep_list = []
    self.high_list = []
    self.low_list = []
    self.trend_list = []
    self._num_days = 0

  def calcPSAR(self, high, low):
    if self._num_days >= 3:
      psar = self._calcPSAR()
    else:
      psar = self._initPSARVals(high, low)

    psar = self._updateCurrentVals(psar, high, low)
    self._num_days += 1

    return psar

  def _initPSARVals(self, high, low):
    if len(self.low_price_window) <= 1:
      self.trend = None
      self.extreme_point = high
      return None

    if self.high_price_window[0] < self.high_price_window[1]:
      self.trend = 1
      psar = min(self.low_price_window)
      self.extreme_point = max(self.high_price_window)
    else:
      self.trend = 0
      psar = max(self.high_price_window)
      self.extreme_point = min(self.low_price_window)

    return psar

  def _calcPSAR(self):
    prev_psar = self.psar_list[-1]
    if self.trend == 1: # Up
      psar = prev_psar + self.af * (self.extreme_point - prev_psar)
      psar = min(psar, min(self.low_price_window))
    else:
      psar = prev_psar - self.af * (prev_psar - self.extreme_point)
      psar = max(psar, max(self.high_price_window))

    return psar

  def _updateCurrentVals(self, psar, high, low):
    if self.trend == 1:
      self.high_price_trend.append(high)
    elif self.trend == 0:
      self.low_price_trend.append(low)

    psar = self._trendReversal(psar, high, low)

    self.psar_list.append(psar)
    self.af_list.append(self.af)
    self.ep_list.append(self.extreme_point)
    self.high_list.append(high)
    self.low_list.append(low)
    self.high_price_window.append(high)
    self.low_price_window.append(low)
    self.trend_list.append(self.trend)

    return psar

  def _trendReversal(self, psar, high, low):
    # Checks for reversals
    reversal = False
    if self.trend == 1 and psar > low:
      self.trend = 0
      psar = max(self.high_price_trend)
      self.extreme_point = low
      reversal = True
    elif self.trend == 0 and psar < high:
      self.trend = 1
      psar = min(self.low_price_trend)
      self.extreme_point = high
      reversal = True

    if reversal:
      self.af = self.init_af
      self.high_price_trend.clear()
      self.low_price_trend.clear()
    else:
        if high > self.extreme_point and self.trend == 1:
          self.af = min(self.af + self.af_step, self.max_af)
          self.extreme_point = high
        elif low < self.extreme_point and self.trend == 0:
          self.af = min(self.af + self.af_step, self.max_af)
          self.extreme_point = low

    return psar

# In[5]:

def main():

  ticker = "TQQQ"
  dir_path = os.getcwd()
  backtest_file = dir_path + "\\..\\Back_Testing" + "\\" + "debug1.csv"
  df = pd.read_csv(backtest_file)
  df.reset_index(inplace=True)
  df.set_index('Date',inplace=True)
  print (df)

  # delete adj close and volume
  # as we dont need them
  del df['Adj_Close']
  del df['Volume']
  # no need to iterate over timestamp index
  df.reset_index(inplace=True)
  df = df[:100]
  # df.iloc[::-1]
  df.reset_index(inplace=True)
  df.set_index('Date',inplace=True)
  reversed_df = df.iloc[::-1]
  data = reversed_df.copy()
  data.reset_index(inplace=True)
  data.set_index('Date',inplace=True)
  print (data)


  # Somewhere here calculate the RL10 line on the data (based in the LSMA experiment script)
  # and then, and this is the real experiment, replace 'High' and 'Low' both the columns
  # with RL data and see if the PSAR (remember to modify the acceleartion to 0.02 and the
  # max value to 0.12) matches TC200 value.
  # It is probably wise to do it in experiment_02
  # Should not take much time to see whether this thing is worknig or not...Hopefully
  # may work (Search if this script is using close anywhere)
  # The original columns are 'Date', 'Open', 'High', 'Low', 'Close', 'Adj_Close', 'Volume'
  # Date is used in plot (keep it)
  # Open does not seem to be used anywhere (Leave it as is)
  # High seems to be used only in the next line (Modify this to RL)
  # Low  seems to be used only in the next line (Modify this to RL)
  # Close is used in many places (Keep it, but it can introduce inaccuracy, as the PSAR dots are flipped based on Close but are calcuated based on RL)
  # Adj_Close and Volume have been deleted

  # Maybe a simple thing to do is to modify the TQQQ csv (High and Low) with RL line and see what generates :-)

  indic = PSAR()
  data['PSAR'] = data.apply(lambda x: indic.calcPSAR(x['High'], x['Low']), axis=1)
  # Add supporting data
  data['EP'] = indic.ep_list
  data['Trend'] = indic.trend_list
  data['AF'] = indic.af_list
  print (data.tail())
  print (data['PSAR'].tail())


  colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
  psar_bull = data.loc[data['Trend'] == 1]['PSAR']
  psar_bear = data.loc[data['Trend'] == 0]['PSAR']
  buy_sigs = data.loc[data['Trend'].diff() == 1]['Close']
  short_sigs = data.loc[data['Trend'].diff() == -1]['Close']

  plt.figure(figsize=(12, 8))
  plt.plot(data['Close'], label='Close', linewidth=1, zorder=0)
  plt.scatter(buy_sigs.index, buy_sigs, color=colors[2],
              label='Buy', marker='^', s=100)
  plt.scatter(short_sigs.index, short_sigs, color=colors[4],
              label='Short', marker='v', s=100)
  plt.scatter(psar_bull.index, psar_bull, color=colors[1], label='Up Trend')
  plt.scatter(psar_bear.index, psar_bear, color=colors[3], label='Down Trend')
  plt.xlabel('Date')
  plt.xticks(fontsize=6,rotation=90)
  plt.ylabel('Price ($)')
  plt.title(f'{ticker} Price and Parabolic SAR')
  plt.legend()
  plt.show()


if __name__ == '__main__':
  main()