import json
import os
from pathlib import Path
from datetime import datetime, timedelta
import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv
import requests
from yahooquery import Ticker
import logging
import os
import sys
import datetime as dt

tda_url = 'https://api.tdameritrade.com/v1/marketdata/{ticker}/pricehistory'
load_dotenv()

# -------------------------------------------------------------
# Set the buy and sell price based on strategy and price quality
# -------------------------------------------------------------
def calculate_buysell_prices(row, invest_strategy,price_quality):
  open_price = row['Open']
  high_price = row['High']
  low_price = row['Low']
  close_price = row['Adj_Close']

  if (price_quality == 'Best'):
    if (invest_strategy == "Long"):
      buy_price = low_price
      sell_price = high_price
    else:
      buy_price = high_price
      sell_price = low_price
  elif (price_quality == 'Worst'):
    if (invest_strategy == "Long"):
      buy_price = high_price
      sell_price = low_price
    else:
      buy_price = low_price
      sell_price = high_price
  elif (price_quality == "Open"):
    buy_price = open_price
    sell_price = open_price
  elif (price_quality == "Close"):
    buy_price = close_price
    sell_price = close_price
  elif (price_quality == "Average"):
    buy_price = (low_price + high_price) / 2
    sell_price = (low_price + high_price) / 2

  return buy_price, sell_price
  # -------------------------------------------------------------

def main():
  # -----------------------------------------------------------------------------
  # Read the master tracklist file into a dataframe
  # -----------------------------------------------------------------------------
  dir_path = os.getcwd()
  user_dir = "\\..\\" + "User_Files"
  log_dir = "\\..\\" + "Logs"
  historical_dir = "\\..\\" + "Historical"
  Yahoo_historical_download_dir = "\\..\\" + "Download\YahooHistorical"
  Back_Testing_dir = "\\..\\" + "Back_Testing"
  tracklist_file = "Tracklist.csv"
  tracklist_file_full_path = dir_path + user_dir + "\\" + tracklist_file

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
                      filename=dir_path + log_dir + "\\" + 'SC_Performance_with_BuySell_Dates_debug.txt',
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

  # disable and enable global level logging
  logging.disable(sys.maxsize)
  logging.disable(logging.NOTSET)
  # -----------------------------------------------------------------------------
  pd.set_option('display.max_columns', None)
  pd.set_option('display.max_rows', None)
  pd.set_option('display.width', 1000)

  tracklist_df = pd.read_csv(tracklist_file_full_path)
  # print ("The Tracklist df is", tracklist_df)
  tracklist_df.sort_values('Tickers', inplace=True)
  ticker_list_unclean = tracklist_df['Tickers'].tolist()
  ticker_list = [x for x in ticker_list_unclean if str(x) != 'nan']

  portfolio_start_value = 10000
  invest_strategy = "Long"
  # If you want to iterate over this?
  # price_quality_list = ['Best', 'Worst', 'Open', 'Close', 'Average']
  price_quality = 'Average'

  # ticker_list = ['PLUS','AUDC', 'MED', 'IBM']
  i_int = 1
  for ticker_raw in ticker_list:
    ticker = ticker_raw.replace(" ", "").upper()  # Remove all spaces from ticker_raw and convert to uppercase
    historical_df = pd.read_csv(dir_path + Yahoo_historical_download_dir + "\\" + ticker + "_yahoo_historical.csv")
    logging.debug ("The Historical Dataframe is : \n" + historical_df.to_string())
    buysell_dates_df = pd.read_csv(dir_path + Back_Testing_dir + "\\" + ticker + "_BuySell_Dates.csv")
    logging.debug ("The BuySell Dates df is : \n" + buysell_dates_df.to_string())

    buy_dates_list = buysell_dates_df['Buy'].dropna().tolist()
    sell_dates_list = buysell_dates_df['Sell'].dropna().tolist()
    latest_date_in_historical_file = historical_df['Date'].tolist()[0]

    # -------------------------------------------------------------------------
    # Sanity Checks
    # -------------------------------------------------------------------------
    # For Long :
    #   If there is sell date missing at the end (it is assumed in this block of
    #   code that it is the end/last entry that is missing the date), then
    #   replace that sell date by the latest date from Historical
    #   It just means that the strategy has not generated a sell signal and the
    #   last sell (for our calculation purposes can be the last date for which
    #   historical data is available)
    #  For Short :
    #   Same but in reverse
    # -------------------------------------------------------------------------
    no_of_buy_dates = len(buy_dates_list)
    no_of_sell_dates = len(sell_dates_list)
    if (no_of_buy_dates != no_of_sell_dates):
      if (invest_strategy == "Long") and  ((no_of_buy_dates - no_of_sell_dates) > 1):
        logging.error("Invest Strategy : " + str(invest_stragtey))
        logging.error("Number of Buy  dates : " + str(no_of_buy_dates))
        logging.error("Number of Sell dates : " + str(no_of_sell_dates))
        logging.error("Number of Buy dates is atleast 2 more than the number of Sell dates")
        logging.error("They should either be same OR the Sell date on the last buy date can be missing")
        logging.error("The sell date after the last buy date can be missing. In that case the script will replace the latest historical with the Buy date")
        logging.error("Please correct and rerun...")
        sys.exit()
      elif (invest_strategy == "Long") and ((no_of_buy_dates - no_of_sell_dates) == 1):
        sell_dates_list.append(latest_date_in_historical_file)
        logging.info("")
        logging.info("====================")
        logging.info("The last Sell Date is missing the Buy/Sell file")
        logging.info("That is probably alright as the strategy might not have generated a Sell signal yet")
        logging.info("For our calcuations, adding the latest date from Historical Data : " + str(latest_date_in_historical_file) + ", to the Sell Dates")
        logging.info("====================")
        logging.info("")
      elif (invest_strategy == "Short") and ((no_of_sell_dates - no_of_buy_dates) > 1):
        logging.error("Invest Strategy : " + str(invest_stragtey))
        logging.error("Number of Buy  dates : " + str(no_of_buy_dates))
        logging.error("Number of Sell dates : " + str(no_of_sell_dates))
        logging.error("Number of Sell dates is atleast 2 more than the number of Buy dates")
        logging.error("They should either be same OR the Buy date on the last buy date can be missing")
        logging.error("The Buy date after the last Sell date can be missing. In that case the script will replace the latest historical with the Buy date")
        logging.error("Please correct and rerun...")
        sys.exit()
      elif (invest_strategy == "Short") and ((no_of_sell_dates - no_of_buy_dates) == 1):
        buy_dates_list.append(latest_date_in_historical_file)
        logging.info("")
        logging.info("====================")
        logging.info("The last Buy Date is missing the Buy/Sell file")
        logging.info("That is probably alright as the strategy might not have generated a Buy signal yet")
        logging.info("For our calcuations, adding the latest date from Historical Data : " + str(latest_date_in_historical_file) + ", to the Buy Dates")
        logging.info("====================")
        logging.info("")
      # -------------------------------------------------------------------------

    buy_dates_list_dt = sorted([dt.datetime.strptime(date, '%m/%d/%Y').date() for date in buy_dates_list])
    sell_dates_list_dt = sorted([dt.datetime.strptime(date, '%m/%d/%Y').date() for date in sell_dates_list])

    for i_idx, date_dt in enumerate(buy_dates_list_dt):
      if (invest_strategy == "Long") and (date_dt > sell_dates_list_dt[i_idx]) :
          logging.error("")
          logging.error("====================")
          logging.error("Invest Strategy : " + str(invest_strategy))
          logging.error("At Sorted dates Row " + str(i_idx+1))
          logging.error("The Sell date : " + str(sell_dates_list_dt[i_idx]) + ", is ***** EARLIER ***** than the corresponding Buy date : " + str(date_dt))
          logging.error("For Long strategy, the Sell date should should always be later than that Buy date")
          logging.error("Please check the BuySell Dates file, rectify and rerun...")
          logging.error("====================")
          logging.error("")
          sys.exit()
      # Todo : Test this out
      # Todo : Test out for the dates that are NOT in historical
      #   Case 1 : Not in historical and NOT beyond the latest date
      #   Case 2 : Not in historical and     beyond the latest date
      elif (invest_strategy == "Short") and (sell_dates_list_dt[i_idx] > date_dt) :
          logging.error("")
          logging.error("====================")
          logging.error("Invest Strategy : " + str(invest_strategy))
          logging.error("At Sorted dates Row " + str(i_idx+1))
          logging.error("The Buy date : " + str(date_dt) + ", is ***** EARLIER ***** than the Sell date : " + str(sell_dates_list_dt[i_idx]))
          logging.error("For Short strategy, the Buy date should should always be later than that Sell date")
          logging.error("Please check the BuySell Dates file, rectify and rerun...")
          logging.error("====================")
          logging.error("")
          sys.exit()

    days_strategy_was_employed = (sell_dates_list_dt[-1] - buy_dates_list_dt[0]).days
    # logging.debug("Sorted Buy  Dates dt : " + str(buy_dates_list_dt))
    # logging.debug("Sorted Sell Dates dt : " + str(sell_dates_list_dt))

    buy_dates_list = [dt.datetime.strftime(date, '%m/%d/%Y') for date in buy_dates_list_dt]
    sell_dates_list = [dt.datetime.strftime(date, '%m/%d/%Y') for date in sell_dates_list_dt]
    logging.debug("Sorted Buy  Dates : " + str(buy_dates_list))
    logging.debug("Sorted Sell Dates : " + str(sell_dates_list))

    logging.debug("This is a " + str(invest_strategy) + " strategy")

    found_first_trade = 0
    no_of_trades = 0
    for i_index, row in historical_df[::-1].iterrows():
      historical_date = row['Date']
      historical_date_dt = dt.datetime.strptime(historical_date, '%m/%d/%Y').date()
      historical_date = dt.datetime.strftime(historical_date_dt, '%m/%d/%Y')

      buy_price, sell_price = calculate_buysell_prices(row, invest_strategy,price_quality)
      historical_df.at[i_index, 'Positioning'] = "N/A"
      prev_positioning = "N/A"

      if (invest_strategy == "Long"):
        if (found_first_trade == 1):
          prev_positioning = historical_df.at[i_index+1, 'Positioning']
          prev_port_value = historical_df.at[i_index+1, 'Port Value']
        # -------------------------------------------------
        # First Buy or a Buy after position in cash or sell
        # -------------------------------------------------
        if (historical_date in buy_dates_list):
          historical_df.at[i_index, 'Positioning'] = "Buy"
          no_of_trades = no_of_trades + 1
          if (prev_positioning == "N/A"): # Indicates first buy
            found_first_trade = 1
            historical_df.at[i_index, 'Port Value'] = portfolio_start_value
            historical_df.at[i_index, 'Buy_and_Hold'] = portfolio_start_value
            logging.debug("Found (first) buy at :  " + str(historical_date) + ", Buy Price : " + str(buy_price)  +  ", Positioning : " + str(historical_df.at[i_index, 'Positioning']))
          elif (prev_positioning == "Cash") or (prev_positioning == "Sell"):
            historical_df.at[i_index, 'Port Value'] = prev_port_value
        # -------------------------------------------------
        # First day after buy
        # -------------------------------------------------
        elif (historical_date not in buy_dates_list) and (historical_date not in sell_dates_list) and (prev_positioning == "Buy"):
          historical_df.at[i_index, 'Positioning'] = "Market"
          portfolio_value = historical_df.at[i_index+1, 'Port Value']*(historical_df.at[i_index, 'Adj_Close']/historical_df.at[i_index+1, 'Adj_Close'])
          historical_df.at[i_index, 'Port Value'] = portfolio_value
        # -------------------------------------------------
        # After buy, now in market and not selling
        # -------------------------------------------------
        elif (historical_date not in buy_dates_list) and (historical_date not in sell_dates_list) and (prev_positioning == "Market"):
          historical_df.at[i_index, 'Positioning'] = "Market"
          portfolio_value = historical_df.at[i_index+1, 'Port Value']*(historical_df.at[i_index, 'Adj_Close']/historical_df.at[i_index+1, 'Adj_Close'])
          historical_df.at[i_index, 'Port Value'] = portfolio_value
        # -------------------------------------------------
        # Either bought last day or in the market and selling
        # -------------------------------------------------
        elif (historical_date in sell_dates_list) and (prev_positioning == "Market") or (prev_positioning == "Buy"):
          no_of_trades = no_of_trades + 1
          historical_df.at[i_index, 'Positioning'] = "Sell"
          portfolio_value = historical_df.at[i_index+1, 'Port Value']*(sell_price/historical_df.at[i_index+1, 'Adj_Close'])
          historical_df.at[i_index, 'Port Value'] = portfolio_value
        # -------------------------------------------------
        # First day after sell
        # -------------------------------------------------
        elif (historical_date not in buy_dates_list) and (historical_date not in sell_dates_list) and (prev_positioning == "Sell"):
          historical_df.at[i_index, 'Positioning'] = "Cash"
          portfolio_value = historical_df.at[i_index+1, 'Port Value']
          historical_df.at[i_index, 'Port Value'] = portfolio_value
        # -------------------------------------------------
        # Now in cash
        # -------------------------------------------------
        elif (historical_date not in buy_dates_list) and (historical_date not in sell_dates_list) and (prev_positioning == "Cash"):
          historical_df.at[i_index, 'Positioning'] = "Cash"
          portfolio_value = historical_df.at[i_index+1, 'Port Value']
          historical_df.at[i_index, 'Port Value'] = portfolio_value
        # -------------------------------------------------
        # Buy and Hold - Start calculation after first buy
        # -------------------------------------------------
        if (found_first_trade == 1) and (prev_positioning != "N/A"):
          buy_and_hold_value = historical_df.at[i_index+1, 'Buy_and_Hold']*(historical_df.at[i_index, 'Adj_Close']/historical_df.at[i_index+1, 'Adj_Close'])
          historical_df.at[i_index, 'Buy_and_Hold'] = buy_and_hold_value







    portfolio_final_val = buy_and_hold_value = historical_df.at[0, 'Port Value']
    buy_and_hold_final_val = buy_and_hold_value = historical_df.at[0, 'Buy_and_Hold']
    logging.debug ("The Historical Dataframe is : \n" + historical_df.to_string())

    logging.info("Starting Capital : " + str(portfolio_start_value))
    logging.info("Strategy : " + str(invest_strategy))
    logging.info("Price Quality to execute Trades : " + str(price_quality))
    logging.info("Start Date : " + str(buy_dates_list[0]) + ", Stop Date " + str(sell_dates_list[-1]))
    logging.info("# of days stragey was in play : " + str(days_strategy_was_employed) )
    logging.info("# of Trades : " + str(no_of_trades) )
    logging.info("Final Portfolio value        : " + str(round(portfolio_final_val,2)) +
                 ", Total Return : "  + str( round(((portfolio_final_val/portfolio_start_value-1)*100),2)) + "%"
                 ", Annualized Return : "  + str( round(((((portfolio_final_val/portfolio_start_value)**(365/days_strategy_was_employed))-1)*100),2)) + "%")
    logging.info("Buy and Hold Portfolio value : " + str(round(buy_and_hold_final_val,2)) +
                 ", Total Return : " + str(round(((buy_and_hold_final_val / portfolio_start_value - 1) * 100),2)) + "%"
                 ", Annualized Return : "  + str( round(((((buy_and_hold_final_val/portfolio_start_value)**(365/days_strategy_was_employed))-1)*100),2)) + "%")


if __name__ == "__main__":
    main()


# Somo other stuff
# https://www.quantifiedstrategies.com/python-and-macd-trading-invest_strategy/
# https://www.alpharithms.com/calculate-macd-python-272222/




# def get_database_connection():
#     conn = psycopg2.connect(
#         dbname=os.environ['dbname'],
#         user=os.environ['dbusername'],
#         password=os.environ['dbpassword']
#     )
#     return conn
#
#
# def get_price_history(symbol):
#     ticker = Ticker(symbol)
#     df = ticker.history()
#     df = df.reset_index()
#     return df
#
#
# def get_up_or_down(df):
#     for i in range(len(df)):
#         if df.iloc[i]['close'] >= df.iloc[i-1]['close']:
#             df.at[i, 'gain'] = df.iloc[i]['close'] - df.iloc[i-1]['close']
#             df.at[i, 'loss'] = 0
#         elif df.iloc[i]['close'] < df.iloc[i-1]['close']:
#             df.at[i, 'loss'] = df.iloc[i-1]['close'] - df.iloc[i]['close']
#             df.at[i, 'gain'] = 0
#         else:
#             df.at[i, 'gain'] = 0
#             df.at[i, 'loss'] = 0
#     return df
#
#
# def get_average_gains(df, period):
#     for i in range(len(df)):
#         n, up, down = 0, 0, 0
#         if i == period:
#             while n < period:
#                 if df.iloc[i-n]['gain'] > 0:
#                     up += df.iloc[i-n]['gain']
#                 elif df.iloc[i-n]['loss'] > 0:
#                     down += df.iloc[i-n]['loss']
#                 else:
#                     up += 0
#                     down += 0
#                 n += 1
#             df.at[i, 'ag'] = up/period
#             df.at[i, 'al'] = down/period
#         elif i > period:
#             df.at[i, 'ag'] = (df.iloc[i-1]['ag'] * (period - 1) + df.iloc[i]['gain'])/period
#             df.at[i, 'al'] = (df.iloc[i-1]['al'] * (period - 1) + df.iloc[i]['loss'])/period
#             df['ag'] = df['ag'].fillna(0)
#             df['al'] = df['al'].fillna(0)
#     return df
#
#
# def get_relative_strength(df, period):
#     for i in range(len(df)):
#         if i >= period:
#             df.at[i, 'rs'] = df.iloc[i]['ag']/df.iloc[i]['al']
#             df.at[i, 'rsi'] = (100-(100/(1+df.iloc[i]['rs'])))
#     return df
#
#
# def get_relative_strength_index(df):
#     df = get_up_or_down(df)
#     df = get_average_gains(df, 14)
#     df = get_relative_strength(df, 14)
#     pd.set_option('display.max_columns', None)
#     pd.set_option('display.max_rows', None)
#     pd.set_option('display.width', 1000)
#     return df
#
#
# def get_stochastic_oscillator(df, period=14):
#     for i in range(len(df)):
#         low = df.iloc[i]['close']
#         high = df.iloc[i]['close']
#         if i >= period:
#             n = 0
#             while n < period:
#                 if df.iloc[i-n]['close'] >= high:
#                     high = df.iloc[i-n]['close']
#                 elif df.iloc[i-n]['close'] < low:
#                     low = df.iloc[i-n]['close']
#                 n += 1
#             df.at[i, 'best_low'] = low
#             df.at[i, 'best_high'] = high
#             df.at[i, 'fast_k'] = 100*((df.iloc[i]['close']-df.iloc[i]['best_low'])/(df.iloc[i]['best_high']-df.iloc[i]['best_low']))
#
#     df['fast_d'] = df['fast_k'].rolling(3).mean().round(2)
#     df['slow_k'] = df['fast_d']
#     df['slow_d'] = df['slow_k'].rolling(3).mean().round(2)
#
#     return df
#
#
# def get_moving_averages(symbol):
#     ticker = Ticker(symbol)
#     end_date = datetime.today() - timedelta(days=700)
#     df = ticker.history(
#         period='year', interval='1d', start=end_date, end=datetime.today())
#     df = df.reset_index()
#     df['ma50'] = df['close'].rolling(50).mean()
#     df['ma200'] = df['close'].rolling(200).mean()
#     return df
#
#
# def chart_price_history(symbol):
#     df = get_moving_averages(symbol)
#
#     plt.figure(figsize=[16, 8])
#     plt.style.use('default')
#     fig, ax = plt.subplots()
#
#     plt.plot(df['close'], label='data')
#     plt.plot(df['ma50'], label='data')
#     plt.plot(df['ma200'], label='data')
#
#     ax.grid(True)
#     ax.set_ylabel(r'Price [\$]')
#     ax.set_title(symbol, loc='left', y=0.85, x=0.02, fontsize='medium')
#     for label in ax.get_xticklabels(which='major'):
#         label.set(rotation=30, horizontalalignment='right')
#     plt.show()
#
#
# def chart_stochastic_oscillator(ticker, df):
#     plt.figure(figsize=[16, 8])
#     plt.style.use('default')
#     fig, ax = plt.subplots(figsize=(5, 1))
#
#     plt.plot(df['date'], df['fast_k'], color='orange', linewidth=.75)
#     plt.plot(df['date'], df['fast_d'], color='grey', linewidth=.75)
#     plt.plot(df['date'], df['slow_d'], color='green', linewidth=.75)
#
#     ax.grid(True)
#     ax.set_ylabel(r'Price [\$]')
#     ax.set_title(ticker, loc='left', y=0.85, x=0.02, fontsize='medium')
#     ax.set_ylim(0, 100)
#     ax.axhline(y=80, color='b', linestyle='-')
#     ax.axhline(y=20, color='r', linestyle='-')
#     plt.show()
#
#
# def chart_stochastic_oscillator_and_price(ticker, df):
#
#     df['ma50'] = df['close'].rolling(50).mean()
#     df['ma200'] = df['close'].rolling(200).mean()
#
#     plt.figure(figsize=[16, 8])
#     plt.style.use('default')
#     fig, ax = plt.subplots(2, gridspec_kw={'height_ratios': [3, 1]})
#     fig.suptitle(ticker)
#     plt.subplots_adjust(hspace=0.02)
#     ax[0].grid(True)
#     ax[0].axes.get_xaxis().set_visible(False)  # Remove X labels
#     ax[0].set_ylabel(r'Price [\$]')
#     ax[0].plot(df['close'], color='black', linewidth=1)
#
#     ax[1].plot(df['date'], df['fast_k'], color='orange', linewidth=1)
#     ax[1].plot(df['date'], df['fast_d'], color='grey', linewidth=1)
#     ax[1].plot(df['date'], df['slow_d'], color='green', linewidth=1)
#     ax[1].grid(True)
#     ax[1].set_ylabel(r'S.O.')
#     ax[1].set_ylim(0, 100)
#     ax[1].axhline(y=80, color='b', linestyle='-')
#     ax[1].axhline(y=20, color='r', linestyle='-')
#     plt.xticks(rotation=30, ha='right')
#     plt.show()
#
#
# def chart_candlesticks(ticker, df):
#
#     width = .5
#     width2 = .05
#
#     up = df[df.close >= df.open]
#     down = df[df.close < df.open]
#
#     col1 = 'green'
#     col2 = 'red'
#
#     plt.figure()
#     fig, ax = plt.subplots()
#     ax.set_title(ticker)
#     fig.subplots_adjust(bottom=0.2)
#
#     plt.grid(True)
#     plt.bar(up.index, up.close - up.open, width, bottom=up.open, color=col1)
#     plt.bar(up.index, up.high - up.close, width2, bottom=up.close, color=col1)
#     plt.bar(up.index, up.low - up.open, width2, bottom=up.open, color=col1)
#
#     plt.bar(down.index, down.close - down.open, width, bottom=down.open, color=col2)
#     plt.bar(down.index, down.high - down.open, width2, bottom=down.open, color=col2)
#     plt.bar(down.index, down.low - down.close, width2, bottom=down.close, color=col2)
#     plt.xticks(rotation=45, ha='right')
#     plt.show()
#
#
# def chart_volume(ticker, df):
#     plt.figure()
#     fig, ax = plt.subplots()
#     ax.set_title(ticker)
#     fig.subplots_adjust(bottom=0.2)
#     plt.plot(df['volume'], label='data')
#     ax.set_ylabel(r'Volume')
#     for label in ax.get_xticklabels(which='major'):
#         label.set(rotation=30, horizontalalignment='right')
#     plt.show()
#
#
#
#
#
# def chart_rsi(ticker, df):
#     plt.figure()
#     fig, ax = plt.subplots()
#     ax.set_title(ticker)
#     fig.subplots_adjust(bottom=0.2)
#     ax.plot(df['Date'], df['rsi'])
#     ax.set_ylim(0, 100)
#     ax.axhline(y=70, color='r', linestyle='-')
#     ax.axhline(y=30, color='r', linestyle='-')
#     ax.grid(True)
#     ax.set_ylabel(r'RSI')
#     for label in ax.get_xticklabels(which='major'):
#         label.set(rotation=30, horizontalalignment='right')
#     plt.show()
#
#
# def chart_volume_and_averages(ticker, df):
#     # Create a new column in dataframe and populate with bar color
#     i = 0
#     while i < len(df):
#         if df.iloc[i]['close'] >= df.iloc[i-1]['close']:
#             df.at[i, 'color'] = "green"
#         elif df.iloc[i]['close'] < df.iloc[i-1]['close']:
#             df.at[i, 'color'] = "red"
#         else:
#             df.at[i, 'color'] = "blue"
#         i += 1
#
#     # Set up the chart
#     plt.figure(figsize=[16, 8])
#     plt.style.use('default')
#     fig, ax = plt.subplots(2, gridspec_kw={'height_ratios': [3, 1]})
#     fig.suptitle(ticker)
#
#     # Draw the price history
#     ax[0].plot(df['Date'], df['close'])
#     ax[0].axes.get_xaxis().set_visible(False)  # Remove X labels
#     ax[0].grid(True)
#
#     # Draw the volume
#     ax[1].bar(df['Date'], df['volume'], color=df['color'])
#     ax[1].grid(True)
#
#     # Tweak chart to display better
#     plt.xticks(rotation=45, ha='right')
#     plt.subplots_adjust(bottom=0.2)
#     plt.show()
#
#
# def chart_rsi_with_candles(ticker, df):
#     plt.figure()
#     fig, ax = plt.subplots(2, gridspec_kw={'height_ratios': [3, 1]})
#     fig.suptitle(ticker)
#
#     width = .5
#     width2 = .05
#     col1 = 'green'
#     col2 = 'red'
#     up = df[df.close >= df.open]
#     down = df[df.close < df.open]
#     fig.subplots_adjust(bottom=0.2)
#
#     ax[0].grid(True)
#     ax[0].set_ylabel(r'PRICE')
#     ax[0].axes.get_xaxis().set_visible(False)  # Remove X labels
#     ax[0].bar(up.index, up.close - up.open, width, bottom=up.open, color=col1)
#     ax[0].bar(up.index, up.high - up.close, width2, bottom=up.close, color=col1)
#     ax[0].bar(up.index, up.low - up.open, width2, bottom=up.open, color=col1)
#     ax[0].bar(down.index, down.close - down.open, width, bottom=down.open, color=col2)
#     ax[0].bar(down.index, down.high - down.open, width2, bottom=down.open, color=col2)
#     ax[0].bar(down.index, down.low - down.close, width2, bottom=down.close, color=col2)
#
#     ax[1].plot(df['date'], df['rsi'])
#     ax[1].set_ylim(0, 100)
#     ax[1].axhline(y=70, color='r', linestyle='-')
#     ax[1].axhline(y=30, color='r', linestyle='-')
#     ax[1].grid(True)
#     ax[1].set_ylabel(r'RSI')
#     for label in ax[1].get_xticklabels(which='major'):
#         label.set(rotation=30, horizontalalignment='right')
#     plt.show()
#
#
#
