This is a file that talks about what various scripts do:

x. \...\Scripts\SC_YahooHistorical_Download.py
	This scripts downlads the Historical data from Yahoo. The data is downloaded in the directory 
	\...\Download\YahooHistorical
	Once the historical data is downloaded then the YahooHistorical_Merge script can run...

x. \...\Scripts\SC_YahooDividend_Download.py
	This scripts downlads the Dividend data from Yahoo. The data is downloaded in the directory 
	\...\Dividend


x. \...\Scripts\SC_YahooHistorical_Merge.py
	This script takes the Yahoo Historical data downloaded by SC_YahooHistorical_Download.py from 
	above and reads in the stock market calendar (the days when the stock market is open till 2024)
	dates from the direcotry 
	\...\User_Files\Calendar.csv 
	and Configurations file from the directory 
	\...\User_Files\Calendar.csv
	and see what the user has specified for the ticker and then puts those stock market date 
	on the top of the historical data and creates the ticker specific file in the direcotry
	\...\Historical

	Running of SC_YahooHistorical_Download and SC_YahooHistorical_Merge (serially) and 
	SC_YahooDividend_Download gets us all the historical and dividend data that is needed
	to prepare the chart (Earnings data is also needed but that is in the ticker_earnings.csv
	file)

x. \...\Scripts\SC_EarningsChart.py
	This script takes in the Historical, dividend data prepared above and takes the earnings data
	from the 
	\...\Earnings 
	directory and prepares the chart. There are various other files that is script references...
	more to come. 
	

8. \...\Scripts\SC_CopyLastest_Charts.py

10. \...\Scripts\SC_Extract_Earnings.py

3. \...\Scripts\SC_SpotCheck_Earning_Files.py

5. \...\Scripts\SC_YahooEarningsCalendar.py


1. \...\Scripts\SC_logger.py -- Not used anymore. Move to backup/old

2. \...\Scripts\SC_Parse_MasterTracklist.py -- It is covered by otherscripts. Move to backup/old 


Talk about the macros in AAMC_Macros file as well



