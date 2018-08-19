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

def getEnvironment(var, silent=False):
	if var.upper() == 'HOME':
		var = '{}_HOME'.format(OS)

	env = os.environ.get(VAR_PREFIX + var.upper())

	if not env and not silent:
		raise EnvironmentError('Variable {} not set'.format(var))

	return env

def getConfigPath():
	return getEnvironment('config')

def getDBPath():
	return os.path.join(os.path.dirname(getConfigPath()), 'helix.db')

def getAllEnv():
	ret = {}

	for key, val in os.environ.iteritems():
		if key.startswith(VAR_PREFIX):
			ret[key] = val

	return ret

def getShow():
	show = getEnvironment('show', silent=True)

	if show:
		from helix import Show
		return Show.fromPk(show)

def getSequence():
	seq = getEnvironment('sequence', silent=True)

	if seq:
		from helix import Sequence
		return Sequence.fromPk(seq)

def getShot():
	shot = getEnvironment('shot', silent=True)

	if shot:
		from helix import Shot
		return Shot.fromPk(shot)

def getWorkingElement():
	element = getEnvironment('element', silent=True)

	if element:
		from helix import Element
		return Element.fromPk(element)

def setWorkingElement(element):
	setEnvironment('element', element.id)
	setEnvironment('show', element.show)
	setEnvironment('sequence', element.sequenceId)
	setEnvironment('shot', element.shotId)

def getDept():
	from helix import Person
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

def convertPath(path):
	homePaths = ('HELIX_LINUX_HOME', 'HELIX_WINDOWS_HOME', 'HELIX_MAC_HOME')
	for homePath in homePaths:
		if homePath in os.environ:
			val = os.environ[homePath]

			if path.startswith(val):
				return path.replace(val, getEnvironment('home'))

	raise ValueError('Unknown location for path: {}. Currently configured paths are: {}'.format(
			path,
			', '.join([os.environ[h] for h in homePaths if h in os.environ])
		)
	)

cfg = getConfig()

DATE_FORMAT = cfg.config.get('Formatting', 'dateformat')
VERSION_PADDING = cfg.config.getint('Formatting', 'versionpadding')
FRAME_PADDING = cfg.config.getint('Formatting', 'framepadding')
SEQUENCE_SHOT_PADDING = cfg.config.getint('Formatting', 'sequenceshotpadding')

setEnvironment('db', getDBPath())
setEnvironment('work', os.path.join(getEnvironment('home'), 'work'))
setEnvironment('release', os.path.join(getEnvironment('home'), 'release'))

show = None
element = None