import os

VAR_PREFIX = 'HELIX_'
DATE_FORMAT = '%m%d%y-%H:%M:%S' # TODO: pull from config
VERSION_PADDING = 4 # TODO: pull from config
FRAME_PADDING = 4 # TODO: pull from config

show = None
element = None

def setEnvironment(var, value):
	os.environ[VAR_PREFIX + var.upper()] = value

def getEnvironment(var):
	return os.environ.get(VAR_PREFIX + var.upper())

def getAllEnv():
	ret = {}

	for key, val in os.environ.iteritems():
		if key.startswith(VAR_PREFIX):
			ret[key] = val

	return ret

def getCreationInfo():
	import getpass, datetime

	return (getpass.getuser(), datetime.datetime.now().strftime(DATE_FORMAT))
