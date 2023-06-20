filename=Logs/earnings_last_reported.txt
i=1
for line in `cat $filename` 
do
  #echo "This is the value : $line"
  let j=$((i % 3))
  # echo "Iteration number : $i, Internal var, j = $j"
  if [[ $j -eq 1 ]]
  then 
    echo ""
    ticker=${line[0]}
    # echo "Ticker is : $ticker"
    grep -i "^$ticker " Logs/earnings_last_reported.txt
    grep -i "^$ticker," Logs/yahoo_earnings_calendar_2021_02_15.csv
  fi 

  
  let i=$i+1
done

