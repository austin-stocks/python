echo "Cleaning up the backup files that are appreantly created by MyCloud backup"

rm -f *-2020-07-*.csv
rm -f historical/*-2020-07-*.csv
rm -f Dividend/*-2020-07-*.csv
rm -f Earnings/*-2020-07-*.csv
rm -f User_Files/*-2020-07-*.csv

rm -f Charts/Linear/Charts_With_Numbers/*-2020-07-*.jpg
rm -f Charts/Long_Linear/Charts_With_Numbers/*-2020-07-*.jpg
rm -f Charts/Log/Charts_With_Numbers/*-2020-07-*.jpg

rm -f Charts/Linear/Charts_Without_Numbers/*-2020-07-*.jpg
rm -f Charts/Long_Linear/Charts_Without_Numbers/*-2020-07-*.jpg
rm -f Charts/Log/Charts_Without_Numbers/*-2020-07-*.jpg

rm -f Latest_Charts/Linear/Charts_With_Numbers/*-2020-07-*.jpg
rm -f Latest_Charts/Long_Linear/Charts_With_Numbers/*-2020-07-*.jpg
rm -f Latest_Charts/Log/Charts_With_Numbers/*-2020-07-*.jpg

rm -f Latest_Charts/Linear/Charts_Without_Numbers/*-2020-07-*.jpg
rm -f Latest_Charts/Long_Linear/Charts_Without_Numbers/*-2020-07-*.jpg
rm -f Latest_Charts/Log/Charts_Without_Numbers/*-2020-07-*.jpg
