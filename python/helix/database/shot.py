import os

from helix.database.database import DatabaseObject
from helix.database.show import Show
from helix.database.sequence import Sequence
import helix.environment.environment as env
from helix.utils.fileutils import SHOT_FORMAT

class Shot(DatabaseObject):
	TABLE = 'shots'
	def __init__(self, num, sequence, show=env.show, author=None):
		self.table = Shot.TABLE
		self.num = num
		self.sequence = sequence
		self.show = show if show else env.show
		self._exists = None

		if not num:
			raise ValueError('Shot\'s num can\'t be None')

		if not sequence:
			raise ValueError('Shot\'s sequence can\'t be None')

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
			self.start = 0
			self.end = 0
			self.clipName = ''
			self.assigned_to = None
			self.take = 0
			self.thumbnail = ''

			s = Show(self.show)
			sq = Sequence(self.sequence, show=self.show)

			if not s.exists():
				raise ValueError('No such show: {}'.format(show))

			if not sq.exists():
				raise ValueError('No such sequence {} in show {}'.format(self.sequence, self.show))

			self.work_path = os.path.join(sq.work_path, self.directory)
			self.release_path = os.path.join(sq.release_path, self.directory)

			if not os.path.isdir(self.work_path):
				os.makedirs(self.work_path)

			if not os.path.isdir(self.release_path):
				os.makedirs(self.release_path)

	@property
	def id(self):
		return super(Shot, self)._id(self.show + str(self.sequence) + str(self.num))

	def exists(self, fetch=False):
		# we cache the exists after construction because we either fetched
		# it from the DB or made a new one
		if self._exists is not None and not fetch:
			return self._exists

		return super(Shot, self).exists(self.pk, fetch=fetch)

	@property
	def directory(self):
		return SHOT_FORMAT.format(str(self.num).zfill(env.SEQUENCE_SHOT_PADDING))

	@property
	def pk(self):
		return 'id'
