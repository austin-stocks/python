import pandas as pd

aaii_analysts_projection_file = "AAII_Analysts_2025_06_16.csv"

aaii_missing_tickers_list = [
'CRZO','GOOG','RACE','WCG','FOX','DISCK','BRK-B'
]


aaii_qtr_or_yr_report_dates_too_far_apart = ['RETC',
                                             'TURN',
                                             'GOED',
                                             'ACBM',  # Changed the yr fiscal
                                             'ADMP',  # yr  dates are 275 days apart
                                             'ADAP',  # yr  dates are 184 days apart
                                             'ADTX',  # qtr dates are 183 days apart
                                             'AAP',   # qtr dates are 112 days apart
                                             'AEG',   # qtr dates are 184 days apart
                                             'AJRD',  # yr  dates are 397 days apart
                                             'AKOM',  # yr  dates are 275 days apart
                                             'AFIB']  # qtr datea are 275 days apart

master_to_aaii_ticker_xlate = pd.DataFrame(
  {'Ticker': ['GOOG', 'BRK-B'],
   'aaii_tracking_ticker': ['GOOGL', 'BRK.A']}
)
