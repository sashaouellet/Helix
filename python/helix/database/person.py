from helix.database.database import DatabaseObject
import helix.environment.environment as env

class Person(DatabaseObject):
	TABLE = 'people'
	PK = 'username'

	def __init__(self, username, full_name=None, department=None, dummy=False):
		self.table=Person.TABLE
		self.username = username
		self._exists = None

		if dummy:
			return

		if len(self.username) > 10:
			raise ValueError('Username cannot be longer than 10 characters')

		fetched = self.exists(fetch=True)

		if fetched:
			self.unmap(fetched)
			self._exists = True
		else:
			self._exists = False
			self.full_name = full_name

			if not department:
				department = 'general'

			self.department = department.lower()

			from helix.environment.permissions import PermissionGroup

			# Create the default group right away if it doesn't exist
			# otherwise, we can't insert the user into the database with that group
			defGroup = PermissionGroup(PermissionGroup.DEFAULT, permissions=['helix.*'])

			if not defGroup.exists():
				defGroup.insert()

			self.perm_group = PermissionGroup.DEFAULT

			if self.department not in env.cfg.departments and self.department != 'general':
				raise ValueError('Not a valid department ({}). Options are: {}'.format(self.department, ', '.join(['general'] + env.cfg.departments)))

	def __str__(self):
		if self.full_name:
			return '{} ({})'.format(self.full_name, self.username)
		else:
			return self.username

	@property
	def permGroup(self):
		from helix.environment.permissions import PermissionGroup
		return PermissionGroup.fromPk(self.perm_group)

	@property
	def pk(self):
		return Person.PK

	@staticmethod
	def dummy():
		return Person('', dummy=True)