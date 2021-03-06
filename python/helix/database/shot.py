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
			self.snapshot = 0

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

	def getLatestSnapshot(self):
		from helix.database.sql import Manager
		from helix import Snapshot

		with Manager(willCommit=False) as mgr:
			res = mgr.connection().execute(
				'''
					SELECT *
					FROM {table}
					WHERE num = (SELECT MAX(num) FROM {table} WHERE show='{show}' AND sequenceId='{seq}' AND shotId='{shot}')
				'''.format(table=Snapshot.TABLE, show=self.show, seq=self.parent.id, shot=self.id)
			).fetchone()

			if res:
				return Snapshot.dummy().unmap(res)
			else:
				return None

	def addStage(self, stage):
		from helix import Stage

		if stage.lower() not in Stage.STAGES:
			raise ValueError('Invalid stage "{}". Must be one of: {}'.format(stage, ', '.join(Stage.STAGES)))

		stage = Stage(self.id, stage, show=self.show)

		if stage.exists():
			print 'Stage "{}" has already been added for this shot'.format(stage)
		else:
			stage.insert()

	def getStages(self):
		from helix.database.sql import Manager
		from helix import Stage

		with Manager(willCommit=False) as mgr:
			query = """SELECT * FROM {} WHERE shotId='{}'""".format(Stage.TABLE, self.id)
			stages = []

			for row in mgr.connection().execute(query).fetchall():
				stages.append(Stage.dummy().unmap(row))

			return stages

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
	def work_path(self):
		return os.path.realpath(env.convertPath(self._work_path))

	@work_path.setter
	def work_path(self, val):
		self._work_path = val

	@property
	def release_path(self):
		return os.path.realpath(env.convertPath(self._release_path))

	@release_path.setter
	def release_path(self, val):
		self._release_path = val

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
		snapshot = self.getLatestSnapshot()

		if snapshot is not None:
			return snapshot.thumbnail

		return None

	@property
	def pk(self):
		return Shot.PK

	@staticmethod
	def dummy():
		return Shot(0, 0, dummy=True)
