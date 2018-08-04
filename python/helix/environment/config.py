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

			self.config.add_section('Departments')
			self.config.set('Departments', '# The master list of all possible departments users in the system will be a part of. Used for generating reports and being able to assign fixes on a per-department basis.')
			self.config.set('Departments', 'departments', 'animation,layout,editorial,sets,lookdev,lighting,fx,cfx,comp,production,pipeline')

			self.config.add_section('Permissions')
			self.config.set('Permissions', '# Define any number of user groups, the permission "nodes" for the group, and a list of members of that group')
			self.config.set('Permissions', '# The following permission node list indicates that users in ExampleGroup can do all helix commands (helix.*) except children of the helix.delete permission nodes. The "^" indicates NOT, while "*" indicates all children under.')
			self.config.set('Permissions', 'ExampleGroup', 'helix.*, ^helix.delete.*')
			self.config.set('Permissions', 'ExampleGroupUsers', 'souell20')
			self.config.set('Permissions', '# Make sure to always define something for "DefaultGroup" so that there is a fallback for new users')
			self.config.set('Permissions', 'DefaultGroup', 'helix.pop')

			self.config.add_section('Executables-Linux')
			self.config.set('Executables-Linux', '# Defines the locations of Maya, Nuke, and Houdini executables for Linux. The same idea applies for the Executables-Windows and Executables-Mac sections.')
			self.config.set('Executables-Linux', '# If a section is omitted, some Helix features will not be enabled for that particular operating system.')
			self.config.set('Executables-Linux', 'maya', '/usr/local/bin/nuke')
			self.config.set('Executables-Linux', 'houdini','/usr/autodesk/maya2018/bin/maya2018')
			self.config.set('Executables-Linux', 'nuke','/opt/hfs16.5.268/bin/houdini')

			self.config.add_section('Executables-Windows')
			self.config.set('Executables-Windows', '# Windows executables here...')

			self.config.add_section('Executables-Mac')
			self.config.set('Executables-Mac', '# Mac executables here...')

			self.write()
			self.config.read(self.file) # Read in again to strip comments
			self.interpret()

	def interpret(self):
		from helix.environment.permissions import PermissionGroup

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

		if self.config.has_section('Permissions'):
			pattern = re.compile(r'^(\w+)(users)$')

			for option in self.config.options('Permissions'):
				match = re.match(pattern, option)

				if match and match.group(2):
					groupUsers = [g.strip() for g in self.config.get('Permissions', option).split(',')]
					groupName = match.group(1)
					groupPerms = [p.strip() for p in self.config.get('Permissions', match.group(1)).split(',')]

					self.permGroups[groupName] = PermissionGroup(groupName, users=groupUsers, permissions=groupPerms)

			if self.config.has_option('Permissions', 'DefaultGroup'):
				perms = [p.strip() for p in self.config.get('Permissions', 'DefaultGroup').split(',')]
				self.permGroups['defaultgroup'] = PermissionGroup('defaultgroup', users=None, permissions=perms)
			else:
				print 'Had to create DefaultGroup permissions since it was missing from the config file. Please note that ALL users will now be able to do ANYTHING, so modify the config accordingly!'
				self.permGroups['defaultgroup'] = PermissionGroup('defaultgroup', users=None, permissions=['helix.*'])

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

		# Permissions
		self.config.add_section('Permissions')

		for pg in self.permGroups.values():
			self.config.set('Permissions', pg.name, ', '.join(pg.permissions))

			if pg.name != 'defaultgroup':
				self.config.set('Permissions', pg.name + 'users', ', '.join(pg.users))

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