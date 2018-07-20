import os

from helix.database.database import DatabaseObject
from helix.database.show import Show
import helix.environment.environment as env
from helix.utils.fileutils import SEQUENCE_FORMAT

class Sequence(DatabaseObject):
	TABLE = 'sequences'
	def __init__(self, num, show=env.show, author=None):
		self.table = Sequence.TABLE
		self.num = num
		self.show = show if show else env.show
		self._exists = None

		if not num:
			raise ValueError('Sequence\'s num can\'t be None')

		if not self.show:
			raise ValueError('Tried to fallback to environment-set show, but it was null.')

		fetched = self.exists(fetch=True)

		if fetched:
			self.unmap(fetched)
			self._exists = True
		else:
			creationInfo = env.getCreationInfo(format=False)

			self.author = author if author else creationInfo[0]
			self.creation = creationInfo[1]

			s = Show(self.show)

			if not s.exists():
				raise ValueError('No such show: {}'.format(show))
			else:
				self.work_path = os.path.join(s.work_path, self.directory)
				self.release_path = os.path.join(s.release_path, self.directory)

			if not os.path.isdir(self.work_path):
				os.makedirs(self.work_path)

			if not os.path.isdir(self.release_path):
				os.makedirs(self.release_path)

	@property
	def id(self):
		return super(Sequence, self)._id(self.show + str(self.num))

	def exists(self, fetch=False):
		# we cache the exists after construction because we either fetched
		# it from the DB or made a new one
		if self._exists is not None and not fetch:
			return self._exists

		return super(Sequence, self).exists(self.pk, fetch=fetch)

	@property
	def directory(self):
		return SEQUENCE_FORMAT.format(str(self.num).zfill(env.SEQUENCE_SHOT_PADDING))

	@property
	def pk(self):
		return 'id'
