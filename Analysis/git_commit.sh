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


for chrs in $alphabets 
do 
  echo "Adding the files that start with [$chrs]*"
  if [ $chrs = "A" ]
  then
    echo "Doing $chrs...Will loop through subloop"
    for chrs_subloop in $alphabets_subloop
    do
      echo "Adding the files that start with ==> [$chrs][$chrs_subloop]"
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




for chrs in $alphabets 
do 
  echo ""
  echo "Commiting the files that start with [$chrs]*"
  echo ""
  sleep 2
  if [ $chrs = "A" ]
  then
    echo "Doing $chrs...Will loop through subloop"
    for chrs_subloop in $alphabets_subloop
    do
      echo "Committing the files that start with ==> [$chrs][$chrs_subloop]"
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

