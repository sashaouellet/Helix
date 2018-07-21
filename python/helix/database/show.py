import os

from helix.database.database import DatabaseObject
from helix.database.person import Person
import helix.environment.environment as env
import helix.utils.utils as utils

class Show(DatabaseObject):
	TABLE='shows'

	def __init__(self, alias, name=None, author=None, makeDirs=False):
		self.table = Show.TABLE

		sanitary, reasons = utils.isSanitary(alias)

		if not sanitary:
			raise ValueError('Invalid alias specified:' + '\n'.join(reasons))

		self.alias = alias # TODO: Can't be longer than 10 characters
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
			self.work_path = os.path.join(env.getEnvironment('work'), self.directory)
			self.release_path = os.path.join(env.getEnvironment('release'), self.directory)

			p = Person(self.author)

			if not p.exists():
				raise ValueError('No such user: {}'.format(self.author))

		if makeDirs:
			if not os.path.isdir(self.work_path):
				os.makedirs(self.work_path)

			if not os.path.isdir(self.release_path):
				os.makedirs(self.release_path)

	@property
	def directory(self):
		return self.alias

	@property
	def pk(self):
		return 'alias'
