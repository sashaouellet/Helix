"""
.. module:: show
   :synopsis: Represents the data structure of a Show in the database

.. moduleauthor:: Sasha Ouellet <sashaouellet@gmail.com>

"""

import os

from helix.database.elementContainer import ElementContainer
from helix.database.person import Person
import helix.environment.environment as env
import helix.utils.utils as utils

class Show(ElementContainer):
	TABLE='shows'
	PK='alias'

	def __init__(self, alias, name=None, author=None, makeDirs=False, dummy=False):
		"""Construct a new show. Based on the given parameter values, this
		may equate to a show that already exists in the DB, or will construct
		an entirely new instance.
		
		Args:
		    alias (str): The alias (internal name) of the show
		    name (str, optional): The long, descriptive name
		    author (str, optional): The creator of the show, defaults to the
		    	current user
		    makeDirs (bool, optional): Whether to make the show's directories on
		    	disk, if they don't already exist.
		    dummy (bool, optional): Whether this is a throwaway instance or not.
		    	Dummy instances are meant to be "unmapped" into since they will
		    	have no attributes set.
		
		Raises:
		    ValueError: If the alias specified does not meet the sanitation criteria,
		    	or if the given user (if any provided) does not exist in the database
		    	already.
		"""
		self.table = Show.TABLE

		if dummy:
			return

		sanitary, reasons = utils.isSanitary(alias)

		if not sanitary:
			raise ValueError('Invalid alias specified:' + '\n'.join(reasons))

		self.alias = alias

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

	def getElements(self, names=[], types=[], seqs=[], shots=[], clips=[], authors=[], assignedTo=[], status=[], exclusive=False, debug=False):
		return super(Show, self).getElements(
			shows=self.alias,
			names=names,
			types=types,
			seqs=seqs if not exclusive else 'null',
			shots=shots if not exclusive else 'null',
			clips=clips if not exclusive else 'null',
			authors=authors,
			assignedTo=assignedTo,
			status=status,
			debug=debug
		)

	def __str__(self):
		return self.alias

	@property
	def directory(self):
		return self.alias

	@property
	def pk(self):
		return Show.PK

	@staticmethod
	def dummy():
		return Show('', dummy=True)
