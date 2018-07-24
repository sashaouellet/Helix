"""This module outlines all the different types of database objects that are stored to and from disk. Currently,
this is only implemented for a JSON implementation but should be easy to extend beyond that. The show object is the
parent of all other items and stores sequences. Sequences house shots which hold the individual elements that make up
that particular shot, i.e. Camera, FX, props, etc.

__author__  = Sasha Ouellet (sashaouellet@gmail.com / www.sashaouellet.com)
__version__ = 1.0.0
__date__    = 02/18/18
"""
import json
import os, sys, shutil, glob, datetime, copy, re, itertools
import helix.environment.environment as env
import helix.utils.fileutils as fileutils
from helix.api.exceptions import *
from helix.utils.fileclassification import FrameSequence, Frame
import sqlite3
import hashlib

class DatabaseObject(object):

	"""The DatabaseObject represents any individual piece of the database that will be saved to disk.
	The DatabaseObject is responsible for encoding and decoding itself to/from the JSON format.

	Each class inheriting DatabaseObject will have their class name stored under the key "_DBOType" in order
	for decoding operations to be simplified. This allows for a particular JSON object on disk to be easily
	indentified and then properly constructed given the rest of its data structure.
	"""
	def get(self, attr, default=None):
		from helix.database.sql import Manager
		with Manager(willCommit=False) as mgr:
			try:
				return mgr.connection().execute('SELECT {} FROM {} WHERE {}="{}"'.format(attr, self.table, self.pk, getattr(self, self.pk, None))).fetchone()[0]
			except sqlite3.OperationalError as e:
				print 'No such attribute: {}, defaulting to {}'.format(attr, default)
				return default

	def set(self, attr, val, insertIfMissing=False):
		from helix.database.sql import Manager
		with Manager() as mgr:
			if self.exists():
				mgr.connection().execute("UPDATE {} SET {}='{}' WHERE {}='{}'".format(self.table, attr, val, self.pk, getattr(self, self.pk)))
			else:
				setattr(self, attr, val)
				if insertIfMissing:
					self.insert()

	def insert(self):
		from helix.database.sql import Manager
		with Manager() as mgr:
			self._exists = mgr._insert(self.table, self)

			return self._exists

	def exists(self, fetch=False):
		# we cache the exists after construction because we either fetched
		# it from the DB or made a new one
		if self._exists is not None and not fetch:
			return self._exists

		from helix.database.sql import Manager

		with Manager(willCommit=False) as mgr:
			try:
				rows = mgr.connection().execute('SELECT * FROM {} WHERE {}="{}"'.format(self.table, self.pk, getattr(self, self.pk, None))).fetchall()

				if fetch:
					return rows[0] if rows else None
				else:
					return len(rows) > 0
			except sqlite3.OperationalError as e:
				print e
				if fetch:
					return None
				else:
					return False

	@classmethod
	def fromPk(cls, pk):
		if not pk:
			return None

		from helix.database.sql import Manager

		with Manager(willCommit=False) as mgr:
			query = """SELECT * FROM {} WHERE {}='{}'""".format(
				cls.TABLE,
				cls.PK,
				pk
			)

			row = mgr.connection().execute(query).fetchone()

			if row:
				return cls.dummy().unmap(row)

		return None

	def _id(self, token=''):
		# It's useless to call this on a subclass that hasn't
		# overwritten this method.. which is fine, not all of them
		# need to have an id.
		return hashlib.md5(token).hexdigest()

	@property
	def pk(self):
		raise NotImplementedError()

	def map(self):
		from helix.database.sql import Manager
		with Manager(willCommit=False) as mgr:
			values = ()

			for c, notNull in mgr.getColumnNames(self.table):
				val = getattr(self, c, None)

				if val is None and notNull:
					raise ValueError('{} for {} cannot be null'.format(c, type(self).__name__))

				values += (val, )

			return values

	def unmap(self, values):
		from helix.database.sql import Manager
		with Manager(willCommit=False) as mgr:
			for col, val in zip([c[0] for c in mgr.getColumnNames(self.table)], list(values)):
				try:
					setattr(self, col, val)
				except:
					# Gross, but for private variables we are
					# probably calculating them a different way anyway
					# when we retrieve them later
					pass

			self._exists = True

			return self

	def __repr__(self):
		from helix.database.sql import Manager
		with Manager(willCommit=False) as mgr:
			vals = []

			for c, _ in mgr.getColumnNames(self.table):
				val = getattr(self, c, None)

				if val is None:
					val = 'NULL'

				vals.append((c + '=' + str(val)))

			return type(self).__name__ + ' (' + ', '.join(vals) + ')'

	def __eq__(self, other):
		if not isinstance(other, type(self)):
			return False

		return self.__dict__ == other.__dict__

	def __ne__(self, other):
		return not (self == other)

def getShows():
	from helix.database.sql import Manager
	from helix.database.show import Show
	with Manager(willCommit=False) as mgr:
		query = """SELECT * FROM {}""".format(Show.TABLE)
		rows = mgr.connection().execute(query).fetchall()
		shows = []

		for r in rows:
			shows.append(Show.dummy().unmap(r))

		return shows

def getShow(alias):
	from helix.database.sql import Manager
	from helix.database.show import Show
	with Manager(willCommit=False) as mgr:
		query = """SELECT * FROM {} WHERE alias='{}'""".format(Show.TABLE, alias)
		row = mgr.connection().execute(query).fetchone()

		if row and row[0]:
			return Show.dummy().unmap(row)

		return None

class Element(DatabaseObject):

	"""Represents the leaves of the Show-->Shot hierarchy. This are the individual assets that
	artists work on and will be published and moved around.

	Attributes:
	    CAMERA (str): A camera object - probably published as an FBX
	    CHARACTER (str): A character in a shot - This includes the rig and model
	    COMP (str): A composite (Nuke)
	    EFFECT (str): An FX setup - i.e. simulations
	    PROP (str): A prop
	    SET (str): A set, the environment a particular shot is set in. Can also be the layout element.
	    LIGHT (str): A light or collection of lights (light rig)
	    TEXTURE (str): An image representing a texture
	    PLATE (str): An image/image sequence (footage)
	    ELEMENT_TYPES (TYPE): A list of all the aforementioned types. Holds what kind of elements can be retrieved
	    	from lookup tables.
	"""

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

	def toTuple(self):
		eid = None
		name = self.get('name')
		elType = self.get('type')
		author = self.get('author')
		date = datetime.datetime.strptime(self.get('creation'), env.DATE_FORMAT)
		show = 'test'
		parent = self.get('parent')
		sequence = None
		shot = None

		if parent:
			s, sh = parent.split('/')
			if s:
				sequence = int(s)

			if sh:
				shot = int(sh)

		pubVersion = self.get('pubVersion', 0)
		version = self.get('version', 1)

		return (eid, name, elType, author, date, show, sequence, shot, pubVersion, version)

	def getWorkFile(self, path=None):
		wf = WorkFile(path=path, element=self)
		workFile = self.get('workFile', wf)

		self.set('workFile', workFile)

		return workFile

	def getPublishedVersions(self):
		versionInfo = self.get('versionInfo', {})

		return versionInfo.values()

	def getFileName(self, sequence=False): # TODO: determine format for publish file name
		"""Gets the file name of the element - that is the filename that the system will look for
		in the work directory when publishing.

		Currently, this is just the name of the element followed by its specified extension.

		Args:
			sequence (bool, optional): By default, returns the standard file name. If true, returns
				the sequence version of the file name, with frame padding included between the base
				name and the extension

		Returns:
		    str: The filename of the element
		"""
		if sequence:
			return '{}.{}.{}'.format(self.get('name'), '[0-9]' * env.FRAME_PADDING, self.get('ext'))

		return '{}.{}'.format(self.get('name'), self.get('ext'))

	def getVersionedFileName(self, versionNum=None, frameNum=None):
		"""Given a version number, returns the formatted filename including the version number.

		Args:
		    versionNum (int, optional): The version number to format with. By default uses the element's
		    	current version (which happens to be the next version to publish).

		    	The version that the artist is working on in the work directory is always 1 ahead of whatever
		    	is published in the release directory (since they are working on a new version)
		    frameNum (int, optional): By default, returns the standard file name. If a number is provided, the
		    	name will be formatted with the appropriate frame padding

		Returns:
		    str: The formatted string including the given version number
		"""
		baseName, ext = os.path.splitext(self.getFileName())
		version = self.get('version') if not versionNum else versionNum

		return '{baseName}{frameNum}.{version}{ext}'.format(
				baseName=baseName,
				frameNum='.' + str(frameNum).zfill(env.FRAME_PADDING) if frameNum is not None else '',
				version='v{}'.format(str(version).zfill(env.VERSION_PADDING)),
				ext=ext
			)

	def clone(self, container):
		el = container.getElement(self.get('type'), self.get('name'))

		if el:
			raise DatabaseError('Element already cloned at the given location')

		el = Element(data=self._data)

		container.addElement(el)
		el.setParent(container)

		return el

	def makeOverride(self, seq, shot=None):
		"""Given a particular database.Sequence and database.Shot, creates an override for this
		element by updating the overrides list and adding the element to the respective sequence/shot.

		If shot is omitted, the override is only created for the sequence

		Args:
			seq (database.Sequence): The sequence to make the override for
			shot (database.Shot, optional): The shot in the given sequence to make the override for. By
				default, will make the override for just the sequence given.

		Returns:
			bool: If override creation was successful
		"""
		if shot:
			self.translateTable()

			if shot.addElement(Element(data=self._data)):
				overrides = self.get('overrides', [])

				overrides.append('{}/{}'.format(seq.get('num'), shot.get('num')))
				self.set('overrides', overrides)
				return True
			else:
				raise DatabaseError()
		elif seq:
			# Only sequence specified
			self.translateTable()

			if seq.addElement(Element(data=self._data)):
				overrides = self.get('overrides', [])

				overrides.append('{}/{}'.format(seq.get('num'), -1))
				self.set('overrides', overrides)
				return True
			else:
				return False
		else:
			# No sequence specified
			raise ValueError('Invalid sequence specified')

	def getOverrides(self):
		"""Gets all the overrides of this element

		Returns:
			tuple: A tuple of the overrides, the first item is a list of database.Sequence, where
				sequence-level overrides of this element occur, the second is a list of database.Shot,
				where shot-level overrides of this element occur
		"""
		seqOverrides = []
		shotOverrides = []

		for o in self.get('overrides', []):
			seq, shot = o.split('/')

			if int(shot) == -1:
				# Only a sequence override
				seqOverrides.append(env.show.getSequence(seq))
			else:
				shotOverrides.append(env.show.getShot(seq, shot)[1])

		return (seqOverrides, shotOverrides)

	def isMoreRecent(self, date):
		"""Given a particular date, determines if this element's currently published version is
		time stamped after the date.

		Args:
		    date (str): Date to compare against. Should be formatted as %m/%d/%y i.e. 02/20/18
		"""

		date = datetime.datetime.strptime(date, '%m/%d/%y')
		pubVersionNum = self.get('pubVersion')
		pubDate = self.get('versionInfo')[pubVersionNum].split('/')[1]
		pubDate = datetime.datetime.strptime(pubDate, env.DATE_FORMAT)

		return pubDate >= date

	def getDiskLocation(self, workDir=True):
		"""Gets the on disk location of where this element's files are stored. If workDir is False,
		then the release directory path is returned. By default, the work directory path is returned.

		Args:
		    workDir (bool, optional): Whether or not to retrieve the work directory path of the element.
		    	By default, is the work directory.

		Returns:
		    str: The directory location of this element (either work or release depending on workDir)
		"""
		baseDir = env.getEnvironment('work') if workDir else env.getEnvironment('release')
		show = env.show
		name = self.get('name')

		# For special reserved element names, we don't create the additional subdirectory.
		# This is so that we can have specific elements that are "overridden" for a shot that will
		# be the only one of its kind in the directory, so it is less confusing overall for the end
		# user. This is pretty hack at the moment and I'd like to revisit a new solution
		nameDir = '' if name.startswith('__sq') else name
		parent = self.get('parent', '')

		if parent:
			seq, shot = parent.split('/')
			s, sh = env.show.getShot(seq, shot)

			if seq and shot:
				return os.path.join(baseDir, show.get('dirName'), s.getDirectoryName(), sh.getDirectoryName(), self.get('type'), nameDir)
			elif seq:
				return os.path.join(baseDir, show.get('dirName'), s.getDirectoryName(), self.get('type'), nameDir)

		return os.path.join(baseDir, show.get('dirName'), self.get('type'), nameDir)

	def setParent(self, container):
		if isinstance(container, Show):
			self.set('parent', '')
		elif isinstance(container, Sequence):
			self.set('parent', '{}/'.format(container.get('num')))
		elif isinstance(container, Shot):
			self.set('parent', '{}/{}'.format(container.get('seq'), container.get('num')))

	def getCreation(self):
		"""Returns the element's creation timestamp as a datetime object

		Returns:
		    datetime: The datetime object representing this element's creation timestamp
		"""
		creation = self.get('creation')
		dt = datetime.datetime.strptime(creation, env.DATE_FORMAT)

		return dt

	def getContainer(self):
		parent = self.get('parent', '')

		if parent:
			seq, shot = parent.split('/')
			s, sh = env.show.getShot(seq, shot)

			if seq and shot:
				return (s, sh)
			elif seq:
				return s

		return env.show

	def diff(self, other, path=[]):
		diffs = DiffSet()

		if type(self) != type(other):
			raise ValueError('Can only perform diff between objects of the same type')

		path.append(self.get('name'))

		for key, val in self._data.iteritems():
			otherVal = other._data.get(key)

			if isinstance(val, list) and isinstance(otherVal, list):
				path.append(key)

				valTuple, otherValTuple = zip(*list(itertools.izip_longest(val, otherVal, fillvalue=None)))

				for v, ov in zip(valTuple, otherValTuple):
					if v != ov:
						diffs.add(path, valTuple.index(v), val, otherVal, v, ov)

				path.pop()
			else:
				if isinstance(otherVal, unicode):
					otherVal = str(otherVal)
				if isinstance(val, unicode):
					val = str(val)
				if otherVal != val:
					diffs.add(path, key, self._data, other._data, val, otherVal)

		for key, val in other._data.iteritems():
			if key not in self._data:
				diffs.add(path, key, self._data, other._data, None, val)

		path.pop()

		return diffs

	@staticmethod
	def factory(elType, name):
		"""Constructs an element with the given type and name. Creation info is tagged onto
		this element: time and user.

		Args:
		    elType (str): The element type to make (i.e. "prop", "character")
		    name (str): The name of the element to make

		Returns:
		    database.Element: The constructed element

		Raises:
		    ValueError: If the given element type does not exist
		"""
		element = None

		if elType == Element.SET:
			element = Set()
		elif elType == Element.LIGHT:
			element = Light()
		elif elType == Element.CHARACTER:
			element = Character()
		elif elType == Element.PROP:
			element = Prop()
		elif elType == Element.EFFECT:
			element = Effect()
		elif elType == Element.COMP:
			element = Comp()
		elif elType == Element.CAMERA:
			element = Camera()
		elif elType == Element.PLATE:
			element = Plate()
		else:
			raise ValueError('Invalid element type specified')

		user, time = env.getCreationInfo()

		element.set('name', name)
		element.set('type', elType)
		element.set('author', user)
		element.set('creation', time)
		element.set('version', 1)

		return element

	def __repr__(self):
		return '{} ({})'.format(self.get('name', 'undefined'), self.get('type'))

class Set(Element):
	pass

class Light(Element):
	pass

class Character(Element):
	pass

class Prop(Element):
	pass

class Effect(Element):
	pass

class Comp(Element):
	pass

class Camera(Element):
	pass

class Plate(Element):
	pass