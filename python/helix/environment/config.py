import ConfigParser
import os, re
from helix.environment.environment import getConfigPath

class ConfigFileHandler(object):
	_instance = None

	# Singleton
	def __new__(cls, *args, **kwargs):
		if not cls._instance:
			cls._instance = super(ConfigFileHandler, cls).__new__(cls, *args, **kwargs)

		return cls._instance

class GeneralConfigHandler(ConfigFileHandler):
	def __init__(self):
		super(GeneralConfigHandler, self).__init__()

		self.config = ConfigParser.ConfigParser(allow_no_value=True)
		self.file = getConfigPath()

		# All options
		self.dateFormat = None
		self.versionPadding = None
		self.framePadding = None
		self.seqShotPadding = None
		self.autoAddUsers = False
		self.makeTempFile = False
		self.permGroups = {}
		self.mayaLinux = None
		self.houdiniLinux = None
		self.nukeLinux = None
		self.mayaWin = None
		self.houdiniWin = None
		self.nukeWin = None
		self.mayaMac = None
		self.houdiniMac = None
		self.nukeMac = None

		if os.path.exists(self.file):
			self.config.read(self.file)
			self.interpret()
		else:
			self.config.add_section('Formatting')
			self.config.set('Formatting', '# The formatting for all date/time values in the system (i.e. when publishing)')
			self.config.set('Formatting', '# Do not change unless you know what you are doing (see http://strftime.org/)')
			self.config.set('Formatting', 'DateFormat', '%m%d%y-%H:%M:%S')
			self.config.set('Formatting', '# Number padding for versions when publishing')
			self.config.set('Formatting', 'VersionPadding', 4)
			self.config.set('Formatting', '# The expected frame padding for image sequences in the system')
			self.config.set('Formatting', 'FramePadding', 4)
			self.config.set('Formatting', '# The number padding for sequence/shot folders')
			self.config.set('Formatting', 'SequenceShotPadding', 4)

			self.config.add_section('Database')
			self.config.set('Database', '# This determines if newly encountered users should automatically be added to the database. If not, they will not be able to do anything in the system without being manually added.')
			self.config.set('Database', 'AutoAddUsers', True)
			self.config.set('Database', '# When True, a temp file will be made locally for database commits. This is necessary to avoid database locks when the DB is hosted on a samba mounted drive (i.e. network share).')
			self.config.set('Database', 'MakeTempFile', False)

			self.config.add_section('Departments')
			self.config.set('Departments', '# The master list of all possible departments users in the system will be a part of. Used for generating reports and being able to assign fixes on a per-department basis.')
			self.config.set('Departments', 'departments', 'animation,layout,editorial,sets,lookdev,lighting,fx,cfx,comp,production,pipeline')

			self.config.add_section('Paths')
			self.config.set('Paths', '# OS specific paths so that Helix assets can work universally')
			self.config.set('Paths', 'HELIX_LINUX_HOME', '/some/path/to/helix/system/root')
			self.config.set('Paths', 'HELIX_WINDOWS_HOME', 'C:\\some\\windows\\path')

			self.config.add_section('Executables-Linux')
			self.config.set('Executables-Linux', '# Defines the locations of Maya, Nuke, and Houdini executables for Linux. The same idea applies for the Executables-Windows and Executables-Mac sections.')
			self.config.set('Executables-Linux', '# If a section is omitted, some Helix features will not be enabled for that particular operating system.')
			self.config.set('Executables-Linux', 'nuke', '/usr/local/bin/nuke')
			self.config.set('Executables-Linux', 'maya','/usr/autodesk/maya2018/bin/maya2018')
			self.config.set('Executables-Linux', 'houdini','/opt/hfs16.5.268/bin/houdini')

			self.config.add_section('Executables-Windows')
			self.config.set('Executables-Windows', '# Windows executables here...')

			self.config.add_section('Executables-Mac')
			self.config.set('Executables-Mac', '# Mac executables here...')

			self.write()
			self.config.read(self.file) # Read in again to strip comments
			self.interpret()

	def interpret(self):
		if self.config.has_section('Formatting'):
			if self.config.has_option('Formatting', 'DateFormat'):
				self.dateFormat = self.config.get('Formatting', 'DateFormat')
			if self.config.has_option('Formatting', 'VersionPadding'):
				self.versionPadding = self.config.getint('Formatting', 'VersionPadding')
			if self.config.has_option('Formatting', 'FramePadding'):
				self.framePadding = self.config.getint('Formatting', 'FramePadding')
			if self.config.has_option('Formatting', 'SequenceShotPadding'):
				self.seqShotPadding = self.config.getint('Formatting', 'SequenceShotPadding')

		if self.config.has_section('Departments'):
			self.departments = [d.strip() for d in self.config.get('Departments', 'departments').split(',')]

		if self.config.has_section('Database'):
			if self.config.has_option('Database', 'AutoAddUsers'):
				self.autoAddUsers = self.config.getboolean('Database', 'AutoAddUsers')
			else:
				self.autoAddUsers = False

			if self.config.has_option('Database', 'MakeTempFile'):
				self.makeTempFile = self.config.getboolean('Database', 'MakeTempFile')
			else:
				self.makeTempFile = False

		if self.config.has_section('Paths'):
			if self.config.has_option('Paths', 'HELIX_LINUX_HOME'):
				os.environ['HELIX_LINUX_HOME'] = self.config.get('Paths', 'HELIX_LINUX_HOME')
			if self.config.has_option('Paths', 'HELIX_WINDOWS_HOME'):
				os.environ['HELIX_WINDOWS_HOME'] = self.config.get('Paths', 'HELIX_WINDOWS_HOME')
			if self.config.has_option('Paths', 'HELIX_MAC_HOME'):
				os.environ['HELIX_MAC_HOME'] = self.config.get('Paths', 'HELIX_MAC_HOME')

		if self.config.has_section('Executables-Linux'):
			if self.config.has_option('Executables-Linux', 'maya'):
				self.mayaLinux = self.config.get('Executables-Linux', 'maya')
			if self.config.has_option('Executables-Linux', 'houdini'):
				self.houdiniLinux = self.config.get('Executables-Linux', 'houdini')
			if self.config.has_option('Executables-Linux', 'nuke'):
				self.nukeLinux = self.config.get('Executables-Linux', 'nuke')

		if self.config.has_section('Executables-Windows'):
			if self.config.has_option('Executables-Windows', 'maya'):
				self.mayaWin = self.config.get('Executables-Windows', 'maya')
			if self.config.has_option('Executables-Windows', 'houdini'):
				self.houdiniWin = self.config.get('Executables-Windows', 'houdini')
			if self.config.has_option('Executables-Windows', 'nuke'):
				self.nukeWin = self.config.get('Executables-Windows', 'nuke')

		if self.config.has_section('Executables-Mac'):
			if self.config.has_option('Executables-Mac', 'maya'):
				self.mayaMac = self.config.get('Executables-Mac', 'maya')
			if self.config.has_option('Executables-Mac', 'houdini'):
				self.houdiniMac = self.config.get('Executables-Mac', 'houdini')
			if self.config.has_option('Executables-Mac', 'nuke'):
				self.nukeMac = self.config.get('Executables-Mac', 'nuke')

	def store(self):
		# Clear everything first
		self.config = ConfigParser.ConfigParser(allow_no_value=True)

		# General config
		self.config.add_section('Formatting')

		self.config.set('Formatting', 'DateFormat', self.dateFormat)
		self.config.set('Formatting', 'VersionPadding', self.versionPadding)
		self.config.set('Formatting', 'FramePadding', self.framePadding)
		self.config.set('Formatting', 'SequenceShotPadding', self.seqShotPadding)

		# Departments
		self.config.add_section('Departments')
		self.config.set('Departments', 'departments', ', '.join(self.departments))

		self.config.add_section('Database')
		self.config.set('Database', 'AutoAddUsers', self.autoAddUsers)
		self.config.set('Database', 'MakeTempFile', self.makeTempFile)

		# Paths
		self.config.add_section('Paths')

		for homePath in ('HELIX_LINUX_HOME', 'HELIX_WINDOWS_HOME', 'HELIX_MAC_HOME'):
			if homePath in os.environ:
				self.config.set('Paths', homePath, os.environ[homePath])

		# Linux executables
		if (self.mayaLinux or self.houdiniLinux or self.nukeLinux):
			self.config.add_section('Executables-Linux')

			if self.mayaLinux:
				self.config.set('Executables-Linux', 'maya', self.mayaLinux)
			else:
				self.config.remove_option('Executables-Linux', 'maya')

			if self.houdiniLinux:
				self.config.set('Executables-Linux', 'houdini', self.houdiniLinux)
			else:
				self.config.remove_option('Executables-Linux', 'houdini')

			if self.nukeLinux:
				self.config.set('Executables-Linux', 'nuke', self.nukeLinux)
			else:
				self.config.remove_option('Executables-Linux', 'nuke')
		else:
			self.config.remove_section('Executables-Linux')

		# Windows executables
		if (self.mayaWin or self.houdiniWin or self.nukeWin):
			self.config.add_section('Executables-Windows')

			if self.mayaWin:
				self.config.set('Executables-Windows', 'maya', self.mayaWin)
			else:
				self.config.remove_option('Executables-Windows', 'maya')

			if self.houdiniWin:
				self.config.set('Executables-Windows', 'houdini', self.houdiniWin)
			else:
				self.config.remove_option('Executables-Windows', 'houdini')

			if self.nukeWin:
				self.config.set('Executables-Windows', 'nuke', self.nukeWin)
			else:
				self.config.remove_option('Executables-Windows', 'nuke')
		else:
			self.config.remove_section('Executables-Windows')

		# Mac executables
		if (self.mayaMac or self.houdiniMac or self.nukeMac):
			self.config.add_section('Executables-Mac')

			if self.mayaMac:
				self.config.set('Executables-Mac', 'maya', self.mayaMac)
			else:
				self.config.remove_option('Executables-Mac', 'maya')

			if self.houdiniMac:
				self.config.set('Executables-Mac', 'houdini', self.houdiniMac)
			else:
				self.config.remove_option('Executables-Mac', 'houdini')

			if self.nukeMac:
				self.config.set('Executables-Mac', 'nuke', self.nukeMac)
			else:
				self.config.remove_option('Executables-Mac', 'nuke')
		else:
			self.config.remove_section('Executables-Mac')

	def write(self):
		with open(self.file, 'w') as configFile:
			self.config.write(configFile)

	def getFile(self):
		return self.file