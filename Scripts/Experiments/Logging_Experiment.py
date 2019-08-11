import logging
import pandas as pd
import sys

# critical, error, warning, info, debug

# set up logging to file - see previous section for more details
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename='Logging_Experiment.txt',
                    filemode='w')
# define a Handler which writes INFO messages or higher to the sys.stderr
console = logging.StreamHandler()
console.setLevel(logging.WARNING)
# set a format which is simpler for console use
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
# tell the handler to use this format
console.setFormatter(formatter)
# add the handler to the root logger
logging.getLogger('').addHandler(console)

# Disnable and enable global level logging 
logging.disable(sys.maxsize)
logging.disable(logging.NOTSET)

# Now, we can log to the root logger, or any other logger. First the root...
tmp_str = "This is tmp string"
tmp_list = [0,1,2,3,4]
tmp_df = pd.DataFrame(index = [0,1,2],columns=['A','B','D'])
tmp_df.A = 0
tmp_df.B = 4
tmp_df.D = "EMPTY"
print ("The dataframe is\n",tmp_df)
print ("The type of the structure is\n",type(tmp_df))

logging.debug("Debug Level")
logging.info('Info Level')
logging.warning('Warning Level')
logging.error('Error Level')
logging.critical('Critical Level')
logging.critical("I am trying to print a string "f'tmp_str')
logging.critical("I am trying to print a list "f'{tmp_list}')
logging.critical("I am trying to print a df\n "f'{tmp_df}')
logging.critical("The type of the structure is\n %s",type(tmp_df))


# Now, define a couple of other loggers which might represent areas in your
# application:
#
# logger1 = logging.getLogger('myapp.area1')
# logger2 = logging.getLogger('myapp.area2')
#
# logger1.debug('Quick zephyrs blow, vexing daft Jim.')
# logger1.info('How quickly daft jumping zebras vex.')
# logger2.warning('Jail zesty vixen who grabbed pay from quack.')
# logger2.error('The five boxing wizards jump quickly.')


'''
AzureAD+SundeepChadha@LaptopOffice-T480 MINGW64 /c/Sundeep/Stocks_Automation/scripts/experiments (master)
$ cat Logging_Experiment.txt
08-11 12:14 root         INFO     Jackdaws love my big sphinx of quartz.
08-11 12:14 myapp.area1  DEBUG    Quick zephyrs blow, vexing daft Jim.
08-11 12:14 myapp.area1  INFO     How quickly daft jumping zebras vex.
08-11 12:14 myapp.area2  WARNING  Jail zesty vixen who grabbed pay from quack.
08-11 12:14 myapp.area2  ERROR    The five boxing wizards jump quickly.
'''
