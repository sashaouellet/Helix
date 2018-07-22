import os

from helix.database.database import DatabaseObject
from helix.database.show import Show
from helix.database.person import Person
import helix.environment.environment as env
from helix.utils.fileutils import SEQUENCE_FORMAT

class Sequence(DatabaseObject):
	TABLE = 'sequences'
	def __init__(self, num, show=None, author=None, makeDirs=False, dummy=False):
		self.table = Sequence.TABLE
		self.num = num
		self.show = show if show else env.show
		self._exists = None

		if dummy:
			return

		if num is None:
			raise ValueError('Sequence\'s num can\'t be None')

		try:
			self.num = int(num)
		except ValueError:
			raise ValueError('Sequence number must be a number, not: {}'.format(num))

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

			p = Person(self.author)

			if not p.exists():
				raise ValueError('No such user: {}'.format(self.author))

			if makeDirs:
				if not os.path.isdir(self.work_path):
					os.makedirs(self.work_path)

				if not os.path.isdir(self.release_path):
					os.makedirs(self.release_path)

	def getShots(self, nums=[]):
		from helix.database.sql import Manager
		from helix.database.shot import Shot

		with Manager(willCommit=False) as mgr:
			query = """SELECT * FROM {} WHERE show='{}' AND sequenceId='{}'""".format(Shot.TABLE, self.show, self.id)

			if nums is not None:
				if isinstance(nums, int):
					nums = [nums]
				if nums:
					query += " AND num in ({})".format(','.join(["'{}'".format(n) for n in nums]))

			shots = []

			for row in mgr.connection().execute(query).fetchall():
				shots.append(Shot.dummy().unmap(row))

			return shots

	@property
	def id(self):
		return super(Sequence, self)._id(
			'{}_{}'.format(
				self.show,
				str(self.num)
			)
		)

	@property
	def directory(self):
		return SEQUENCE_FORMAT.format(str(self.num).zfill(env.SEQUENCE_SHOT_PADDING))

	@property
	def pk(self):
		return 'id'

	@staticmethod
	def dummy():
		return Sequence(0, dummy=True)