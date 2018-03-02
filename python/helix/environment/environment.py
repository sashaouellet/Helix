import os
from helix.environment.config import GeneralConfigHandler

VAR_PREFIX = 'HELIX_'

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

def getConfig():
	configPath = getEnvironment('config')
	exists = False

	if not configPath:
		print 'HELIX_CONFIG environment variable not set, defaulting configuration'

		configPath = os.path.join(getEnvironment('home'), 'config.ini')

	exists = os.path.exists(configPath)

	return GeneralConfigHandler(*os.path.split(configPath), existingConfig=exists)

cfg = getConfig()

DATE_FORMAT = cfg.config.get('Formatting', 'dateformat')
VERSION_PADDING = cfg.config.getint('Formatting', 'versionpadding')
FRAME_PADDING = cfg.config.getint('Formatting', 'framepadding')

show = None
element = None
