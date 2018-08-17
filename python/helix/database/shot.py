import os

from helix.database.elementContainer import ElementContainer
from helix.database.mixins import FixMixin
from helix.database.show import Show
from helix.database.sequence import Sequence
from helix.database.person import Person
import helix.environment.environment as env
from helix.utils.fileutils import SHOT_FORMAT

class Shot(ElementContainer, FixMixin):
	TABLE = 'shots'
	PK = 'id'

	def __init__(self, num, sequence, show=None, author=None, clipName=None, start=0, end=0, makeDirs=False, dummy=False):
		self.table = Shot.TABLE
		self.num = num
		self.sequence = sequence
		self.show = show if show else env.getEnvironment('show')
		self.clipName = clipName
		self._exists = None

		self.sequenceId = None

		if dummy:
			return

		if num is None:
			raise ValueError('Shot\'s num can\'t be None')

		try:
			self.num = int(num)
		except ValueError:
			raise ValueError('Shot number must be a number, not: {}'.format(num))

		if sequence is None:
			raise ValueError('Shot\'s sequence can\'t be None')

		try:
			self.sequence = int(sequence)
		except ValueError:
			raise ValueError('Sequence number must be a number, not: {}'.format(sequence))

		if not self.show:
			raise ValueError('Tried to fallback to environment-set show, but it was null.')

		fetched = self.exists(fetch=True)

		if fetched:
			self.unmap(fetched)
			self._exists = True
		else:
			self._exists = False
			creationInfo = env.getCreationInfo(format=False)

			self.author = author if author else creationInfo[0]
			self.creation = creationInfo[1]
			self.start = start
			self.end = end
			self.clipName = clipName
			self.take = 0

			s = Show.fromPk(self.show)
			sq = Sequence(self.sequence, show=self.show)

			if not s:
				raise ValueError('No such show: {}'.format(show))

			p = Person(self.author)

			if not p.exists():
				raise ValueError('No such user: {}'.format(self.author))

			if not sq.exists():
				raise ValueError('No such sequence {} in show {}'.format(sq.num, sq.show))
			else:
				self.sequenceId = sq.id

			self.work_path = os.path.join(sq.work_path, self.directory)
			self.release_path = os.path.join(sq.release_path, self.directory)

			if makeDirs:
				if not os.path.isdir(self.work_path):
					os.makedirs(self.work_path)

				if not os.path.isdir(self.release_path):
					os.makedirs(self.release_path)

	def getElements(self, names=[], types=[], authors=[], assignedTo=[], status=[], exclusive=False, debug=False):
		return super(Shot, self).getElements(
			shows=self.show,
			seqs=self.sequence,
			shots=self.num,
			clips=self.clipName if self.clipName else 'null',
			names=names,
			types=types,
			authors=authors,
			assignedTo=assignedTo,
			status=status,
			debug=debug
		)

	def getLatestTake(self):
		from helix.database.sql import Manager
		from helix.database.take import Take

		with Manager(willCommit=False) as mgr:
			res = mgr.connection().execute(
				'''
					SELECT *
					FROM {table}
					WHERE num = (SELECT MAX(num) FROM {table} WHERE show='{show}' AND sequenceId='{seq}' AND shotId='{shot}')
				'''.format(table=Take.TABLE, show=self.show, seq=self.parent.id, shot=self.id)
			).fetchone()

			if res:
				return Take.dummy().unmap(res)
			else:
				return None

	def addCheckpointStage(self, stage):
		from helix.database.checkpoint import Checkpoint

		if stage.lower() not in Checkpoint.STAGES:
			raise ValueError('Invalid stage "{}". Must be one of: {}'.format(stage, ', '.join(Checkpoint.STAGES)))

		cp = Checkpoint(self.id, stage, show=self.show)

		if cp.exists():
			print 'Checkpoint "{}" has already been added for this shot'.format(stage)
		else:
			cp.insert()

	def getCheckpoints(self):
		from helix.database.sql import Manager
		from helix.database.checkpoint import Checkpoint

		with Manager(willCommit=False) as mgr:
			query = """SELECT * FROM {} WHERE shotId='{}'""".format(Checkpoint.TABLE, self.id)
			cps = []

			for row in mgr.connection().execute(query).fetchall():
				cps.append(Checkpoint.dummy().unmap(row))

			return cps

	def __str__(self):
		return 'Shot ' + str(self.num) + (self.clipName if self.clipName else '')

	@property
	def id(self):
		return super(Shot, self)._id(
			'{}_{}_{}_{}'.format(
				self.show,
				str(self.sequence),
				str(self.num),
				self.clipName if self.clipName else ''
			)
		)

	@property
	def directory(self):
		return '{}{}'.format(
			SHOT_FORMAT.format(str(self.num).zfill(env.SEQUENCE_SHOT_PADDING)),
			'_' + self.clipName if self.clipName else ''
		)

	@property
	def parent(self):
		return Sequence.fromPk(self.sequenceId)

	@property
	def thumbnail(self):
		take = self.getLatestTake()

		if take is not None:
			return take.thumbnail

		return None

	@property
	def pk(self):
		return Shot.PK

	@staticmethod
	def dummy():
		return Shot(0, 0, dummy=True)
