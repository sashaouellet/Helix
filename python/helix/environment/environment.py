import os

VAR_PREFIX = 'HELIX_'

def setEnvironment(var, value):
	os.environ[VAR_PREFIX + var.upper()] = value

def getEnvironment(var):
	env = os.environ.get(VAR_PREFIX + var.upper())

	if not env:
		raise EnvironmentError('Variable {} not set'.format(env))

	return env

def EnvironmentError(HelixException):
	pass

def getConfigPath():
	return os.path.join(getEnvironment('home'), 'config.ini')

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
	from helix.environment.config import GeneralConfigHandler
	return GeneralConfigHandler()

cfg = getConfig()

DATE_FORMAT = cfg.config.get('Formatting', 'dateformat')
VERSION_PADDING = cfg.config.getint('Formatting', 'versionpadding')
FRAME_PADDING = cfg.config.getint('Formatting', 'framepadding')
SEQUENCE_SHOT_PADDING = cfg.config.getint('Formatting', 'sequenceshotpadding')

show = None
element = None
