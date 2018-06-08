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
		# First check negated node, since that would override anything else
		if '^' + node in self.permNodes:
			raise PermissionError('You don\'t have permission to do this')

		if node in self.permNodes:
			return True

		wildcards = self.toWildcard(node)
		negWildcards = ['^' + w for w in wildcards]

		# First check negated wildcard nodes
		for nw in negWildcards:
			if nw in self.permNodes:
				raise PermissionError('You don\'t have permission to do this')

		for w in wildcards:
			if w in self.permNodes:
				return True

		raise PermissionError('You don\'t have permission to do this')

	def toWildcard(self, node):
		permGroups = node.split('.')
		wildcards = []

		for i in range(0, len(permGroups) - 1):
			partial = permGroups[0:i+1] + ['*']

			wildcards.append('.'.join(partial))

		return wildcards

	def group(self):
		return self.group

class PermissionError(HelixException):
	pass