import os

from helix.database.elementContainer import ElementContainer
from helix.database.mixins import FixMixin
from helix.database.show import Show
from helix.database.person import Person
import helix.environment.environment as env
from helix.utils.fileutils import SEQUENCE_FORMAT

class Sequence(ElementContainer, FixMixin):
	TABLE = 'sequences'
	PK = 'id'

	def __init__(self, num, show=None, author=None, makeDirs=False, dummy=False):
		self.table = Sequence.TABLE
		self.num = num
		self.show = show if show else env.getEnvironment('show')
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

			s = Show.fromPk(self.show)

			if not s:
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

	def getElements(self, names=[], types=[], shots=[], clips=[], authors=[], assignedTo=[], status=[], exclusive=False, debug=False):
		return super(Sequence, self).getElements(
			shows=self.show,
			seqs=self.num,
			names=names,
			types=types,
			shots=shots if not exclusive else 'null',
			clips=clips if not exclusive else 'null',
			authors=authors,
			assignedTo=assignedTo,
			status=status,
			debug=debug
		)

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

	def __str__(self):
		return 'Sequence ' + str(self.num)

	@property
	def completion(self):
		from helix.database.sql import Manager
		from helix import Fix

		with Manager(willCommit=False) as mgr:
			query = """SELECT status, COUNT(*) FROM {} WHERE show='{}' and type='task' AND sequenceId='{}' GROUP BY status""".format(Fix.TABLE, self.show, self.id)
			rows = mgr.connection().execute(query).fetchall()

			if rows:
				done = 0
				total = 0

				for r in rows:
					total += r[1] # Add count for this status to total
					if r[0] == 'done':
						done += r[1]

				return float(done) / total
			else:
				# No tasks at all, 0% completion. Maybe we want no tasks to mean 100% completion?
				return 0

	@property
	def id(self):
		return super(Sequence, self)._id(
			'{}_{}'.format(
				self.show,
				str(self.num)
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
		return SEQUENCE_FORMAT.format(str(self.num).zfill(env.SEQUENCE_SHOT_PADDING))

	@property
	def parent(self):
		return Show.fromPk(self.show)

	@property
	def pk(self):
		return Sequence.PK

	@staticmethod
	def dummy():
		return Sequence(0, dummy=True)
