import iniparse

# TODO: Need to make it more robust
INIFILE = "../src/wallr.ini"

settings = iniparse.INIConfig(open(INIFILE))

def save():
    f = open(INIFILE, 'w')
    print >>f, settings
    f.close()
