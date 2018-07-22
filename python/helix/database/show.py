import os

from helix.database.database import DatabaseObject
from helix.database.person import Person
import helix.environment.environment as env
import helix.utils.utils as utils

class Show(DatabaseObject):
	TABLE='shows'

	def __init__(self, alias, name=None, author=None, makeDirs=False, dummy=False):
		self.table = Show.TABLE

		if dummy:
			return

		sanitary, reasons = utils.isSanitary(alias)

		if not sanitary:
			raise ValueError('Invalid alias specified:' + '\n'.join(reasons))

		self.alias = alias

		if len(self.alias) > 10:
			raise ValueError('Alias can\'t be longer than 10 characters')

		self._exists = None

		fetched = self.exists(fetch=True)

		if fetched:
			self.unmap(fetched)
			self._exists = True
		else:
			self._exists = False
			self.name = name

			creationInfo = env.getCreationInfo(format=False)

			self.author = author if author else creationInfo[0]
			self.creation = creationInfo[1]
			self.work_path = os.path.join(env.getEnvironment('work'), self.directory)
			self.release_path = os.path.join(env.getEnvironment('release'), self.directory)

			p = Person(self.author)

			if not p.exists():
				raise ValueError('No such user: {}'.format(self.author))

		if makeDirs:
			if not os.path.isdir(self.work_path):
				os.makedirs(self.work_path)

			if not os.path.isdir(self.release_path):
				os.makedirs(self.release_path)

	def getSequences(self, nums=[]):
		from helix.database.sql import Manager
		from helix.database.sequence import Sequence

		with Manager(willCommit=False) as mgr:
			query = """SELECT * FROM {} WHERE show='{}'""".format(Sequence.TABLE, self.alias)

			if nums is not None:
				if isinstance(nums, int):
					nums = [nums]
				if nums:
					query += " AND num in ({})".format(','.join(["'{}'".format(n) for n in nums]))

			seqs = []

			for row in mgr.connection().execute(query).fetchall():
				seqs.append(Sequence.dummy().unmap(row))

			return seqs

	def getShots(self, seqs=[], nums=[]):
		from helix.database.sql import Manager
		from helix.database.shot import Shot

		with Manager(willCommit=False) as mgr:
			query = """SELECT * FROM {} WHERE show='{}'""".format(
				Shot.TABLE,
				self.alias
			)

			if seqs is not None:
				if isinstance(seqs, int):
					seqs = [seqs]
				if seqs:
					query += " AND sequence IN ({})".format(','.join(["'{}'".format(n) for n in seqs]))

			if nums is not None:
				if isinstance(nums, int):
					nums = [nums]
				if nums:
					query += " AND num IN ({})".format(','.join(["'{}'".format(n) for n in nums]))

			shots = []

			for row in mgr.connection().execute(query).fetchall():
				shots.append(Shot.dummy().unmap(row))

			return shots

	def getElements(self, names=[], types=[], seqs=[], shots=[], authors=[], assignedTo=[], status=[]):
		from helix.database.sql import Manager
		from helix.database.element import Element

		with Manager(willCommit=False) as mgr:
			query = """SELECT * FROM {} WHERE show='{}'""".format(
				Element.TABLE,
				self.alias
			)

			if names is not None:
				if isinstance(names, str):
					names = [names]
				if names:
					query += " AND name IN ({})".format(','.join(["'{}'".format(n) for n in names]))

			if types is not None:
				if isinstance(types, str):
					types = [types]
				if types:
					query += " AND type IN ({})".format(','.join(["'{}'".format(n) for n in types]))

			if seqs is not None:
				if isinstance(seqs, int):
					seqs = [seqs]
				if seqs:
					query += " AND sequence IN ({})".format(','.join(["'{}'".format(n) for n in seqs]))

			if shots is not None:
				if isinstance(shots, int):
					shots = [shots]
				if shots:
					query += " AND num IN ({})".format(','.join(["'{}'".format(n) for n in shots]))

			if status is not None:
				if isinstance(status, str):
					status = [status]
				if status:
					query += " AND status IN ({})".format(','.join(["'{}'".format(n) for n in status]))

			if authors is not None:
				if isinstance(authors, str):
					authors = [authors]
				if authors:
					query += " AND author IN ({})".format(','.join(["'{}'".format(n) for n in authors]))

			if assignedTo is not None:
				if isinstance(assignedTo, str):
					assignedTo = [assignedTo]
				if assignedTo:
					query += " AND assigned_to IN ({})".format(','.join(["'{}'".format(n) for n in assignedTo]))

			elements = []

			for row in mgr.connection().execute(query).fetchall():
				elements.append(Element.dummy().unmap(row))

			return elements

	@property
	def directory(self):
		return self.alias

	@property
	def pk(self):
		return 'alias'
