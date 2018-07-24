import os

from helix.database.elementContainer import ElementContainer
from helix.database.show import Show
from helix.database.sequence import Sequence
from helix.database.person import Person
import helix.environment.environment as env
from helix.utils.fileutils import SHOT_FORMAT

class Shot(ElementContainer):
	TABLE = 'shots'
	PK = 'id'
	STATUS = { # TODO: configurable
		0: 'new', # Should always be first though
		1: 'assigned',
		2: 'layout',
		3: 'lock_for_anim',
		4: 'animation_rough',
		5: 'animation_final',
		6: 'set_decoration',
		7: 'shading',
		8: 'master_lighting',
		9: 'shot_lighting',
		10: 'fx',
		11: 'comp',
		12: 'ip',
		13: 'review',
		14: 'done'
	}
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
			self.status = Shot.STATUS[0]
			self.assigned_to = None
			self.take = 0
			self.thumbnail = None

			s = Show(self.show)
			sq = Sequence(self.sequence, show=self.show)

			if not s.exists():
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
	def pk(self):
		return Shot.PK

	@staticmethod
	def dummy():
		return Shot(0, 0, dummy=True)
