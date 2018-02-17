import ConfigParser
import os

class ConfigFileHandler(object):
	def __init__(self, dir, fileName, existingConfig=False):
		self.dir = dir
		self.fileName = fileName

class GeneralConfigHandler(ConfigFileHandler):
	def __init__(self, dir, fileName, existingConfig=False):
		super(GeneralConfigHandler, self).__init__(dir, fileName, existingConfig=False)

		self.config = ConfigParser.ConfigParser(allow_no_value=True)

		if existingConfig:
			self.config.read(os.path.join(dir, fileName))
		else:
			self.config.add_section('Formatting')
			self.config.set('Formatting', '# The formatting for all date/time values in the system (i.e. when publishing)')
			self.config.set('Formatting', '# Do not change unless you know what you are doing (see http://strftime.org/)')
			self.config.set('Formatting', 'DateFormat', '%m%d%y-%H:%M:%S')
			self.config.set('Formatting', '# Number padding for versions when publishing')
			self.config.set('Formatting', 'VersionPadding', 4)
			self.config.set('Formatting', '# The expected frame padding for image sequences in the system')
			self.config.set('Formatting', 'FramePadding', 4)

			self.config.add_section('Permissions')
			self.config.set('Permissions', '# Define any number of user groups, the commands that group can perform, and a list of members of that group')
			self.config.set('Permissions', 'ExampleGroup', ['pop', 'mke', 'get', 'pub', 'mod'])
			self.config.set('Permissions', 'ExampleGroupUsers', ['souell20'])
			self.config.set('Permissions', '# Make sure to always define something for "DefaultGroup" so that there is a fallback for new users')
			self.config.set('Permissions', 'DefaultGroup', ['pop'])

			self.write()
			self.config.read(os.path.join(dir, fileName)) # Read in again to strip comments

	def write(self):
		with open(os.path.join(self.dir, self.fileName), 'w') as configFile:
			self.config.write(configFile)

if __name__ == '__main__':
	import environment as env
	config = GeneralConfigHandler(os.path.dirname(env.getEnvironment('work')), 'config.ini')

	print config.config.get('Formatting', 'framepadding')