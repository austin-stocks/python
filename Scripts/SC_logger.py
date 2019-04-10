# =============================================================================
def my_print(debug_fh, msg, stdout, lvl):

  # Info - Generally useful information to log (service start/stop, configuration
  #         assumptions, etc). Info I want to always have available but usually
  #         don't care about under normal circumstances. This is my out-of-the-box config level.

  # Debug - Information that is diagnostically helpful to people more than just
  #         developers (IT, sysadmins, etc.).
  # Warn - Anything that can potentially cause application oddities, but for which
  #         I am automatically recovering. (Such as switching from a primary to
  #         backup server, retrying an operation, missing secondary data, etc.)
  # Error - Any error which is fatal to the operation, but not the service or
  #         application (can't open a required file, missing data, etc.). These
  #         errors will force user (administrator, or direct user) intervention.
  #         These are usually reserved (in my apps) for incorrect connection
  #         strings, missing services, etc.

  # Sundeep will end up only using debug, warn and error...the calling code can
  # have info - but that will not print anywhere for now...

  if ((stdout == 1) and (lvl == 'DEBUG')) or ((lvl == 'ERROR') or (lvl == 'WARN')):
    print(msg + "\n")

  if (lvl == 'DEBUG') or (lvl == 'ERROR') or (lvl == 'WARN'):
    debug_fh.write(msg + "\n")

# =============================================================================
#
#
