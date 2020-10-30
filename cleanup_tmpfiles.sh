echo "Cleaning up the backup files that are appreantly created by MyCloud backup"


my_dates='-2020-09-  -2020-10- -2020-11-'

for tmp_date in $my_dates
do
  echo "Removing files that have $tmp_date string"

   rm -f AAII_Financials/Quarterly/*$tmp_date*.xlsx
   rm -f AAII_Financials/Yearly/*$tmp_date*.xlsx
 
   rm -f Analysis/Quarterly/*$tmp_date*.csv
   rm -f Analysis/Yearly/*$tmp_date*.csv
   rm -f Analysis/Key_statistics/*$tmp_date*.csv
 
   rm -f Analysis_Plots/*$tmp_date*.jpg
   rm -f Analysis_Watchlist/Wheat/*$tmp_date*.jpg
   rm -f Analysis_Watchlist/Not_Wheat/*$tmp_date*.jpg
 
 
   rm -f Charts/Linear/Charts_With_Numbers/*$tmp_date*.jpg
   rm -f Charts/Long_Linear/Charts_With_Numbers/*$tmp_date*.jpg
   rm -f Charts/Log/Charts_With_Numbers/*$tmp_date*.jpg
 
   rm -f Charts/Linear/Charts_Without_Numbers/*$tmp_date*.jpg
   rm -f Charts/Long_Linear/Charts_Without_Numbers/*$tmp_date*.jpg
   rm -f Charts/Log/Charts_Without_Numbers/*$tmp_date*.jpg
 
   rm -f Dividend/*$tmp_date*.csv
 
   rm -f Download/YahooHistorical/*$tmp_date*.csv
 
   rm -f Downloaded_from_AAII/*/Analysis/*$tmp_date*.xlsm
   rm -f Downloaded_from_AAII/*/"Financials - Quarterly"/*$tmp_date*.xlsm
   rm -f Downloaded_from_AAII/*/"Financials - Yearly"/*$tmp_date*.xlsm
   rm -f Downloaded_from_AAII/*/"Key Statistics"/*$tmp_date*.xlsm
 
   rm -f Earnings/*$tmp_date*.csv
 
   rm -f historical/*$tmp_date*.csv
 
   rm -f Latest_Charts/Linear/Charts_With_Numbers/*$tmp_date*.jpg
   rm -f Latest_Charts/Long_Linear/Charts_With_Numbers/*$tmp_date*.jpg
   rm -f Latest_Charts/Log/Charts_With_Numbers/*$tmp_date*.jpg
 
   rm -f Latest_Charts/Linear/Charts_Without_Numbers/*$tmp_date*.jpg
   rm -f Latest_Charts/Long_Linear/Charts_Without_Numbers/*$tmp_date*.jpg
   rm -f Latest_Charts/Log/Charts_Without_Numbers/*$tmp_date*.jpg
 
   rm -f Logs/*$tmp_date*.csv
   rm -f Logs/*$tmp_date*.txt
 
   rm -f Readme/*$tmp_date*.csv
   rm -f Readme/*$tmp_date*.txt
 
   rm -f User_Files/*$tmp_date*.csv
   rm -f User_Files/*$tmp_date*.txt
 
 done
 
 