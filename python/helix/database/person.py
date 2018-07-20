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

	def exists(self, fetch=False):
		# we cache the exists after construction because we either fetched
		# it from the DB or made a new one
		if self._exists is not None and not fetch:
			return self._exists

		return super(Person, self).exists(self.pk, fetch=fetch)

	def get(self, attr, default=None):
		return super(Person, self).get(attr, self.pk, default=default)

	def set(self, attr, val):
		from helix.database.sql import Manager
		with Manager() as mgr:
			if self.exists():
				mgr.connection().execute("UPDATE {} SET {}='{}' WHERE {}='{}'".format(self.table, attr, val, self.pk, getattr(self, self.pk)))
			else:
				setattr(self, attr, val)
				self.insert()

	@property
	def pk(self):
		return 'username'