"""
.. module:: show
   :synopsis: Represents the data structure of a Show in the database

.. moduleauthor:: Sasha Ouellet <sashaouellet@gmail.com>

"""

import os

from helix.database.elementContainer import ElementContainer
from helix.database.mixins import FixMixin
from helix.database.person import Person
import helix.environment.environment as env
import helix.utils.utils as utils

class Show(ElementContainer, FixMixin):
	TABLE='shows'
	PK='alias'

	def __init__(self, alias, resolution, fps, name=None, author=None, makeDirs=False, dummy=False):
		"""Construct a new show. Based on the given parameter values, this
		may equate to a show that already exists in the DB, or will construct
		an entirely new instance.

		Args:
		    alias (str): The alias (internal name) of the show
		    resolution (tuple): The image resolution for the show
		    fps (float): The frames per second that the show will follow
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

			if not isinstance(resolution, tuple) or len(resolution) != 2:
				raise ValueError('Invalid resolution specified, must be a length 2 tuple representing the width and height values')

			self.resolution_x = resolution[0]
			self.resolution_y = resolution[1]
			self.fps = fps
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

	def getSequence(self, num):
		seqs = self.getSequences(nums=[num])

		return seqs[0] if seqs else None

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

	def getShot(self, seq, num, clipName=None):
		shots = self.getShots(seqs=[seq], nums=[num])

		for s in shots:
			if s.clipName == clipName:
				return s

		return None

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
	def resolution(self):
		return (self.resolution_x, self.resolution_y)

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
		return self.alias

	@property
	def id(self):
		return self.alias

	@property
	def pk(self):
		return Show.PK

	@staticmethod
	def dummy():
		return Show(None, None, None, dummy=True)
