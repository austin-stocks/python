echo "Adding Yearly xlsx"

alphabets='A B C D E F G H I J K L M N O P Q R S T U V W X Y Z'

for chrs in $alphabets
do
  echo "Adding the Yearly files that start with ==> [$chrs]*"
  git add Yearly/[$chrs]*.xlsx -v
  echo "Adding Quarterly files that start with ==> [$chrs]*"
  git add Quarterly/[$chrs]*.xlsx -v
done

for chrs in $alphabets
do
  echo "Commiting the Yearly files that start with ==> [$chrs]*"
  git commit -m "Updating" Yearly/[$chrs]*.xlsx -v
  echo "Adding Quarterly files that start with ==> [$chrs]*"
  git commit -m "Updating" Quarterly/[$chrs]*.xlsx -v
done

