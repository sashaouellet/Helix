from helix.database.database import DatabaseObject

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
			self.department = department

	def __str__(self):
		if self.full_name:
			return '{} ({})'.format(self.full_name, self.username)
		else:
			return self.username

	@property
	def pk(self):
		return Person.PK