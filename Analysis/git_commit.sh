echo ""
echo "Showing the current status"
git status
sleep 2
echo ""
echo ""
echo "=====> Now starting the add process <====="
echo ""

alphabets='A B C D E F G H I J K L M N O P Q R S T U V W X Y Z'
alphabets_subloop='A B C D E F G H I J K L M N O P Q R S T U V W X Y Z'

aaii_datafilename="${dir_name}_AAII_DATA.xlsm"


# ---------------------------------------------------------
# First do the git add
# ---------------------------------------------------------
for chrs in $alphabets 
do 
  echo "Adding the files that start with ==> [$chrs]*"
  if [ $chrs = "A" ] || [ $chrs = "C" ] || [ $chrs = "S" ]  
  then
    echo "Doing $chrs...Will loop through subloop"
	  # This is to add if the ticker is JUST == A or == C
	  tmp_filename="${chrs}_qtr_data.csv"
    git  add Quarterly/$tmp_filename -v
	  tmp_filename="${chrs}_yr_data.csv"
    git  add Yearly/$tmp_filename -v
	  tmp_filename="${chrs}_key_statistics_data.csv"
    git  add Key_Statistics/$tmp_filename -v 	
    for chrs_subloop in $alphabets_subloop
    do
      echo ""
      echo "Adding the files that start with ==> [$chrs][$chrs_subloop]"
      echo ""
      git  add Quarterly/[$chrs][$chrs_subloop]*csv -v
      git  add Yearly/[$chrs][$chrs_subloop]*csv -v
      git  add Key_Statistics/[$chrs][$chrs_subloop]*csv -v
    done
  else
    git add Quarterly/[$chrs]*.csv
    git add Yearly/[$chrs]*.csv 
    git add Key_Statistics/[$chrs]*.csv
  fi 
done
# ---------------------------------------------------------


# ---------------------------------------------------------
# Now do the commit
# ---------------------------------------------------------
for chrs in $alphabets 
do 
  echo ""
  echo "Commiting the files that start with ==> [$chrs]*"
  echo ""
  ## sleep 2
  if [ $chrs = "A" ] || [ $chrs = "C" ] || [ $chrs = "S" ]  
  then
    echo "Doing $chrs...Will loop through subloop"
	  # This is to add if the ticker is JUST == A or == C
	  tmp_filename="${chrs}_qtr_data.csv"
    git  commit -m "More Updates" Quarterly/$tmp_filename -v
	  tmp_filename="${chrs}_yr_data.csv"
    git  commit -m "More Updates" Yearly/$tmp_filename -v
	  tmp_filename="${chrs}_key_statistics_data.csv"
    git  commit -m "More Updates" Key_Statistics/$tmp_filename -v 	
    for chrs_subloop in $alphabets_subloop
    do
      echo ""
      echo "Committing the files that start with ==> [$chrs][$chrs_subloop]"
      echo ""
      git commit -m "More Updates" Quarterly/[$chrs][$chrs_subloop]*csv -v
      git commit -m "More Updates" Yearly/[$chrs][$chrs_subloop]*csv -v
      git commit -m "More Updates" Key_Statistics/[$chrs][$chrs_subloop]*csv -v
    done
  else
    git commit -m "More Updates"  Quarterly/[$chrs]*.csv -v 
    git commit -m "More Updates"  Yearly/[$chrs]*.csv -v 
    git commit -m "More Updates"  Key_Statistics/[$chrs]*.csv -v 
  fi 
done
# ---------------------------------------------------------

