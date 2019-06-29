import datetime as dt
import os
# import pandas.io.data as web
import numpy as np
import pandas as pd
import plotly.plotly as py
import plotly.io as pio
import plotly

plotly.tools.set_credentials_file(username='sundeep_chadha', api_key='K8uygD8krqX8PMJZ2LjX')

INCREASING_COLOR = '#17BECF'
DECREASING_COLOR = '#7F7F7F'

historical_df = pd.read_csv('AAPL_historical.csv')
historical_df.dropna(inplace=True)

print ("The historical data is : ",historical_df)

# =============================================================================
# =============================================================================
# =============================================================================
data = [ dict(
    type = 'candlestick',
    open = historical_df.Open,
    high = historical_df.High,
    low = historical_df.Low,
    close = historical_df.Close,
    x = historical_df.index,
    yaxis = 'y2',
    name = 'AAPL',
    increasing = dict( line = dict( color = INCREASING_COLOR ) ),
    decreasing = dict( line = dict( color = DECREASING_COLOR ) ),
) ]

layout=dict()

fig = dict( data=data, layout=layout )
# =============================================================================

# =============================================================================
# Create the Layout Object
# =============================================================================
fig['layout'] = dict()
fig['layout']['plot_bgcolor'] = 'rgb(250, 250, 250)'
fig['layout']['xaxis'] = dict( rangeselector = dict( visible = True ) )
fig['layout']['yaxis'] = dict( domain = [0, 0.2], showticklabels = False )
fig['layout']['yaxis2'] = dict( domain = [0.2, 0.8] )
fig['layout']['legend'] = dict( orientation = 'h', y=0.9, x=0.3, yanchor='bottom' )
fig['layout']['margin'] = dict( t=40, b=40, r=40, l=40 )
# =============================================================================

# =============================================================================
# Add range buttons
# =============================================================================
rangeselector = dict(
    visibe=True,
    x=0, y=0.9,
    bgcolor='rgba(150, 200, 250, 0.4)',
    font=dict(size=13),
    buttons=list([
        dict(count=1,
             label='reset',
             step='all'),
        dict(count=1,
             label='1yr',
             step='year',
             stepmode='backward'),
        dict(count=3,
             label='3 mo',
             step='month',
             stepmode='backward'),
        dict(count=1,
             label='1 mo',
             step='month',
             stepmode='backward'),
        dict(step='all')
    ]))

fig['layout']['xaxis']['rangeselector'] = rangeselector
# =============================================================================

# Add moving average
def movingaverage(interval, window_size=10):
    window = np.ones(int(window_size))/float(window_size)
    return np.convolve(interval, window, 'same')


# Set the volume bar chart
colors = []

for i in range(len(historical_df.Close)):
    # if i != 0:
    #     if historical_df.Close[i] > historical_df.Close[i-1]:
    #         colors.append(INCREASING_COLOR)
    #     else:
    #         colors.append(DECREASING_COLOR)
    # else:
    colors.append(DECREASING_COLOR)


# Add the bollinger bands
def bbands(price, window_size=10, num_of_std=5):
    rolling_mean = price.rolling(window=window_size).mean()
    rolling_std  = price.rolling(window=window_size).std()
    upper_band = rolling_mean + (rolling_std*num_of_std)
    lower_band = rolling_mean - (rolling_std*num_of_std)
    return rolling_mean, upper_band, lower_band

bb_avg, bb_upper, bb_lower = bbands(historical_df.Close)

fig['data'].append( dict( x=historical_df.index, y=bb_upper, type='scatter', yaxis='y2',
                         line = dict( width = 1 ),
                         marker=dict(color='#ccc'), hoverinfo='none',
                         legendgroup='Bollinger Bands', name='Bollinger Bands') )

fig['data'].append( dict( x=historical_df.index, y=bb_lower, type='scatter', yaxis='y2',
                         line = dict( width = 1 ),
                         marker=dict(color='#ccc'), hoverinfo='none',
                         legendgroup='Bollinger Bands', showlegend=False ) )

# plot
# py.iplot( fig, filename = 'candlestick-test-3', validate = False )
iplot( fig)
pio.write_image(fig, 'fig1.jpeg')
