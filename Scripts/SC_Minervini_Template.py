import numpy as np
import yfinance as yf
import plotly.graph_objects as go

def get_slope(x):
  return np.polyfit(x.index.values, x.values, 1)[0]


# -----------------------------------------------------------------------------
# Minervini's Template
# -----------------------------------------------------------------------------
# 1. The current stock price is above both 150 day (30 wk) and 200 day (40 wk)
#    ma price lines
# 2. The 150 day ma is above 200 day ma
# 3. The 200 day ma is trending up for at least 1 month (preferably 4-5 months
#    minimum in most cases)
# 4. The 50 day (10 wk) ma is above both the 150 day and 200 day ma
# 5. The current stock price is trading above 50 day ma
# 6. The current stock price is at least 30% agove it 52 wk low (Many of the best
#    selections will be 100 percent, 300 percent or greater above their 52 wk low
#    before they emergy from a solid consolidate period and mount a large scale
#    advance)
# 7. The current stock price is within atleast 25% of it's 52 wk hight (the closer
#    to high the better)
# 8. The RS ranking (as reported by IBD), is no less than 70 and preferably
#    in the 80s or 90s , which will generally be the case with the better
#    selections

# #1 to #7 are coded below
# -----------------------------------------------------------------------------

ticker_list = ['TQQQ','ANET','CRWD','ADBE']

for ticker in ticker_list:
  df = yf.download(ticker).reset_index()

  # find the moving averages
  df['200_ma'] = df['Close'].rolling(200).mean()
  df['150_ma'] = df['Close'].rolling(150).mean()
  df['50_ma'] = df['Close'].rolling(50).mean()

  # get the slope of the moving average over 1 month
  df['200_ma_slope'] = df['200_ma'].rolling(5*4).apply(get_slope)

  # Determine the 52 week high and low
  df['52_week_low'] = df['Low'].rolling(52*5).min()
  df['52_week_high'] = df['High'].rolling(52*5).max()

  df = df.dropna()

  # Constraints for the trend template
  df['trend_template'] = (
      ((df['Close'] > df['150_ma']) & (df['Close'] > df['200_ma']))
    &  (df['150_ma'] > df['200_ma'])
    &  (df['200_ma_slope'] > 0)
    & ((df['50_ma'] > df['150_ma']) & (df['50_ma'] > df['200_ma']))
    &  (df['Close'] > df['50_ma'])
    &  (df['Close']/df['52_week_low'] > 1.3)
    &  (df['Close']/df['52_week_high'] > 0.75)
  )

  print (df)

  df_filtered = df[
      (df['Date'] < '2022-01-01')
    & (df['Date'] > '2020-01-01')
  ].reset_index()

  df_filtered = df.tail(200).reset_index()

  fig = go.Figure()
  fig.add_trace(
    go.Candlestick(
      x = df_filtered['Date'],
      open = df_filtered['Open'],
      high = df_filtered['High'],
      low = df_filtered['Low'],
      close = df_filtered['Close'],
      showlegend=False,
    )
  )

  for ma in [50,150,200]:
    fig.add_trace(
      go.Line(x=df_filtered['Date'], y=df_filtered[f'{ma}_ma'], name=f'{ma} SMA')
    )

  df_pattern = (
    df_filtered[df_filtered['trend_template']]
    .groupby((~df_filtered['trend_template']).cumsum())
    ['Date']
    .agg(['first','last'])
  )

  for idx, row in df_pattern.iterrows():
    fig.add_vrect(
      x0=row['first'],
      x1=row['last'],
      line_width=0,
      fillcolor='green',
      opacity=0.2,
    )

  fig.update_layout(
    xaxis_rangeslider_visible=False,
    xaxis_title='Date',
    yaxis_title='Price ($)',
    title=str(ticker) + ' - Mark Minervini Tread Template',
    width=1000,
    height=700,
  )

  fig.show()