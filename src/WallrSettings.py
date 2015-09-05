import iniparse

# TODO: Need to make it more robust
INIFILE = "../src/wallr.ini"

settings = iniparse.INIConfig(open(INIFILE))

def save():
    f = open(INIFILE, 'w')
    print >>f, settings
    f.close()

def get_section(name):
    s = settings[name]
    if isinstance(s, iniparse.config.Undefined):
        return None
    else:
        return s
