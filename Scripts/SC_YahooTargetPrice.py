import requests
import bs4
import tkinter as tk
import sys

import urllib.request
import pandas as pd
import html5lib


# -----------------------------------------------------------------------------
# This works -- yeah yeah
# -----------------------------------------------------------------------------
yahoo_quotes_page = 'https://finance.yahoo.com/quote/IBM/'
req = urllib.request.Request(yahoo_quotes_page, headers={'User-Agent': 'Mozilla/5.0'})
html = str(urllib.request.urlopen(req).read())
yahoo_quotes_tables = pd.read_html(html)

print ("The tables are ", yahoo_quotes_tables)

for df_idx in yahoo_quotes_tables:
  print ("The idx is ", df_idx, " and the heading is ", df_idx.columns.values)


# earnings_history_df = yahoo_quotes_tables[2]
# print ("The earnings estimates is ", type(earnings_history_df))

print ("\n\n\n\n")
cnbc_quote_page = 'https://apps.cnbc.com/view.asp?symbol=IBM&uid=stocks/earnings&view=earnings'
req = urllib.request.Request(cnbc_quote_page, headers={'User-Agent': 'Mozilla/5.0'})
html = str(urllib.request.urlopen(req).read())
cnbc_quote_page = pd.read_html(html)

print ("The tables are ", cnbc_quote_page)


import requests

url = "https://apps.cnbc.com/view.asp?symbol=IBM&uid=stocks/earnings&view=earnings"

file_name = "Data.csv"
u = requests.get(url)

# file_size = int(u.headers['content-length'])
# print "Downloading: %s Bytes: %s", % (file_name, file_size)

with open(file_name, 'wb') as f:
    for chunk in u.iter_content(chunk_size=1024):
        if chunk: # filter out keep-alive new chunks
            f.write(chunk)
            f.flush()
f.close()


sys.exit(1)
# -----------------------------------------------------------------------------


# Ask user for the stock ticker of interest
stock_ticker = input('Enter stock ticker: ')
# stock_ticker = 'IBM'

# Concatenate the url with the stock ticker and apply upper() to automatically uppercase user input
link = 'https://finance.yahoo.com/quote/'+ stock_ticker.upper() + '/history?p=' + stock_ticker.upper()
print(link)

# Use pandas read_html() function to read HTL tables into a list of DataFrames objects
df_list = pd.read_html(link)[0].head()

print(df_list)


sys.exit(1)




EPS_Actual = []
EPS_Estimate = []
price = []

window = tk.Tk()
title = tk.Label(text="Target Price Calculator ", fg="purple", width=40, height=1)

first_label = tk.Label(text="Enter Stock Ticker: ", fg="purple", width=40, height=3)
tickers = tk.Entry()
Results = tk.Label(text="Target Price: ", fg="purple")

title.pack()
first_label.pack()
tickers.pack()
Results.pack()


def GO():
  for i in tickers:
    try:
      r = requests.get("https://finance.yahoo.com/quote/" + i + "/analysis?p=" + i).text
      soup = bs4.BeautifulSoup(r, "lxml")
      EPS = soup.findAll("td", class_="Ta(end)")

      EPS = EPS[48].get_text()
      EPS_Actual.append(EPS)

      EST = soup.findAll("td", class_="Ta(end)")

      EST = EST[60].get_text()
      EPS_Estimate.append(EST)

      Price = soup.find("span", class_="Trsdu(0.3s) Fw(b) Fz(36px) Mb(-4px) D(ib)")
      price.append(Price.get_text())
    except:
      tk.Label(window, text="Unable to find {} ".format(i), width=50, height=5, fg="red").pack()
      window.update()

  for actual, estimate, PRICE, tick in zip(EPS_Actual, EPS_Estimate, price, tickers):
    if actual != 'N/A':
      actual = float(actual)
    if estimate != 'N/A':
      estimate = float(estimate)
    if PRICE != 'N/A':
      PRICE = float(PRICE)
    try:
      target = (PRICE * ((PRICE * actual) / (PRICE * estimate)))

      tk.Label(window, text="The target price for {} is {}".format(tick, target), width=40, height=5, fg="green").pack()
      window.update()


    except:
      tk.Label(window, text="Unable to find {} ".format(tick), width=50, height=5, fg="red").pack()
      window.update()


def SUBMIT():
  global tickers
  tickers = tickers.get()
  tickers = [tickers]
  print(tickers)
  GO()


button = tk.Button(text="Find ", fg="purple", command=SUBMIT, width=25)
button.pack()

window.mainloop()