import iniparse

# TODO: Need to make it more robust
INIFILE = "../src/wallr.ini"

settings = iniparse.INIConfig(open(INIFILE))
