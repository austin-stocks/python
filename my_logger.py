
import logging


# =============================================================================
def my_print (debug_fh, msg, stdout,lvl):

  if (stdout == 1):
    print (msg+"\n")

  debug_fh.write (msg+"\n")


# =============================================================================

debug_fh = open("logfilename.txt", "w+")
lvl = "info"


debug_str = "1: This is a wonderful world"
stdout = 0; my_print (debug_fh,debug_str,stdout,lvl)

debug_str = "2: This is a wonderful world"
stdout = 1; my_print (debug_fh,debug_str,stdout,lvl)
