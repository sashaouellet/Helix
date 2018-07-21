from helix.database.database import DatabaseObject

class Person(DatabaseObject):
	TABLE='people'

	def __init__(self, username, full_name=None, department=None):
		self.table=Person.TABLE
		self.username = username
		self._exists = None

		fetched = self.exists(fetch=True)

		if fetched:
			self.unmap(fetched)
			self._exists = True
		else:
			self._exists = False
			self.full_name = full_name
			self.department = department

	@property
	def pk(self):
		return 'username'