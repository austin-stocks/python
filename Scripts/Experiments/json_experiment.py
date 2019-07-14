import pandas as pd
import json
from pprint import pprint
import datetime as dt
import sys

# config_json = pd.read_json('Read_Experiment1.json')
# print ("Read Data is", config_json )
with open('json_experiment.json') as json_file:
  config_json = json.load(json_file)
pprint(config_json)

#
ticker = "UFPI"
if (ticker not in config_json.keys()):
  print ("json data for ",ticker, "does not exist in",configuration_json, "file")
else :
  if ("Upper_Price_Channel_Adj" in config_json[ticker]):
    len_upper_price_channel_adj = len(config_json[ticker]["Upper_Price_Channel_Adj"])
    print ("The number of Upper channel adjustments specified", len_upper_price_channel_adj)
    upper_price_channel_adj_start_date_list = []
    upper_price_channel_adj_stop_date_list = []
    upper_price_channel_adj_amount_list = []
    for i in range(len_upper_price_channel_adj):
      i_start_date = config_json[ticker]["Upper_Price_Channel_Adj"][i]["Start_Date"]
      i_stop_date = config_json[ticker]["Upper_Price_Channel_Adj"][i]["Stop_Date"]
      i_adj_amount = config_json[ticker]["Upper_Price_Channel_Adj"][i]["Adj_Amount"]
      try:
        upper_price_channel_adj_start_date_list.append(dt.datetime.strptime(i_start_date, "%m/%d/%Y").date())
        upper_price_channel_adj_stop_date_list.append(dt.datetime.strptime(i_stop_date, "%m/%d/%Y").date())
        upper_price_channel_adj_amount_list.append(float(i_adj_amount))
      except (ValueError):
        print("\n***** Error : Either the Start/Stop Dates or the Adjust Amount are not in proper format for Upper_Price_Channel_Adj in Configuration json file.\n"
              "***** Error : The Dates should be in the format %m/%d/%Y and the Adjust Amount should be a int/float\n"
              "***** Error : Found somewhere in :", i_start_date, i_stop_date, i_adj_amount)
        sys.exit(1)
    print ("The Upper Channel Start Date List", upper_price_channel_adj_start_date_list)
    print ("The Upper Channel Stop Date List", upper_price_channel_adj_stop_date_list)
    print ("The Upper Channel Adjust List", upper_price_channel_adj_amount_list)

  if ("Lower_Price_Channel_Adj" in config_json[ticker]):
    len_lower_price_channel_adj = len(config_json[ticker]["Lower_Price_Channel_Adj"])
    print ("The number of Lower channel adjustments specified", len_lower_price_channel_adj)
    lower_price_channel_adj_start_date_list = []
    lower_price_channel_adj_stop_date_list = []
    lower_price_channel_adj_amount_list = []
    for i in range(len_lower_price_channel_adj):
      i_start_date = config_json[ticker]["Lower_Price_Channel_Adj"][i]["Start_Date"]
      i_stop_date = config_json[ticker]["Lower_Price_Channel_Adj"][i]["Stop_Date"]
      i_adj_amount = config_json[ticker]["Lower_Price_Channel_Adj"][i]["Adj_Amount"]
      try:
        lower_price_channel_adj_start_date_list.append(dt.datetime.strptime(i_start_date, "%m/%d/%Y").date())
        lower_price_channel_adj_stop_date_list.append(dt.datetime.strptime(i_stop_date, "%m/%d/%Y").date())
        lower_price_channel_adj_amount_list.append(float(i_adj_amount))
      except (ValueError):
        print("\n***** Error : Either the Start/Stop Dates or the Adjust Amount are not in proper format for Lower_Price_Channel_Adj in Configuration json file.\n"
              "***** Error : The Dates should be in the format %m/%d/%Y and the Adjust Amount should be a int/float\n"
              "***** Error : Found somewhere in :", i_start_date, i_stop_date, i_adj_amount)
        sys.exit(1)
    print ("The Upper Channel Start Date List", lower_price_channel_adj_start_date_list)
    print ("The Upper Channel Stop Date List", lower_price_channel_adj_stop_date_list)
    print ("The Upper Channel Adjust List", lower_price_channel_adj_amount_list)


sys.exit()

# len_maps = len(config_json[ticker]["maps"])
# print (config_json[ticker]["maps"][0]["id"])  # will return 'blabla'
# print(config_json[ticker]["masks"][0]["id"])    # will return 'valore'
# print(config_json[ticker]["om_points"])      # will return 'value'
#
# print ("The length of the array is : ", len_maps)
#
# print("\n========== Now really starting ticker processing ==========\n")
# # if anchored text exist
# if ("Anchored_Text" in config_json[ticker]):
#   # if the length of the keys is > 0
#   if (len(config_json[ticker]["Anchored_Text"].keys()) > 0 ):
#     anchored_text_keys = config_json[ticker]["Anchored_Text"].keys()
#     for i_key in config_json[ticker]["Anchored_Text"].keys():
#       print ("Anchored text key :", i_key, " Value :", config_json[ticker]["Anchored_Text"][i_key])
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
print ("Tickers in json data: ",config_json.keys())
if (ticker not in config_json.keys()):
  print (ticker, "does not exist in json data")
else :
  if ("Splits" in config_json[ticker]):
    # if the length of the keys is > 0
    if (len(config_json[ticker]["Splits"].keys()) > 0 ):
      split_keys = config_json[ticker]["Splits"].keys()
      print ("Split Date list is: ", split_keys)
      for i_key in split_keys:
        print ("Split Date :", i_key, "Split Factor :", config_json[ticker]["Splits"][i_key])
        try:
         split_dates.append(dt.datetime.strptime(str(i_key),"%m/%d/%Y").date())
        except (ValueError):
         print ("\n***** Error : The split Date: ",i_key,"does not seem to be right. Should be in the format %m/%d/%Y...please check *****")
         sys.exit(1)
        try:
          (numerator, denominator) = config_json[ticker]["Splits"][i_key].split(":")
          split_multiplier.append(float(denominator)/float(numerator))
        except (ValueError):
          print ("\n***** Error : The split factor: ",config_json[ticker]["Splits"][i_key],"for split date :", i_key , "does not seem to have right format [x:y]...please check *****")
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

