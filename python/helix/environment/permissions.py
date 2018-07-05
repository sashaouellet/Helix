import getpass
import re
from helix.api.exceptions import *

class PermissionNodes(object):
	"""An "enum" for all the permission nodes for the system
	"""
	nodes = dict(
		CREATE_SHOW = 'helix.create.show',
		CREATE_SEQ = 'helix.create.sequence',
		CREATE_SHOT = 'helix.create.shot',
		CREATE_ELEMENT = 'helix.create.element',
		DELETE_SHOW = 'helix.delete.show',
		DELETE_SEQ = 'helix.delete.sequence',
		DELETE_SHOT = 'helix.delete.shot',
		DELETE_ELEMENT = 'helix.delete.element',
		POP = 'helix.pop',
		GET = 'helix.get',
		PUBLISH = 'helix.publish',
		ROLLBACK = 'helix.rollback',
		MOD_SET = 'helix.mod.set',
		MOD_GET = 'helix.mod.get',
		IMPORT_ELEMENT = 'helix.import.element',
		CLONE = 'helix.clone',
		OVERRIDE = 'helix.override',
		GET_WORKFILE = 'helix.workfile.get',
		CREATE_WORKFILE = 'helix.workfile.create',
		VIEW_SHOWS = 'helix.view.show',
		VIEW_SEQS = 'helix.view.sequence',
		VIEW_SHOTS = 'helix.view.shot',
		VIEW_ELEMENTS = 'helix.view.element',
		DUMP_DB = 'helix.dump',
		GET_ENV = 'helix.getenv'
	)

	@staticmethod
	def expandedNodeList(nodes=[]):
		if not nodes:
			nodes = PermissionNodes.nodes.values()

		ret = nodes[:]

		for node in nodes:
			permGroups = node.split('.')

			for i in range(0, len(permGroups) - 1):
				partial = permGroups[0:i+1] + ['*']

				ret.append('.'.join(partial))
				ret.append('^' + '.'.join(partial))

		return list(set(ret))

class PermissionGroup(object):
	def __init__(self, name, users=[], permissions=[]):
		self.name = name
		self.users = users
		self.permissions = permissions

	def __repr__(self):
		return '[{}]: {} -- {}'.format(self.name, ', '.join(self.users if self.users else []), ', '.join(self.permissions if self.permissions else []))

class PermissionHandler(object):
	def __init__(self):
		import helix.environment.environment as env

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