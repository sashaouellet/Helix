import os
import sys
import getpass
import datetime

from helix.api.exceptions import HelixException

VAR_PREFIX = 'HELIX_'
DEBUG = False
HAS_UI = False
USER = getpass.getuser()
LINUX = 'Linux'
WIN = 'Windows'
MAC = 'Mac'
OS = LINUX

if sys.platform == 'win32':
	OS = WIN
elif sys.platform == 'darwin':
	OS = MAC

def setEnvironment(var, value):
	os.environ[VAR_PREFIX + var.upper()] = value

def getEnvironment(var):
	env = os.environ.get(VAR_PREFIX + var.upper())

	if not env:
		raise EnvironmentError('Variable {} not set'.format(var))

	return env

def getConfigPath():
	return os.path.join(getEnvironment('home'), 'config.ini')

def getAllEnv():
	ret = {}

	for key, val in os.environ.iteritems():
		if key.startswith(VAR_PREFIX):
			ret[key] = val

	return ret

def getShow():
	show = getEnvironment('show')

	if show:
		from helix.database.show import Show
		return Show.fromPk(show)

def getWorkingElement():
	element = getEnvironment('element')

	if element:
		from helix.database.element import Element
		return Element.fromPk(element)

def getDept():
	from helix.database.person import Person
	person = Person.fromPk(USER)

	if person is not None:
		return person.department

	return None

def getCreationInfo(format=True):
	dt = datetime.datetime.now()

	if format:
		dt = dt.strftime(DATE_FORMAT)

	return (USER, dt)

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
