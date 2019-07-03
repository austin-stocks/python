import pandas as pd
import json
from pprint import pprint

# json_data = pd.read_json('Read_Experiment1.json')
# print ("Read Data is", json_data )
with open('json_experiment.json') as json_file:
  json_data = json.load(json_file)
pprint(json_data)

#
ticker = "AAPL"
len_maps = len(json_data[ticker]["maps"])

print (json_data[ticker]["maps"][0]["id"])  # will return 'blabla'
print(json_data[ticker]["masks"][0]["id"])    # will return 'valore'
print(json_data[ticker]["om_points"])      # will return 'value'

print ("The length of the array is : ", len_maps)

# if anchored text exist
# if the length of the keys is > 0
anchored_text_keys = json_data[ticker]["Anchored_Text"].keys()
for i_key in json_data[ticker]["Anchored_Text"].keys():
  print ("Anchored text key :", i_key, " Value :", json_data[ticker]["Anchored_Text"][i_key])


