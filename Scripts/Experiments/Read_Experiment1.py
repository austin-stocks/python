import pandas as pd
import json
from pprint import pprint

# data_item = pd.read_json('Read_Experiment1.json')
# print ("Read Data is", data_item )
with open('Read_Experiment1.json') as data_file:
    data_item = json.load(data_file)
pprint(data_item)


print (data_item["maps"][0]["id"])  # will return 'blabla'
print(data_item["masks"][0]["id"])    # will return 'valore'
print(data_item["om_points"])      # will return 'value'