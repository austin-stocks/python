curr_dir=`pwd`
dir_name='2021_05_27'

echo "The directory name is $dir_name"

echo "Now commiting files in 'Financials - Quarterly'"
cd $curr_dir/$dir_name/'Financials - Quarterly'
git commit -m "Adding Financials Quarterly" *.xlsm --verbose

echo ""
echo "=============================="
echo "Now commiting files in 'Financials - Yearly'"
cd $curr_dir/$dir_name/'Financials - Yearly'
git commit -m "Adding Financials Yearly" *.xlsm --verbose

echo ""
echo "=============================="
echo "Now commiting files in 'Key Statistics'"
cd $curr_dir/$dir_name/'Key Statistics'
git commit -m "Adding Key Statistics" *.xlsm --verbose

echo ""
echo "=============================="
echo "Now commiting files in 'Analysis'"
cd $curr_dir/$dir_name/'Analysis'
git commit -m "Adding Analysis" *.xlsm --verbose




