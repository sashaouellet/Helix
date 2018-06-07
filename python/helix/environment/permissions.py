import getpass
import helix.environment.environment as env
import re
from helix.database.database import HelixException

class PermissionHandler(object):
	def __init__(self):
		self.currentUser = getpass.getuser()
		self.group = None
		self.permNodes = []

		cfg = env.getConfig()

		pattern = re.compile(r'^(\w+)(users)$')

		for option in cfg.config.options('Permissions'):
			match = re.match(pattern, option)

			if match and match.group(2):
				if self.currentUser in cfg.config.get('Permissions', option):
					self.group = match.group(1)
					self.permNodes = cfg.config.get('Permissions', match.group(1))

		# If not in any group, defaults to group "default"
		if not self.group:
			self.group = 'defaultgroup'
			self.permNodes = cfg.config.get('Permissions', 'defaultgroup')

	def check(self, node):
		if node in self.permNodes:
			return True

		permGroups = node.split('.')

		for i in range(0, len(permGroups) - 1):
			wildCard = permGroups[0:i+1] + ['*']

			if '.'.join(wildCard) in self.permNodes:
				return True

		raise PermissionError('You don\'t have permission to do this')

	def group(self):
		return self.group

class PermissionError(HelixException):
	pass