echo ""
echo "Showing the current status"
git status
sleep 2
echo ""
echo ""
echo "=====> Now starting the add process <====="
echo ""

alphabets='A B C D E F G H I J K L M N O P Q R S T U V W X Y Z'


for chrs in $alphabets 
do 
  echo "Adding the files that start with [$chrs]*"
  git add Quarterly/[$chrs]*.csv
  git add Yearly/[$chrs]*.csv 
  git add Key_Statistics/[$chrs]*.csv
done




for chrs in $alphabets 
do 
  echo ""
  echo "Commiting the files that start with [$chrs]*"
  echo ""
  sleep 2
  git commit -m "More Updates"  Quarterly/[$chrs]*.csv -v 
  git commit -m "More Updates"  Yearly/[$chrs]*.csv -v 
  git commit -m "More Updates"  Key_Statistics/[$chrs]*.csv -v 
done

