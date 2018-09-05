import getpass
import re
from helix.api.exceptions import *
from helix import DatabaseObject

class PermissionNodes(object):
	"""An "enum" for all the permission nodes for the system
	"""
	nodes = dict(
		CREATE_SHOW 	= 'helix.create.show',
		CREATE_SEQ 		= 'helix.create.sequence',
		CREATE_SHOT 	= 'helix.create.shot',
		CREATE_ELEMENT 	= 'helix.create.element',
		CREATE_SNAPSHOT	= 'helix.create.snapshot',
		DELETE_SHOW 	= 'helix.delete.show',
		DELETE_SEQ 		= 'helix.delete.sequence',
		DELETE_SHOT 	= 'helix.delete.shot',
		DELETE_ELEMENT 	= 'helix.delete.element',
		POP 			= 'helix.pop',
		GET 			= 'helix.get',
		PUBLISH 		= 'helix.publish',
		ROLLBACK 		= 'helix.rollback',
		MOD_SET			= 'helix.mod.set',
		MOD_GET			= 'helix.mod.get',
		IMPORT_ELEMENT 	= 'helix.import.element',
		EXPORT_ELEMENT	= 'helix.export.element',
		CLONE 			= 'helix.clone',
		VIEW_SHOWS 		= 'helix.view.show',
		VIEW_SEQS 		= 'helix.view.sequence',
		VIEW_SHOTS 		= 'helix.view.shot',
		VIEW_ELEMENTS 	= 'helix.view.element',
		GET_ENV 		= 'helix.getenv',
		VIEW_CONFIG 	= 'helix.config.view',
		EDIT_CONFIG 	= 'helix.config.edit'
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

class PermissionGroup(DatabaseObject):
	DEFAULT = 'defaultgroup'
	TABLE = 'permissions'
	PK = 'group_name'

	def __init__(self, name, permissions=[], dummy=False):
		self.table = PermissionGroup.TABLE
		self._exists = None

		if dummy:
			return

		if not name:
			raise ValueError('Permission group name cannot be empty')

		self.group_name = name

		fetched = self.exists(fetch=True)

		if fetched:
			self.unmap(fetched)
			self._exists = True
		else:
			self._exists = False
			self.group_name = name
			self.permissionList = permissions

	@property
	def perm_nodes(self):
		return str(self.permissionList).replace("'", '"')

	@perm_nodes.setter
	def perm_nodes(self, perm_nodes):
		try:
			if perm_nodes:
				self.permissionList = eval(perm_nodes)
			else:
				self.permissionList = []
		except:
			self.permissionList = []

	@property
	def pk(self):
		return PermissionGroup.PK

	@staticmethod
	def dummy():
		return PermissionGroup(None, dummy=True)

class PermissionHandler(object):
	def __init__(self):
		import helix.environment.environment as env

		self.currentUser = getpass.getuser()

		from helix import Person
		user = Person.fromPk(self.currentUser)

		if not user:
			# Add user to DB automatically if we are configured to
			if env.cfg.autoAddUsers:
				user = Person(self.currentUser)
				user.insert()

			# User not existing causes other problems down the line...
			# Should we handle that here? Or do I just silently ignore and put them
			# in the default group..
			permGroup = PermissionGroup.fromPk(PermissionGroup.DEFAULT)
		else:
			permGroup = user.permGroup

			if not permGroup:
				permGroup = PermissionGroup.fromPk(PermissionGroup.DEFAULT)

		# In circumstances where even the default perm group doesn't exist, we must add it
		if not permGroup:
			permGroup = PermissionGroup(PermissionGroup.DEFAULT, permissions=['helix.*'])
			permGroup.insert()

		self.group = permGroup.group_name
		self.permNodes = permGroup.permissionList

	def check(self, node, silent=False):
		# First check negated node, since that would override anything else
		if '^' + node in self.permNodes:
			if silent:
				return False
			raise PermissionError('You don\'t have permission to do this')

		if node in self.permNodes:
			return True

		wildcards = self.toWildcard(node)
		negWildcards = ['^' + w for w in wildcards]

		# First check negated wildcard nodes
		for nw in negWildcards:
			if nw in self.permNodes:
				if silent:
					return False
				raise PermissionError('You don\'t have permission to do this')

		for w in wildcards:
			if w in self.permNodes:
				return True

		if silent:
			return False
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

def permissionCheck(node):
	_node = node # In case we error
	if node not in PermissionNodes.nodes.values():
		node = PermissionNodes.nodes.get(node)

		if not node:
			raise RuntimeError('Invalid node {} does not exist'.format(_node))

	def realDecorator(function):
		def wrapper(*args, **kwargs):
			PermissionHandler().check(node)
			return function(*args, **kwargs)
		return wrapper
	return realDecorator

