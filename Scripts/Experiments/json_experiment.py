import pandas as pd
import json
from pprint import pprint
import datetime as dt
import sys

# json_data = pd.read_json('Read_Experiment1.json')
# print ("Read Data is", json_data )
with open('json_experiment.json') as json_file:
  json_data = json.load(json_file)
pprint(json_data)

#
ticker = "UFPI"

# len_maps = len(json_data[ticker]["maps"])
# print (json_data[ticker]["maps"][0]["id"])  # will return 'blabla'
# print(json_data[ticker]["masks"][0]["id"])    # will return 'valore'
# print(json_data[ticker]["om_points"])      # will return 'value'
#
# print ("The length of the array is : ", len_maps)
#
# print("\n========== Now really starting ticker processing ==========\n")
# # if anchored text exist
# if ("Anchored_Text" in json_data[ticker]):
#   # if the length of the keys is > 0
#   if (len(json_data[ticker]["Anchored_Text"].keys()) > 0 ):
#     anchored_text_keys = json_data[ticker]["Anchored_Text"].keys()
#     for i_key in json_data[ticker]["Anchored_Text"].keys():
#       print ("Anchored text key :", i_key, " Value :", json_data[ticker]["Anchored_Text"][i_key])
#   else:
#     print("\"Anchored_Text\" exits but seems empty for ", ticker)
# else:
#   print ("\"Anchored_Text\" does not exist for ", ticker)
#
#

qtr_eps_df = pd.read_csv(ticker + "_earnings.csv")
qtr_eps_date_list = [dt.datetime.strptime(date, '%m/%d/%Y').date() for date in qtr_eps_df.Date.dropna().tolist()]
qtr_eps_list = qtr_eps_df.Q_EPS.tolist()
print ("The date list for qtr_eps is ", qtr_eps_date_list, "\nand the number of elements are", len(qtr_eps_date_list))
print ("The Earnings list for qtr_eps is ", qtr_eps_list)

# Handle the case if the split is not separated by :
split_dates = list()
split_multiplier = list()
print ("Tickers in json data: ",json_data.keys())
if (ticker not in json_data.keys()):
  print (ticker, "does not exist in json data")
else :
  if ("Splits" in json_data[ticker]):
    # if the length of the keys is > 0
    if (len(json_data[ticker]["Splits"].keys()) > 0 ):
      split_keys = json_data[ticker]["Splits"].keys()
      print ("Split Date list is: ", split_keys)
      for i_key in split_keys:
        print ("Split Date :", i_key, "Split Factor :", json_data[ticker]["Splits"][i_key])
        try:
         split_dates.append(dt.datetime.strptime(str(i_key),"%m/%d/%Y").date())
        except (ValueError):
         print ("\n***** Error : The split Date: ",i_key,"does not seem to be right. Should be in the format %m/%d/%Y...please check *****")
         sys.exit(1)
        try:
          (numerator, denominator) = json_data[ticker]["Splits"][i_key].split(":")
          split_multiplier.append(float(denominator)/float(numerator))
        except (ValueError):
          print ("\n***** Error : The split factor: ",json_data[ticker]["Splits"][i_key],"for split date :", i_key , "does not seem to have right format [x:y]...please check *****")
          sys.exit(1)
      for i in range(len(split_dates)):
        qtr_eps_list_mod = qtr_eps_list.copy()
        print("Split Date :", split_dates[i], " Multiplier : ", split_multiplier[i])
        for j in range(len(qtr_eps_date_list)):
          if (split_dates[i] > qtr_eps_date_list[j]):
            qtr_eps_list_mod[j] = round(qtr_eps_list[j] * split_multiplier[i], 4)
            print("Earnings date ", qtr_eps_date_list[j], " is older than split date. Changed ", qtr_eps_list[j], " to ",
                  qtr_eps_list_mod[j])
        qtr_eps_list = qtr_eps_list_mod.copy()
    else:
      print("\"Splits\" exits but seems empty for ", ticker)
  else:
    print ("\"Splits\" does not exist for ", ticker)


# for i in range(len(split_dates)):
#   print ("Split Date: ", split_dates[i], " Split Factor :", split_multiplier[i])

qtr_eps_list_mod.clear()
print ("The date list for qtr_eps is ", qtr_eps_date_list, "\nand the number of elements are", len(qtr_eps_date_list))
print ("The Original Earnings list for qtr_eps is ", qtr_eps_list)

