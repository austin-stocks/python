
from SC_logger import my_print as my_print



debug_fh = open("logfilename.txt", "w+")

log_lvl = "info"
debug_str = "1: This is a wonderful world"
stdout = 0; my_print (debug_fh,debug_str,stdout,log_lvl.upper())

log_lvl = "debug"
debug_str = "2: This is a wonderful world"
stdout = 1; my_print (debug_fh,debug_str,stdout,log_lvl.upper())
