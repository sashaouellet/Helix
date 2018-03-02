import getpass
import helix.environment.environment as env
import re

class PermissionHandler(object):
	def __init__(self):
		self.currentUser = getpass.getuser()
		self.group = None
		self.cmds = []

		cfg = env.getConfig()

		pattern = re.compile(r'^(\w+)(users)$')

		for option in cfg.config.options('Permissions'):
			match = re.match(pattern, option)

			if match and match.group(2):
				if self.currentUser in cfg.config.get('Permissions', option):
					self.group = match.group(1)
					self.cmds = cfg.config.get('Permissions', match.group(1))

		# If not in any group, defaults to group "default"
		if not self.group:
			self.group = 'defaultgroup'
			self.cmds = cfg.config.get('Permissions', 'defaultgroup')

	def canExecute(self, cmd):
		return cmd in self.cmds or '*' in self.cmds

	def group(self):
		return self.group
