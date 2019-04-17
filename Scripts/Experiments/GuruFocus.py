import urllib.request, json

response = urllib.request.urlopen('https://api.gurufocus.com/public/user/1aa8fe46c95b1a04765958688619d1d7:7b38c3ebb4280faca35db6a381cd04c9/stock/WMT/financials')

content = response.read()
data = json.loads(content.decode('utf8'))
print ("Downloaded Data is", data)
print ("The type of data is ", type(data))

# print(data['Valuation Ratio']['PS Ratio'])