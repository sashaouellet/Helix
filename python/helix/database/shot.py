import os

from helix.database.database import DatabaseObject
from helix.database.show import Show
from helix.database.sequence import Sequence
import helix.environment.environment as env
from helix.utils.fileutils import SHOT_FORMAT

class Shot(DatabaseObject):
	TABLE = 'shots'
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
	def __init__(self, num, sequence, show=None, author=None, makeDirs=False):
		self.table = Shot.TABLE
		self.num = num
		self.sequence = sequence
		self.show = show if show else env.show
		self._exists = None

		if not num:
			raise ValueError('Shot\'s num can\'t be None')

		try:
			self.num = int(num)
		except ValueError:
			raise ValueError('Shot number must be a number, not: {}'.format(num))

		if not sequence:
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
			creationInfo = env.getCreationInfo(format=False)

			self.author = author if author else creationInfo[0]
			self.creation = creationInfo[1]
			self.start = 0
			self.end = 0
			self.clipName = None
			self.status = Shot.STATUS[0]
			self.assigned_to = None
			self.take = 0
			self.thumbnail = None

			s = Show(self.show)
			sq = Sequence(self.sequence, show=self.show)

			if not s.exists():
				raise ValueError('No such show: {}'.format(show))

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

	@property
	def id(self):
		return super(Shot, self)._id(
			'{}_{}_{}'.format(
				self.show,
				str(self.sequence),
				str(self.num)
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
		return 'id'
