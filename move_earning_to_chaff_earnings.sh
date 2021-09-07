files='HWKN'

echo ""
sleep 2
echo "Now going through the loop to move the files"
echo ""
for ticker in $files
do

  filename="$ticker"_earnings.csv
  echo "Moving $filename"
  mv Earnings/$filename Chaff_earnings/$filename

  ## ------------------------------------------------------
  ## Now prepare the various string that will be used to pass to git
  ## ------------------------------------------------------
  tmp_str_0="$tmp_str_0 "Chaff_earnings/$filename
  tmp_str_2="$tmp_str_2 "Chaff_earnings/$filename
  tmp_str_2="$tmp_str_2 "Earnings/$filename
  echo "The string to git add is..."
  echo $tmp_str_0
  echo "The string to git commit is..."
  echo $tmp_str_2
  echo ""
  ## ------------------------------------------------------

done


echo "Now will start to git add and git commit"
sleep 2
git status
sleep 5
echo "Now git adding the moved earnings files to Chaff_earnings"
git add $tmp_str_0
sleep 2
## git status
echo "Now git commiting the moved earnings files to Chaff_earnings and deleted earnings files from Earnings"
git commit -m "More updates" $tmp_str_2
echo ""
echo "All done..."


