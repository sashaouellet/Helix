import os

from helix.database.database import DatabaseObject
from helix.database.show import Show
from helix.database.sequence import Sequence
from helix.database.shot import Shot
from helix.database.person import Person
import helix.environment.environment as env
from helix.utils.fileutils import SHOT_FORMAT, SEQUENCE_FORMAT

class Take(DatabaseObject):
	TABLE = 'takes'

	def __init__(self, filePath, shot, sequence, show=None, author=None, comment=None, start=None, end=None):
		self.table = Take.TABLE
		self.show = show if show else env.show
		self.sequence = sequence
		self.shot = shot
		self.file_path = filePath
		self._exists = None

		self.sequenceId = None
		self.shotId = None
		self.first_frame = start
		self.last_frame = end


		if not self.show:
			raise ValueError('Tried to fallback to environment-set show, but it was null.')

		s = Show(self.show)

		if not s.exists():
			raise ValueError('No such show: {}'.format(show))

		if self.sequence:
			try:
				self.sequence = int(self.sequence)
			except ValueError:
				raise ValueError('Sequence number must be a number, not: {}'.format(self.sequence))

			sq = Sequence(self.sequence, show=self.show)

			if not sq.exists():
				raise ValueError('No such sequence {} in show {}'.format(sq.num, sq.show))
			else:
				self.sequenceId = sq.id

		if self.shot and self.sequence:
			try:
				self.shot = int(shot)
			except ValueError:
				raise ValueError('Shot number must be a number, not: {}'.format(shot))

			sh = Shot(self.shot, self.sequence, show=self.show)

			if not sh.exists():
				raise ValueError('No such shot {} in sequence {} in show {}'.format(sh.num, sh.sequence, sh.show))
			else:
				self.shotId = sh.id
				self.first_frame = self.first_frame if self.first_frame else sh.start
				self.last_frame = self.last_frame if self.last_frame else sh.end

		self.num = Take.nextTakeNum(self.show, self.sequenceId, self.shotId)

		if self.file_path is None: # TODO: do we force this path to exist?
			raise ValueError('Must specify a file path for the Take')

		fetched = self.exists(fetch=True)

		if fetched:
			self.unmap(fetched)
			self._exists = True
		else:
			creationInfo = env.getCreationInfo(format=False)

			self.author = author if author else creationInfo[0]
			self.creation = creationInfo[1]
			self.first_frame = start
			self.last_frame = end

			p = Person(self.author)

			if not p.exists():
				raise ValueError('No such user: {}'.format(self.author))

			self.thumbnail = None

	@property
	def id(self):
		return super(Take, self)._id(
			'{}_{}_{}_{}'.format(
				self.show,
				self.sequenceId,
				self.shotId,
				self.num
			)
		)

	@property
	def pk(self):
		return 'id'

	@staticmethod
	def nextTakeNum(show, sequence, shot):
		from helix.database.sql import Manager

		with Manager(willCommit=False) as mgr:
			res = mgr.connection().execute(
				'''
					SELECT MAX(num) from {} WHERE show='{}' AND sequenceId='{}' AND shotId='{}'
				'''.format(Take.TABLE, show, sequence, shot)
			).fetchone()

			if res and res[0]:
				return int(res[0]) + 1
			else:
				return 1

