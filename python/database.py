"""This module outlines all the different types of database objects that are stored to and from disk. Currently,
this is only implemented for a JSON implementation but should be easy to extend beyond that. The show object is the
parent of all other items and stores sequences. Sequences house shots which hold the individual elements that make up
that particular shot, i.e. Camera, FX, props, etc.

__author__  = Sasha Ouellet (sashaouellet@gmail.com)
__version__ = 1.0.0
__date__    = 02/18/18
"""
import json
import os, sys, shutil, glob, datetime
import environment as env
import fileutils

class Database(object):

	"""Represents a collection of shows on disk
	"""

	_instance = None

	def __new__(cls, *args, **kwargs):
		if not cls._instance:
			cls._instance = super(Database, cls).__new__(cls, *args, **kwargs)

		return cls._instance

	def __init__(self, dbPath, data=None):
		self._dbPath = dbPath
		db = None

		if data is not None:
			self._data = data
		else:
			if not os.path.exists(os.path.dirname(dbPath)):
				os.makedirs(os.path.dirname(dbPath))

			if not os.path.exists(dbPath):
				db = open(dbPath, 'w+')
			else:
				db = open(dbPath, 'r+')

			self._data = DatabaseObject.decode(json.load(db))

			db.close()

		self._makeTables()

	def __del__(self):
		self.save()

		super(Database, self).__del__()

	def _makeTables(self):
		"""The default "data" table contains simply a list of shows, this
		function translates that table into a convenience lookup table keying
		each show's name to the database.Show object
		"""
		self._showTable = {}
		shows = self._data.get('shows', [])

		for show in shows:
			name = show.get('name').lower()

			self._showTable[name] = show

	def _translateTables(self):
		"""Converts the show name-->show object table created by Database._makeTables into
		the standard data table that will be saved back to disk.
		"""
		self._data['shows'] = self._showTable.values()

	def getShow(self, name):
		"""Given the name of a show, returns the database.Show object

		Args:
		    name (str): Can either be the full name of the show, or one of the show's
		    	aliases

		Returns:
		    database.Show: The show with the given name/alias. None if no show with that
		    	name or alias was found
		"""
		name = name.lower()

		# Check trivial case of name being the full show name
		if name in self._showTable:
			return self._showTable.get(name)

		for show in self._showTable.values():
			if name in show.get('aliases'):
				return show

		return None

	def getShows(self):
		"""Gets all shows stored in this database

		Returns:
		    list: The list of all shows
		"""
		return self._showTable.values()

	def addShow(self, show, force=False):
		"""Adds a show to this database.

		Args:
		    show (database.Show): The show to add
		    force (bool, optional): By default, if the show exists it will not be added
		    	to the database. If set to true, the existing show will be overidden by
		    	the provided one.
		"""
		showName = show.get('name').lower()

		if showName not in self._showTable or force:
			self._showTable[showName] = show
		else:
			print 'Show {} already exists in database'.format(showName)

	def save(self):
		"""Saves the database to the JSON file at the path specified by Database._dbPath. Prior
		to saving, the convenience name-->object lookup table to shows is translated back to the
		standard data table.
		"""
		print 'Saving DB...'
		self._translateTables()

		with open(self._dbPath, 'w+') as f:
			json.dump(DatabaseObject.encode(self._data), f, sort_keys=True, indent=4, separators=(',', ': '))

		print 'Done saving'

class DatabaseError(KeyError):

	"""Defines an error that took place with certain database operations. This custom error
	is necessary for certain try statements so that we do not preemptively quit while the user
	is operating on elements, shots, etc.
	"""

	pass

class DatabaseObject(object):

	"""The DatabaseObject represents any individual piece of the database that will be saved to disk.
	The DatabaseObject is responsible for encoding and decoding itself to/from the JSON format.

	Each class inheriting DatabaseObject will have their class name stored under the key "_DBOType" in order
	for decoding operations to be simplified. This allows for a particular JSON object on disk to be easily
	indentified and then properly constructed given the rest of its data structure.
	"""

	def __init__(self, data=None):
		self._data = data if data is not None else {}
		self._data['_DBOType'] = self.__class__.__name__

	def set(self, key, val, checkKey=False):
		"""Sets the given key to the given value. If the key doesn't exist, and checkKey is True then
		the value will not be set. If checkKey is False, then a new key will be added with the given
		value.

		Args:
		    key (str): The key to set
		    val (str | int | bool | list | dict): The value to set the key to
		    checkKey (bool, optional): If the given key doesn't exist, setting this to True will create
		    	a new key, otherwise a DatabaseError will be raised

		Raises:
		    DatabaseError: When the given key does not already exist and checkKey is set to True
		"""
		if checkKey and key not in self._data:
			print 'Attribute {} doesn\'t exist'.format(key)
			raise DatabaseError

		self._data[key] = val

	def get(self, key, default=None):
		"""Gets the value of the given key from this object, defaulti
		to the value specified by default if the key does not exist.

		Args:
		    key (str): The key to obtain the value of
		    default (None, optional): The default value to return if the given key does not exist

		Returns:
		    any: The value of the given key
		"""
		return self._data.get(key, default)

	def translateTable(self):
		pass

	@staticmethod
	def encode(data):
		"""Given any data type (dict, list, int, even other DatabaseObjects), encodes the given data
		into a proper JSON format. This function is obviously recursive so that we are able to encode
		any depth of data type with any number of other DatabaseObjects.

		Args:
		    data (dict | list | DatabaseObject | str | int | bool): The data to encode into JSON

		Returns:
		    dict: The final encoded JSON object that represents the initial data type given
		"""
		ret = {}

		if isinstance(data, DatabaseObject):
			data.translateTable()
			return DatabaseObject.encode(data._data)
		elif isinstance(data, dict):
			for key, val in data.iteritems():
				if isinstance(val, DatabaseObject):
					ret[key] = DatabaseObject.encode(val)
				elif isinstance(val, list):
					l = []

					for v in val:
						if isinstance(v, DatabaseObject):
							l.append(DatabaseObject.encode(v))
						else:
							l.append(v)

					ret[key] = l
				elif isinstance(val, dict):
					ret[key] = DatabaseObject.encode(val)
				else:
					ret[key] = val

		return ret

	@staticmethod
	def decode(data):
		"""Given a particular JSON data type, decodes it into the appropriate DatabaseObject. Dictionaries passed into
		this function are searched for the key "_DBOType" in order to determine the class of the DatabaseObject to
		construct. The rest of the dictionary gets put in that type's data dictionary.

		Args:
		    data (dict | list | str | int | bool): The JSON data to decode

		Returns:
		    database.DatabaseObject | dict | list | str | int | bool: The decoded data

		Raises:
		    ValueError: If the given _DBOType is not found in the class lookup table
		"""
		if not isinstance(data, (dict, list)):
			return data
		elif isinstance(data, list):
			l = []

			for d in data:
				l.append(DatabaseObject.decode(d))

			return l
		elif isinstance(data, dict):
			clazz = data.pop('_DBOType', None)

			if not clazz: # Not a serialized DatabaseObject
				ret = {}

				for key, val in data.iteritems():
					ret[key] = DatabaseObject.decode(val)

				return ret

			classLookup = {'Show':Show, 'Sequence':Sequence, 'Shot':Shot, 'Set':Set, 'Character':Character, 'Prop':Prop, 'Effect':Effect, 'Comp':Comp, 'Camera':Camera}
			obj = classLookup.get(clazz)

			if obj:
				return obj(DatabaseObject.decode(data))
			else:
				raise ValueError('Invalid type to decode: {}'.format(clazz))

class Show(DatabaseObject):

	"""Represent a show, which houses a collection of database.Sequence as well as other show-specific parameters

	The Show data table is converted into a sequence number-->sequence convenience table in order for faster sequence
	lookups.
	"""

	def __init__(self, data=None, aliases=None):
		super(Show, self).__init__(data)

		self._seqTable = {}
		seqs = self._data.get('sequences', [])

		for seq in seqs:
			num = seq.get('num') # TODO: sanitize data

			self._seqTable[num] = seq

	def translateTable(self):
		"""Translates the sequence lookup table (which keys sequence number  to sequence) back into the standard
		data table so that it can be encoded to JSON
		"""
		self._data['sequences'] = self._seqTable.values()

	def addSequence(self, seq, force=False):
		"""Adds the given database.Sequence to the sequence table.

		Args:
		    seq (database.Sequence): The sequence to add
		    force (bool, optional): By default, an existing sequence will not be overridden. If force is True,
		    	an existing sequence will be replaced by the given one.
		"""
		num = seq.get('num')

		if num not in self._seqTable or force:
			self._seqTable[num] = seq
		else:
			print 'Sequence {} already exists in database'.format(num)

	def getSequence(self, num):
		"""Gets the sequence from the table from the specified sequence number.

		Args:
		    num (int): The number of the sequence to retrieve

		Returns:
		    database.Sequence: The sequence with the given number

		Raises:
		    DatabaseError: If the given sequence number does not correlate to an existing sequence in
		    	this show.
		"""
		try:
			return self._seqTable[num]
		except KeyError:
			print 'Sequence {} does not exist for {}'.format(num, self.get('name'))
			raise DatabaseError

	def getSequences(self):
		"""Gets all sequences from the sequence table

		Returns:
		    list: All the sequences this show owns
		"""
		return self._seqTable.values()

	def getShot(self, seqNum, shotNum):
		"""Convenience function for getting a specific shot from a specific sequence in this show.

		Args:
		    seqNum (int): The sequence number to get the specified shot from
		    shotNum (int): The shot number to retrieve

		Returns:
		    database.Shot: The shot with the given number in the specified sequence number
		"""
		return self.getSequence(seqNum).getShot(shotNum)

	def getElement(self, seqNum, shotNum, elementType, elementName):
		"""Convenience function for getting a specific element within a specific shot and sequence.

		Args:
		    seqNum (int): The sequence number to get the specified element from
		    shotNum (int): The shot number to retrieve the specified element from
		    elementType (str): The type that this element to retrieve is (i.e. "prop", "character")
		    elementName (str): The element's name to retrieve

		Returns:
		    database.Element: The element that matches all the given parameters

		Raises:
		    DatabaseError: If the given elementType does not match any known element type.
		"""
		seq = self.getSequence(seqNum)
		shot = seq.getShot(shotNum)

		if elementType not in Element.ELEMENT_TYPES:
			print 'Element type specified ({}) does not exist'.format(elementType)
			print 'Must be one of: {}'.format(', '.join(Element.ELEMENT_TYPES))
			raise DatabaseError

		return (seq, shot, shot.getElement(elementType, elementName))

	def __repr__(self):
		return '{} ({})'.format(self.get('name', 'undefined'), ', '.join(self.get('aliases', [])))

class Sequence(DatabaseObject):

	"""Represents a collection of shots. Shots are stored in a lookup table keying their number to the actual
	shot object.
	"""

	def __init__(self, data=None):
		super(Sequence, self).__init__(data)

		self._shotTable = {}
		shots = self._data.get('shots', [])

		for shot in shots:
			num = shot.get('num') # TODO: sanitize data

			self._shotTable[num] = shot

	def translateTable(self):
		"""Translate the shot lookup table to the sequence's data table.
		"""
		self._data['shots'] = self._shotTable.values()

	def addShot(self, shot, force=False):
		"""Adds the given shot to this sequence. If it already exists, then the shot will not be added
		unless force is set to True.

		Args:
		    shot (database.Shot): The shot to add to this sequence
		    force (bool, optional): By default, if the shot exists, it will not be overridden, but if set
		    	to True, the given shot will take the place of the existing one.
		"""
		num = shot.get('num')

		if num not in self._shotTable or force:
			self._shotTable[num] = shot
		else:
			print 'Shot {} already exists in database'.format(num)

	def getShot(self, num):
		"""Gets the shot from the shot lookup table by the given number, if it exists.

		Args:
		    num (int): The number of the shot to retrieve.

		Returns:
		    database.Shot: The shot with the given number in this sequence

		Raises:
		    DatabaseError: If the given shot number does not exist in this sequence
		"""
		try:
			return self._shotTable[num]
		except KeyError:
			print 'Shot {} does not exist for sequence {}'.format(num, self.get('num'))
			raise DatabaseError

	def getShots(self):
		"""Gets a list of all the shots in this sequence

		Returns:
		    list: All the shots
		"""
		return self._shotTable.values()

	def __repr__(self):
		return 'Sequence {}'.format(self.get('num', -1))

class Shot(DatabaseObject):

	"""Represents a collection of different types of Elements, including a particular Camera. Elements are
	stored in a nested dictionary keyed by their type and name. To retrieve a partocular element from the
	table, the type dictionary must be retrieved, and then the actual element by its name.
	"""

	def __init__(self, data=None):
		super(Shot, self).__init__(data)

		self._elementTable = {}

		# Populate element table with empty dicts for each element type
		for elType in Element.ELEMENT_TYPES:
			self._elementTable[elType] = {}

		# Get elements from shot database record, defaults to empty
		elements = self._data.get('elements', {})

		# Translate them into the element table
		for elType, elList in elements.iteritems():
			for el in elList:
				name = el.get('name') # TODO: sanitize data

				self._elementTable[elType][name] = el

	def translateTable(self):
		"""Converts the element lookup table into the standard data dictionary to be stored on disk.
		"""
		if not self._data.get('elements'):
			self._data['elements'] = {}

		for elType, nameDict in self._elementTable.iteritems():
			self._data['elements'][elType] = nameDict.values()

	def addElement(self, el, force=False):
		"""Adds the given element to the element table.

		Args:
		    el (database.Element): The element to add
		    force (bool, optional): By default, if the given element of this specific type/name already
		    	exists in the table, it will not be overridden. If set to True, it will be overridden.
		"""
		name = el.get('name')
		elType = el.get('type')

		if name not in self._elementTable[elType] or force:
			self._elementTable[elType][name] = el
		else:
			print 'Element {} ({}) already exists in database'.format(name, elType)

	def getElement(self, elType, name):
		"""Gets the element by the given type and name.

		Args:
		    elType (str): The type of the element to retrieve (i.e. "prop", "character")
		    name (str): The name of the element to retrieve

		Returns:
		    database.Element: The element of the given type and name, if it exists. Otherwise None.
		"""
		return self._elementTable[elType].get(name)

	def getElements(self): # TODO allow for retrieval of elements of a certain type
		"""Gets all elements in this shot

		Returns:
		    list: All the elements in the shot
		"""
		return [el for nested in self._elementTable.values() for el in nested.values()]

	def getElementsByType(self, elType=None):
		"""Retrieves a list of elements of the given type. If elType is not specified, all
		types are retrieved.

		Args:
		    elType (str | list | tuple, optional): The element type(s) to retrieve. By default retrieves all
		    	elements
		"""
		if isinstance(elType, str):
			elType = [elType]

		return [e for e in self.getElements() if e.get('type', '') in elType]

	def getElementsByVersion(self, version=None):
		"""Retrieves a list of elements that match the given version(s). If version is not
		specified, all elements are retrieved.

		Args:
		    version (int str | list | tuple, optional): The version(s) to retrieve. By default
		    	retrieves all elements.
		"""
		if type(version) in (str, int):
			version = [int(version)]

		return [e for e in self.getElements() if e.get('pubVersion', -1) in version]

	def destroyElement(self, elType, name):
		"""Removes the element of the given type and name from the element table

		Args:
		    elType (str): The type of the element to remove (i.e. "prop", "character")
		    name (str): The name of the element to remove
		"""
		self._elementTable[elType].pop(name)

	def __repr__(self):
		return 'Shot {}'.format(self.get('num', -1))

class Element(DatabaseObject):

	"""Represents the leaves of the Show-->Shot hierarchy. This are the individual assets that
	artists work on and will be published and moved around.

	Attributes:
	    CAMERA (str): A camera object - probably published as an FBX
	    CHARACTER (str): A character in a shot - This includes the rig and model
	    COMP (str): A composite (Nuke)
	    EFFECT (str): An FX setup - i.e. simulations
	    PROP (str): A prop
	    SET (str): A set, the environment a particular shot is set in. Includes the light rig.
	    ELEMENT_TYPES (TYPE): A list of all the aforementioned types. Holds what can of elements can be retrieved
	    	from lookup tables.
	"""

	SET = 'set'
	CHARACTER = 'character'
	PROP = 'prop'
	EFFECT = 'effect'
	COMP = 'comp'
	CAMERA = 'camera'
	ELEMENT_TYPES = [SET, CHARACTER, PROP, EFFECT, COMP, CAMERA]

	def clone(self, newShot, newSeq=None):
		"""Clones the given element to another sequence and shot. This effectively just allows
		for an element to live across multiple parts of the show without actually being duplicated.

		If newSeq is omitted, the element is assumed to reside in the same sequence it currently is in.

		Args:
			newShot (int): The shot to clone the element into.
		    newSeq (int, optional): The sequence to clone the element into. By default assumes the same
		    	sequence as the element is already in.
		"""
		seq, _ = self.get('parent').split('/')
		seq = seq if not newSeq else newSeq
		clones = self.get('clones', [])

		clones.append('{}/{}'.format(seq, newShot))

		self.set('clones', clones)

	def rmclone(self, shot, seq=None):
		"""Removes a clone of element that has been created earlier. All publishes created of this element
		that are in the corresponding clone will be removed from disk.

		Args:
			shot (int): The shot of the clone to remove
			seq (int, optional): The sequence of the clone to remove. By default, is the sequence the base
				element is already in

		Raises:
		    DatabaseError: If a clone doesn't exist in the specified sequence/shot number
		"""
		seq, _ = self.get('parent').split('/')
		seq = seq if not newSeq else newSeq
		clones = self.get('clones', [])
		clonePath = '{}/{}'.format(seq, shot)

		try:
			clones.remove(clonePath)
		except ValueError: # Specified clone in shot/seq doesn't exist
			raise DatabaseError

	def getFileName(self): # TODO: determine format for publish file name
		"""Gets the file name of the element - that is the filename that the system will look for
		in the work directory when publishing.

		Currently, this is just the name of the element followed by its specified extension.

		Returns:
		    str: The filename of the element
		"""
		return '{}.{}'.format(self.get('name'), self.get('ext'))

	def getVersionedFileName(self, versionNum=None):
		"""Given a version number, returns the formatted filename including the version number.

		Args:
		    versionNum (int, optional): The version number to format with. By default uses the element's
		    	current version (which happens to be the next version to publish).

		    	The version that the artist is working on in the work directory is always 1 ahead of whatever
		    	is published in the release directory (since they are working on a new version)

		Returns:
		    str: The formatted string including the given version number
		"""
		baseName, ext = os.path.splitext(self.getFileName())
		version = self.get('version') if not versionNum else versionNum

		return '{baseName}.{version}{ext}'.format(
				baseName=baseName,
				version='v{}'.format(str(version).zfill(env.VERSION_PADDING)),
				ext=ext
			)

	def rollback(self, version=None):
		"""Switches the current version of this file to an already existing published version.
		The on disk versionless file in the release directory has its link updated to reflect
		this change.

		If version is not specified, tries to rollback to the previous version.

		Args:
		    version (int, optional): The version to change to. If this version doesn't exist on
				disk, or is less than 1 the rollback fails.

		Returns:
		    bool: If the rollback succeeded or not.
		"""
		relDir = self.getDiskLocation(workDir=False)
		versionsDir = os.path.join(relDir, '.versions')
		baseName, ext = os.path.splitext(self.getFileName())
		currVersion = self.get('pubVersion')
		currVersionFile = os.path.join(versionsDir, self.getVersionedFileName(versionNum=currVersion))
		prevVersion = int(currVersion) - 1 if not version else version

		if prevVersion < 1:
			print 'Cannot rollback prior to version 1'
			return False

		if not os.path.exists(currVersionFile):
			print 'Current version file is missing: {}'.format(currVersionFile)
			return False

		prevVersionFile = os.path.join(versionsDir, self.getVersionedFileName(versionNum=prevVersion))

		if not os.path.exists(prevVersionFile):
			print 'Rollback failed. Previous version file is missing: {}'.format(prevVersionFile)
			return False

		versionlessFile = os.path.join(relDir, self.getFileName())

		if os.path.exists(versionlessFile):
			os.remove(versionlessFile)

		os.link(prevVersionFile, versionlessFile)
		self.set('pubVersion', prevVersion)

		# For all clones of the element, change the link to the new version
		for clone in self.get('clones'):
			seq, shot = clone.split('/')
			cloneVersion = os.path.join(self.getDiskLocation(workDir=False, seq=seq, shot=shot), fileName)

			if os.path.exists(cloneVersion):
				os.remove(cloneVersion)

			os.link(prevVersionFile, cloneVersion)

		return prevVersion

	def versionUp(self, sequence=False):
		"""Publishes the current element to the next version, copying the proper file(s) to the
		release directory and updating the versionless file to link to this new version.

		Versions are tagged in the element data with the creator and creation date for rollback purposes.

		"pubVersion" reflects what version the versionless file points to, regardless of whether it is the
		latest version or not. When a publish is executed, this is obviously updated to the version that
		was just published.

		Args:
		    sequence (bool, optional): If the element is publishing a sequence of files, then the publish
		    	will move this entire sequence over to the release directory.

		Returns:
		    bool: Whether the publish action succeeded or not.
		"""
		workDir = self.getDiskLocation()
		relDir = self.getDiskLocation(workDir=False)
		versionsDir = os.path.join(relDir, '.versions')

		if not self.get('ext'):
			print 'Please set the expected extension first using "mod ext VALUE"'
			return False

		if not os.path.exists(versionsDir):
			os.makedirs(versionsDir)

		workDirCopy = os.path.join(workDir, self.getFileName())
		version = self.get('version')

		if sequence:
			workDirCopy = os.path.join(workDir, '{}.{}.{}'.format(self.get('name'), '[0-9]' * env.FRAME_PADDING, self.get('ext')))
			seq = glob.glob(workDirCopy)

			if not seq:
				print 'Could not find the expected sequence: {}'.format(os.path.join(workDir, '{}.{}.{}'.format(self.get('name'), '#' * env.FRAME_PADDING, self.get('ext'))))
				return False
		else:
			fileName = os.path.split(workDirCopy)[1]

			if not os.path.exists(workDirCopy):
				# Artist hasn't made a file that matches what we expect to publish
				print 'Could not find the expected file: {}'.format(fileName)
				return False

			baseName, ext = os.path.splitext(fileName)
			versionedFileName = self.getVersionedFileName()
			versionDest = os.path.join(versionsDir, versionedFileName)
			versionlessFile = os.path.join(relDir, fileName)

			shutil.copy(workDirCopy, versionDest)

			if os.path.exists(versionlessFile):
				os.remove(versionlessFile)

			os.link(versionDest, versionlessFile)

			# For all clones of the element, we only create a versionless file in its respective directory
			for clone in self.get('clones'):
				seq, shot = clone.split('/')
				dir = self.getDiskLocation(workDir=False, seq=seq, shot=shot)
				cloneVersion = os.path.join(dir, fileName)

				if not os.path.exists(dir):
					os.makedirs(dir)

				if os.path.exists(cloneVersion):
					os.remove(cloneVersion)

				os.link(versionDest, cloneVersion)

			# TODO: make versionless and versionDest read-only?

			#from stat import S_IREAD, S_IRGRP, S_SIROTH
			#os.chmod(versionDest, S_IREAD|S_IRGRP|S_SIROTH)
			#os.chmod(versionlessFile, S_IREAD|S_IRGRP|S_SIROTH)

			versionInfo = self.get('versionInfo', {})
			versionInfo[version] = '{}/{}'.format(*env.getCreationInfo())

			self.set('version', int(version) + 1)
			self.set('pubVersion', int(version))
			self.set('versionInfo', versionInfo)

			return self.get('pubVersion')

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

	def getDiskLocation(self, workDir=True, seq=None, shot=None):
		"""Gets the on disk location of where this element's files are stored. If workDir is False,
		then the release directory path is returned. By default, the work directory path is returned.

		Args:
		    workDir (bool, optional): Whether or not to retrieve the work directory path of the element.
		    	By default, is the work directory.
		    seq (int, optional): By default, the element's explicitly set sequence number will be used,
				however for cloned elements this is a convenience for getting their alternate directories
			shot (int, optional): Specify a different shot number to get the disk location of this element
				from

		Returns:
		    str: The directory location of this element (either work or release depending on workDir)
		"""
		baseDir = env.getEnvironment('work') if workDir else env.getEnvironment('release')
		show = env.show
		currseq, currshot = self.get('parent').split('/')
		seq = currseq if not seq else seq
		shot = currshot if not shot else shot

		return os.path.join(baseDir, show.get('dirName'), fileutils.formatShotDir(seq, shot), self.get('type'), self.get('name'))

	@staticmethod
	def factory(seqNum, shotNum, elType, name):
		"""Constructs an element in the given sequence and shot with the given type and name. Creation info is tagged onto
		this element: time and user. "parent" is a path separating the sequence and shot and is used for fast lookup
		purposes.

		Args:
		    seqNum (int): The sequence number of the element to make
		    shotNum (int): The shot number of the element to make
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
		else:
			raise ValueError('Invalid element type specified')

		user, time = env.getCreationInfo()

		element.set('name', name)
		element.set('ext', '')
		element.set('type', elType)
		element.set('author', user)
		element.set('creation', time)
		element.set('version', 1)
		element.set('parent', '{}/{}'.format(seqNum, shotNum))

		if not os.path.exists(element.getDiskLocation()):
			os.makedirs(element.getDiskLocation())

		return element

	def __repr__(self):
		return '{} {} in sequence {} shot {}'.format(type(self).__name__.upper(), self.get('name', 'undefined'), *self.get('parent', '-1/-1').split('/'))

class Set(Element):
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
