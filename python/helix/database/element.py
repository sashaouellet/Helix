import os

from helix.database.database import DatabaseObject
from helix.database.show import Show
from helix.database.sequence import Sequence
from helix.database.shot import Shot
import helix.environment.environment as env
from helix.utils.fileutils import SHOT_FORMAT, SEQUENCE_FORMAT

class Element(DatabaseObject):
	TABLE = 'elements'
	STATUS = {
		0: 'new',
		1: 'assigned',
		2: 'ip',
		3: 'review',
		4: 'done'
	}
	SET = 'set'
	LIGHT = 'light'
	CHARACTER = 'character'
	PROP = 'prop'
	TEXTURE = 'texture'
	EFFECT = 'effect'
	COMP = 'comp'
	CAMERA = 'camera'
	PLATE = 'plate'
	ELEMENT_TYPES = [SET, LIGHT, CHARACTER, PROP, TEXTURE, EFFECT, COMP, CAMERA, PLATE]

	def __init__(self, name, elType, show=None, sequence=None, shot=None, author=None, makeDirs=False):
		self.table = Element.TABLE
		self.name = name # Sanitize
		self.type = elType # Must be from list
		self.show = show if show else env.show
		self.sequence = sequence
		self.shot = shot
		self._exists = None

		if not name:
			if not shot or not sequence:
				raise ValueError('Element\'s name can only be None (considered nameless) if shot and sequence are also specified')
			else:
				self.name = '_{}{}'.format(
						SEQUENCE_FORMAT.format(str(self.sequence).zfill(env.SEQUENCE_SHOT_PADDING)),
						SHOT_FORMAT.format(str(self.shot).zfill(env.SEQUENCE_SHOT_PADDING))
					)

		if not elType:
			raise ValueError('Element\'s type can\'t be None')

		self.elType = elType.lower()

		if self.elType not in Element.ELEMENT_TYPES:
			raise ValueError('Invalid element type: {}. Must be one of: {}'.format(self.elType, ', '.join(Element.ELEMENT_TYPES)))

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
			self.status = Element.STATUS[0]
			self.assigned_to = None
			self.pubVersion = 0
			self.version = 1
			self.thumbnail = None

			s = Show(self.show)

			if not s.exists():
				raise ValueError('No such show: {}'.format(show))

			baseWorkDir = s.work_path
			baseReleaseDir = s.release_path

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

				baseWorkDir = sq.work_path
				baseReleaseDir = sq.release_path

			if self.shot and self.sequence:
				try:
					self.shot = int(shot)
				except ValueError:
					raise ValueError('Sequence number must be a number, not: {}'.format(shot))

				sh = Shot(self.shot, self.sequence, show=self.show)

				if not sh.exists():
					raise ValueError('No such shot {} in sequence {} in show {}'.format(sh.num, sh.sequence, sh.show))
				else:
					self.shotId = sh.id

				baseWorkDir = sh.work_path
				baseReleaseDir = sh.release_path

			self.work_path = os.path.join(baseWorkDir, self.directory)
			self.release_path = os.path.join(baseReleaseDir, self.directory)

		if makeDirs:
			if not os.path.isdir(self.work_path):
				os.makedirs(self.work_path)

			if not os.path.isdir(self.release_path):
				os.makedirs(self.release_path)

	@property
	def id(self):
		return super(Element, self)._id(
			'{}_{}_{}_{}_{}'.format(
				self.show,
				self.sequence if self.sequence else '',
				self.shot if self.shot else '',
				self.name,
				self.type
			)
		)

	@property
	def directory(self):
		nameDir = '' if self.name.startswith('_') else self.name
		return os.path.join(self.type, nameDir)

	@property
	def pk(self):
		return 'id'
