import os

from helix.database.database import DatabaseObject
from helix.database.show import Show
from helix.database.sequence import Sequence
from helix.database.shot import Shot
from helix.database.person import Person
import helix.environment.environment as env
from helix.utils.fileutils import SHOT_FORMAT, SEQUENCE_FORMAT

class Snapshot(DatabaseObject):
	TABLE = 'snapshots'
	PK = 'id'

	def __init__(self, shot, sequence, show=None, clipName=None, author=None, comment=None, start=None, end=None, makeDirs=False, dummy=False):
		self.table = Snapshot.TABLE
		self.show = show if show else env.getEnvironment('show')
		self.sequence = sequence
		self.shot = shot
		self._exists = None

		self.sequenceId = None
		self.shotId = None
		self.first_frame = start
		self.last_frame = end

		if dummy:
			return

		if not self.show:
			raise ValueError('Tried to fallback to environment-set show, but it was null.')

		s = Show.fromPk(self.show)

		if not s:
			raise ValueError('No such show: {}'.format(show))

		if self.sequence is not None:
			try:
				self.sequence = int(self.sequence)
			except ValueError:
				raise ValueError('Sequence number must be a number, not: {}'.format(self.sequence))

			sq = Sequence(self.sequence, show=self.show)

			if not sq.exists():
				raise ValueError('No such sequence {} in show {}'.format(sq.num, sq.show))
			else:
				self.sequenceId = sq.id

		if self.shot is not None and self.sequence is not None:
			try:
				self.shot = int(shot)
			except ValueError:
				raise ValueError('Shot number must be a number, not: {}'.format(shot))

			sh = Shot(self.shot, self.sequence, show=self.show, clipName=clipName)

			if not sh.exists():
				raise ValueError('No such shot {} in sequence {} in show {}'.format(sh.num, sh.sequence, sh.show))
			else:
				self.shotId = sh.id
				self.first_frame = self.first_frame if self.first_frame else sh.start
				self.last_frame = self.last_frame if self.last_frame else sh.end

		self.num = Snapshot.nextSnapshotNum(self.show, self.sequenceId, self.shotId)

		fetched = self.exists(fetch=True)

		if fetched:
			self.unmap(fetched)
			self._exists = True
		else:
			creationInfo = env.getCreationInfo(format=False)

			self.comment = comment
			self.author = author if author else creationInfo[0]
			self.creation = creationInfo[1]
			self.first_frame = start
			self.last_frame = end

			p = Person(self.author)

			if not p.exists():
				raise ValueError('No such user: {}'.format(self.author))

			shotDir = Shot.fromPk(self.shotId).release_path

			self.file_path = os.path.join(shotDir, '.snapshots', str(self.num))

			if makeDirs and not os.path.isdir(self.file_path):
				os.makedirs(self.file_path)

	@property
	def id(self):
		return super(Snapshot, self)._id(
			'{}_{}_{}_{}'.format(
				self.show,
				self.sequenceId,
				self.shotId,
				self.num
			)
		)

	@property
	def pk(self):
		return Snapshot.PK

	@property
	def imageSequence(self):
		fileName = '{}_snapshot{}.{}.png'.format(
			str(Shot.fromPk(self.shotId)).replace(' ', '_').lower(),
			str(self.num),
			'#' * env.FRAME_PADDING
		)

		return os.path.join(self.file_path, fileName)

	@property
	def mov(self):
		fileName = '{}_snapshot{}.mov'.format(
			str(Shot.fromPk(self.shotId)).replace(' ', '_').lower(),
			str(self.num)
		)

		return os.path.join(self.file_path, fileName)

	@property
	def thumbnail(self):
		if self.first_frame is not None and self.last_frame is not None:
			middle = (self.first_frame + self.last_frame) / 2
			return self.imageSequence.replace(
				'#' * env.FRAME_PADDING,
				str(middle).zfill(env.FRAME_PADDING)
			)
		else:
			return None

	@staticmethod
	def nextSnapshotNum(show, sequence, shot):
		from helix.database.sql import Manager

		with Manager(willCommit=False) as mgr:
			res = mgr.connection().execute(
				'''
					SELECT MAX(num) from {} WHERE show='{}' AND sequenceId='{}' AND shotId='{}'
				'''.format(Snapshot.TABLE, show, sequence, shot)
			).fetchone()

			if res and res[0]:
				return int(res[0]) + 1
			else:
				return 1

	@staticmethod
	def dummy():
		return Snapshot('', '', dummy=True)

