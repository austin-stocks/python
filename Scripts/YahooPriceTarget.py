import requests
import pandas as pd

tickers = ['QRVO']
#ticker can be any stock in your portfolio, or whatever you've been following lately
targets = []

for item in tickers:
    lhs_url = 'https://query2.finance.yahoo.com/v10/finance/quoteSummary/'
    rhs_url = '?formatted=true&crumb=swg7qs5y9UP&lang=en-US&region=US&' \
              'modules=upgradeDowngradeHistory,recommendationTrend,' \
              'financialData,earningsHistory,earningsTrend,industryTrend&' \
              'corsDomain=finance.yahoo.com'
    #Change region for those who want non-US stocks
    headers = {
        'User-Agent': ''}
    #Add your own user agent address - Just google it on your browser.
    url = lhs_url + item + rhs_url
    print ("This is the url that I sent", url)
    r = requests.get(url, headers=headers)
    print ("This is what I got back", r)
    result = r.json()['quoteSummary']['result'][0]
    print ("The result is", result)
    target = result['financialData']['targetMeanPrice']['fmt']
    #If you want the median version, then replace 'targetMeanPrice' with 'targetMedianPrice'
    targets.append(target)

    print("--------------------------------------------")
    print("{} has an average target price of: ".format(item), target)
