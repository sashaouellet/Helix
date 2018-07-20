import os

from helix.database.database import DatabaseObject
from helix.database.person import Person
import helix.environment.environment as env

class Show(DatabaseObject):
	TABLE='shows'

	def __init__(self, alias, name=None, author=None):
		self.table = Show.TABLE
		self.alias = alias # TODO implement sanitization
		self._exists = None

		fetched = self.exists(fetch=True)

		if fetched:
			self.unmap(fetched)
			self._exists = True
		else:
			self._exists = False
			self.name = name

			creationInfo = env.getCreationInfo(format=False)

			self.author = author if author else creationInfo[0]
			self.creation = creationInfo[1]
			self.work_path = os.path.join(env.getEnvironment('work'), self.alias)
			self.release_path = os.path.join(env.getEnvironment('release'), self.alias)

		if not os.path.isdir(self.work_path):
			os.makedirs(self.work_path)

		if not os.path.isdir(self.release_path):
			os.makedirs(self.release_path)

	def exists(self, fetch=False):
		# we cache the exists after construction because we either fetched
		# it from the DB or made a new one
		if self._exists is not None and not fetch:
			return self._exists

		return super(Show, self).exists(self.pk, fetch=fetch)

	def get(self, attr, default=None):
		return super(Show, self).get(attr, self.pk, default=default)

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
		return 'alias'
