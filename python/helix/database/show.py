import os

from helix.database.database import DatabaseObject
from helix.database.person import Person
import helix.environment.environment as env

class Show(DatabaseObject):
	TABLE='shows'

	def __init__(self, alias, name=None, author=None, makeDirs=False):
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

		if makeDirs:
			if not os.path.isdir(self.work_path):
				os.makedirs(self.work_path)

			if not os.path.isdir(self.release_path):
				os.makedirs(self.release_path)

	@property
	def pk(self):
		return 'alias'
