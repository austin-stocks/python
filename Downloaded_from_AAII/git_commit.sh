curr_dir=`pwd`
dir_name='2023_09_01'

echo "The directory name : $dir_name"
aaii_datafilename="${dir_name}_AAII_DATA.xlsm"
echo "AAII Datafile name : $aaii_datafilename"
sleep 2

echo "Now commiting files in 'Financials - Quarterly'"
cd $curr_dir/$dir_name/'Financials - Quarterly'
git add *.xlsm --verbose
git commit -m "Adding Financials Quarterly" *.xlsm --verbose


echo ""
echo "=============================="
echo "Now commiting files in 'Financials - Yearly'"
cd $curr_dir/$dir_name/'Financials - Yearly'
git add *.xlsm --verbose
git commit -m "Adding Financials Yearly" *.xlsm --verbose

echo ""
echo "=============================="
echo "Now commiting files in 'Key Statistics'"
cd $curr_dir/$dir_name/'Key Statistics'
git add *.xlsm --verbose
git commit -m "Adding Key Statistics" *.xlsm --verbose

echo ""
echo "=============================="
echo "Now commiting files in 'Analysis'"
cd $curr_dir/$dir_name/'Analysis'
git add *.xlsm --verbose
git commit -m "Adding Analysis" *.xlsm --verbose

git add $curr_dir/$dir_name/$aaii_datafilename
git commit -m "Adding AAII Datafile" $curr_dir/$dir_name/$aaii_datafilename


