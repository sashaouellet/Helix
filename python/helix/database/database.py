"""This module outlines all the different types of database objects that are stored to and from disk. Currently,
this is only implemented for a JSON implementation but should be easy to extend beyond that. The show object is the
parent of all other items and stores sequences. Sequences house shots which hold the individual elements that make up
that particular shot, i.e. Camera, FX, props, etc.

__author__  = Sasha Ouellet (sashaouellet@gmail.com)
__version__ = 1.0.0
__date__    = 02/18/18
"""
import json
import os, sys, shutil, glob, datetime, copy, re, itertools
import helix.environment.environment as env
import helix.utils.fileutils as fileutils
from helix.utils.diff import DiffSet, STATE_ADD

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
		self._diffToResolve = None

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
			self._origData = copy.deepcopy(self._data) # Keep for saving purposes later

			db.close()

		self._makeTables()

	def __del__(self):
		self.save()

		super(Database, self).__del__()

	def _makeTables(self):
		"""The default "data" table contains simply a list of shows, this
		function translates that table into a convenience lookup table keying
		each show's name to the database.
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

		Returns:
			bool: Whether the show was successfully added or not
		"""
		showName = show.get('name')

		if showName not in self._showTable or force:
			self._showTable[showName] = show
		else:
			raise DatabaseError('Show {} already exists in database'.format(showName))

	def removeShow(self, showName, clean=False):
		"""Removes the show with the given name from the database, if it exists.

		Args:
		    showName (str): The name of the show to remove
		    clean (bool, optional): Whether or not to remove the files associated with this show from disk

		Returns:
		    database.Show: The removed show (if it existed), otherwise None
		"""
		show = self._showTable.pop(showName, None)

		if show and clean:
			work = os.path.join(env.getEnvironment('work'), show.get('dirName'))
			release = os.path.join(env.getEnvironment('release'), show.get('dirName'))

			if os.path.exists(work):
				shutil.rmtree(work)

			if os.path.exists(release):
				shutil.rmtree(release)

		return show

	def save(self):
		"""Saves the database to the JSON file at the path specified by Database._dbPath. Prior
		to saving, the convenience name-->object lookup table to shows is translated back to the
		standard data table.
		"""
		print 'Saving DB...'
		result = True
		self._translateTables()

		hasConflicts, ondiskDiffs, localDiffs, latestDiffs = self._hasMergeConflicts()

		if hasConflicts:
			for diff in ondiskDiffs.diffSet:
				localDiff = diff.getFromSet(localDiffs) # Represents the diff between the originally read-in data and the current in-memory data
				latestDiff = diff.getFromSet(latestDiffs) # Represents the diff between the current on-disk data and the current in-memory data

				if localDiff:
					# A change on disk (not by current user) was also made in the local changes by the user
					resp = None

					if not latestDiff:
						print 'Diff found in original data is not found in the current data'
						continue

					if not ERROR_BUBBLING:
						while resp not in ('y', 'n'):
							print 'Conflicting changes: {}'.format(diff)
							print 'Discard local changes? Specifying no (n) will overwrite the changes with your local ones. (y/n) ',
							resp = sys.stdin.readline().lower().strip()

						latestDiff.resolve(discard=resp=='y')

						if resp == 'y':
							result = False
					else:
						self._diffToResolve = latestDiff
						raise MergeConflictError('Conflicting changes: {}'.format(diff))
				else:
					# A change made on disk that we didn't make locally, so we should be able to safely resolve by keeping the latest on disk
					latestDiff.resolve(True)

		with open(self._dbPath, 'w+') as f:
			self._translateTables()
			json.dump(DatabaseObject.encode(self._data), f, sort_keys=True, indent=4, separators=(',', ': '))

			self._origData = copy.deepcopy(self._data)

		print 'Done saving'
		return result

	def _hasMergeConflicts(self):
		"""Checks to see if the current version of the on-disk database has received
		changes that would conflict with any modifications the user has made with the in-memory
		database.

		Returns:
		    database.Show: The removed show (if it existed), otherwise None
		"""
		if not os.path.exists(self._dbPath):
			db = open(self._dbPath, 'w+')
		else:
			db = open(self._dbPath, 'r+')

		ondiskData = DatabaseObject.decode(json.load(db))

		db.close()

		ondiskDiffs = DiffSet()
		localDiffs = DiffSet()
		latestDiffs = DiffSet()
		path = []
		selfShowTable = {}
		origShowTable = {}
		ondiskShowTable = {}
		selfShows = self._data.get('shows', [])
		origShows = self._origData.get('shows', [])
		ondiskShows = ondiskData.get('shows', [])

		for show in selfShows:
			name = show.get('name').lower()

			selfShowTable[name] = show

		for show in origShows:
			name = show.get('name').lower()

			origShowTable[name] = show

		for show in ondiskShows:
			name = show.get('name').lower()

			ondiskShowTable[name] = show

		origShow, ondiskShow = zip(*list(itertools.izip_longest(origShowTable.keys(), ondiskShowTable.keys(), fillvalue=None)))
		origShow, selfShow = zip(*list(itertools.izip_longest(origShowTable.keys(), selfShowTable.keys(), fillvalue=None)))

		# Comparing originally read-in data to the current on-disk data to see if any changes have been made since we last saved/loaded
		for show, oShow in zip(origShow, ondiskShow):
			if show:
				if show not in ondiskShowTable.keys():
					ondiskDiffs.add(path, 'shows', origShowTable, ondiskShowTable, show, None)
				else:
					path.append('shows')
					ondiskDiffs.merge(origShowTable.get(show).diff(ondiskShowTable.get(show), path))
					path.pop()

			if oShow:
				if oShow not in origShowTable.keys():
					ondiskDiffs.add(path, 'shows', origShowTable, ondiskShowTable, None, oShow)

		# Also compare original read-in data to our current local data to see what changes the user has made.
		for show, oShow in zip(origShow, selfShow):
			if show:
				if show not in selfShowTable.keys():
					localDiffs.add(path, 'shows', origShowTable, selfShowTable, show, None)
				else:
					path.append('shows')
					localDiffs.merge(origShowTable.get(show).diff(selfShowTable.get(show), path))
					path.pop()

			if oShow:
				if oShow not in origShowTable.keys():
					localDiffs.add(path, 'shows', origShowTable, selfShowTable, None, oShow)

		# Also compare newest on-disk to our in-memory data (for rollback purposes when we have conflicts)
		for show, oShow in zip(ondiskShow, selfShow):
			if show:
				if show not in selfShowTable.keys():
					latestDiffs.add(path, 'shows', ondiskShowTable, selfShowTable, show, None)
				else:
					path.append('shows')
					latestDiffs.merge(ondiskShowTable.get(show).diff(selfShowTable.get(show), path))
					path.pop()

			if oShow:
				if oShow not in ondiskShowTable.keys():
					latestDiffs.add(path, 'shows', ondiskShowTable, selfShowTable, None, oShow)

		if ondiskDiffs.diffSet:
			# Had some changes
			return (True, ondiskDiffs, localDiffs, latestDiffs)
		else:
			# Can go through with our local changes since nothing was changed on disk
			return (False, ondiskDiffs, localDiffs, latestDiffs)

class HelixException(BaseException):
	pass

class DatabaseError(HelixException):
	"""Defines an error that took place with certain database operations. This custom error
	is necessary for certain try statements so that we do not preemptively quit while the user
	is operating on elements, shots, etc.
	"""
	pass

class MergeConflictError(HelixException):
	"""Represents an error that occurs during attempting the save the Database object. Any conflicting changes
	with what is on disk vs. in memory will raise this error.
	"""
	pass

class PublishError(HelixException):
	"""Represents an error that occurs during publishing, i.e. the publish file not being found
	"""
	pass

class DatabaseObject(object):

	"""The DatabaseObject represents any individual piece of the database that will be saved to disk.
	The DatabaseObject is responsible for encoding and decoding itself to/from the JSON format.

	Each class inheriting DatabaseObject will have their class name stored under the key "_DBOType" in order
	for decoding operations to be simplified. This allows for a particular JSON object on disk to be easily
	indentified and then properly constructed given the rest of its data structure.
	"""

	def __init__(self, *args, **kwargs):
		data = kwargs.pop('data', {})
		self._data = copy.deepcopy(data)
		self._data['_DBOType'] = self._data.get('_DBOType', self.__class__.__name__)

		for key, val in kwargs.iteritems():
			self._data[key] = val

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

	def __eq__(self, other):
		if isinstance(other, self.__class__):
			return self.__dict__ == other.__dict__
		else:
			return False

	def __ne__(self, other):
		if isinstance(other, self.__class__):
			return self.__dict__ != other.__dict__
		else:
			return True

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

			classLookup = {'Show':Show, 'Sequence':Sequence, 'Shot':Shot, 'Set':Set, 'Character':Character, 'Prop':Prop, 'Effect':Effect, 'Comp':Comp, 'Camera':Camera, 'Plate':Plate, 'WorkFile':WorkFile}
			obj = classLookup.get(clazz)

			if obj:
				return obj(data=DatabaseObject.decode(data))
			else:
				raise ValueError('Invalid type to decode: {}'.format(clazz))

class ElementContainer(DatabaseObject):

	"""Represents a particular part of a show (or the show itself) that is parent to any number of elements.

	ElementContainers should be able to translate their data dict into the expected _elementTable dict which
	keys element types and names to their respective elements for faster lookups. Additionally, the inverse
	translation should also take place via overloading DatabaseObject.translateTable()
	"""

	def __init__(self, *args, **kwargs):
		super(ElementContainer, self).__init__(*args, **kwargs)

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
		"""Translates the element table back into the standard data dict for JSON encoding
		"""
		if not self._data.get('elements'):
			self._data['elements'] = {}

		# Convert the element lookup table into the standard data dictionary to be stored on disk.
		for elType, nameDict in self._elementTable.iteritems():
			self._data['elements'][elType] = nameDict.values()

	def addElement(self, el, force=False, makeDirs=True):
		"""Adds the given element to the element table.

		Args:
		    el (database.Element): The element to add
		    force (bool, optional): By default, if the given element of this specific type/name already
		    	exists in the table, it will not be overridden. If set to True, it will be overridden.
		    makeDirs (bool, optional): By default, adding an element to the container will create the
				appropriate on disk folders to house it. Set to False to skip the creation.

		Returns:
			bool: Whether or not the element was successfully added. The addition will fail if the element
				already exists and force was not set to True
		"""
		name = el.get('name')
		elType = el.get('type')

		if name not in self._elementTable.get(elType, {}) or force:
			elTypeDict = self._elementTable.get(elType, {})
			elTypeDict[name] = el

			self._elementTable[elType] = elTypeDict

			if makeDirs:
				diskLoc = el.getDiskLocation()

				if not os.path.exists(diskLoc):
					os.makedirs(diskLoc)
		else:
			raise DatabaseError('Element {} ({}) already exists in database'.format(name, elType))

	def getElement(self, elementType, elementName):
		"""Gets the specified element type and name from this container.

		Args:
		    elementType (str): The type that this element to retrieve is (i.e. "prop", "character")
		    elementName (str): The element's name to retrieve

		Returns:
		    database.Element: The element of the given type and name

		Raises:
		    DatabaseError: If the given elementType does not match any known element type.
		"""

		if elementType not in Element.ELEMENT_TYPES:
			raise DatabaseError('Element type specified ({}) does not exist. Must be one of: {}'.format(elementType, ', '.join(Element.ELEMENT_TYPES)))

		return self._elementTable[elementType].get(elementName)

	def getElements(self, types=None):
		"""Gets all elements in this shot

		Args:
			types (str | list, optional): The type(s) of elements to retrieve. By default, returns all elements

		Returns:
		    list: All the elements in the shot
		"""
		elDicts = self._elementTable.values()

		if types:
			elDicts = []

			for t in types:
				elDicts.append(self._elementTable[t])

		if isinstance(types, str):
			types = [types]

		return [el for nested in elDicts for el in nested.values()]

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

	def destroyElement(self, elType, name, clean=False):
		"""Removes the element of the given type and name from the element table

		Args:
		    elType (str): The type of the element to remove (i.e. "prop", "character")
		    name (str): The name of the element to remove
		"""
		if not self._elementTable[elType].get(name):
			print 'Element {} doesn\'t exist'.format(name)
			raise DatabaseError

		el = self._elementTable[elType].pop(name)

		if clean:
			workDir = el.getDiskLocation(workDir=True)
			relDir = el.getDiskLocation(workDir=False)

			if os.path.exists(workDir):
				shutil.rmtree(workDir)

			if os.path.exists(relDir):
				shutil.rmtree(relDir)

	def diff(self, other, path=[]):
		diffs = DiffSet()

		path.append('elements')

		for elType, elDict in self._elementTable.iteritems():
			path.append(elType)

			otherElDict = other._elementTable.get(elType)

			if not elDict.keys() and not otherElDict.keys():
				path.pop()
				continue

			selfEl, otherEl = zip(*list(itertools.izip_longest(elDict.keys(), otherElDict.keys(), fillvalue=None)))

			for el, oEl in zip(selfEl, otherEl):
				if el:
					if el not in otherElDict.keys():
						diffs.add(path, el, elDict, otherElDict, elDict.get(el), None)
					else:
						diffs.merge(elDict.get(el).diff(otherElDict.get(el), path))

				if oEl and oEl not in elDict.keys():
					diffs.add(path, oEl, elDict, otherElDict, None, otherElDict.get(oEl))

			path.pop()

		path.pop()

		return diffs

class Show(ElementContainer):

	"""Represent a show, which houses a collection of database.Sequence as well as other show-specific parameters

	The Show data table is converted into a sequence number-->sequence convenience table in order for faster sequence
	lookups.
	"""

	def __init__(self, *args, **kwargs):
		super(Show, self).__init__(*args, **kwargs)

		self._seqTable = {}
		seqs = self._data.get('sequences', [])

		for seq in seqs:
			num = int(seq.get('num'))

			self._seqTable[num] = seq

	def translateTable(self):
		"""Translates the lookup tables back into the standard data table so that it can be encoded to JSON
		"""
		self._data['sequences'] = self._seqTable.values()

		super(Show, self).translateTable()

	def getDiskLocation(self, workDir=True):
		baseDir = env.getEnvironment('work') if workDir else env.getEnvironment('release')
		showDir = self.get('dirName')

		return os.path.join(baseDir, showDir)

	def addSequence(self, seq, force=False):
		"""Adds the given database.Sequence to the sequence table.

		Args:
		    seq (database.Sequence): The sequence to add
		    force (bool, optional): By default, an existing sequence will not be overridden. If force is True,
		    	an existing sequence will be replaced by the given one.

		Returns:
			bool: Whether the sequence was successfully added or not
		"""
		num = seq.get('num')

		if num not in self._seqTable or force:
			self._seqTable[num] = seq
		else:
			raise DatabaseError('Sequence {} already exists in database'.format(num))

	def removeSequence(self, seqNum, clean=False):
		"""Removes the sequence with the given number from this show, if it exists.

		Args:
		    seqNum (int | str): The number of the sequence to remove
		    clean (bool, optional): Whether or not to remove the files associated with this show from disk

		Returns:
		    database.Sequence: The removed sequence (if it existed), otherwise None
		"""
		work = self.getSequenceDir(seqNum)
		release = self.getSequenceDir(seqNum, work=False)
		seq = self._seqTable.pop(int(seqNum), None)

		if seq and clean:
			if os.path.exists(work):
				shutil.rmtree(work)

			if os.path.exists(release):
				shutil.rmtree(release)

		return seq

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
			return self._seqTable[int(num)]
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
		    tuple: A tuple of the sequence with the given number and the shot with the given number
		"""
		seq = self.getSequence(seqNum)
		shot = seq.getShot(shotNum) if shotNum else None

		return (seq, shot)

	def getAllElements(self, elFilter=None):
		els = self.getElements()

		for seq in self.getSequences():
			els.extend(seq.getElements())

			for shot in seq.getShots():
				els.extend(shot.getElements())

		if elFilter:
			els = [e for e in els if elFilter(e)]

		return els

	def getElement(self, elementType, elementName, seqNum=None, shotNum=None):
		"""Gets the specified element type and name from the show. If a sequence and/or shot number are specified,
		will attempt to retrieve the overridden element from that sequence/shot (if it exists). If no override is found,
		will just return the show-level element.

		Args:
		    elementType (str): The type that this element to retrieve is (i.e. "prop", "character")
		    elementName (str): The element's name to retrieve
		    seqNum (int, optional): The sequence number to get the specified element from. By default assumes the global (show-level) element
		    shotNum (int, optional): The shot number to retrieve the specified element from. By default assumes the global (show-level) element

		Returns:
		    database.Element: The element that matches all the given parameters

		Raises:
		    DatabaseError: If the given elementType does not match any known element type.
		"""

		if elementType not in Element.ELEMENT_TYPES:
			print 'Element type specified ({}) does not exist'.format(elementType)
			print 'Must be one of: {}'.format(', '.join(Element.ELEMENT_TYPES))
			raise DatabaseError

		showElement = self._elementTable[elementType].get(elementName)

		if seqNum and shotNum:
			try:
				_, shot = self.getShot(seqNum, shotNum)
				shotEl = shot.getElement(elementType, elementName)

				if shotEl:
					return shotEl
				else:
					print 'No such element in sequence {} shot {}'.format(seqNum, shotNum)
					print 'Defaulting to show-level element'
					return showElement
			except DatabaseError:
				print 'Defaulting to show-level element'
				return showElement
		elif seqNum:
			try:
				seq = self.getSequence(seqNum)
				seqEl = seq.getElement(elementType, elementName)

				if seqEl:
					return seqEl
				else:
					print 'No such element in sequence {}'.format(seqNum)
					print 'Defaulting to show-level element'
					return showElement
			except DatabaseError:
				print 'Defaulting to show-level element'
				return showElement

		return showElement

	def getSafeName(self):
		"""Constructs the "safe name" for this show, based on its actual name. The safe name
		is free of special characters and spaces so that directories can be safely made using it.

		Returns:
		    str: The transformed name
		"""
		return fileutils.sanitize(fileutils.convertToCamelCase(self.get('name')))

	def getSequenceDir(self, seqNum, work=True):
		baseDir = env.getEnvironment('work') if work else env.getEnvironment('release')
		seq = self.getSequence(seqNum)

		return os.path.join(baseDir, self.get('dirName'), seq.getDirectoryName())

	def getShotDir(self, seqNum, shotNum, work=True):
		baseDir = env.getEnvironment('work') if work else env.getEnvironment('release')
		seq, shot = self.getShot(seqNum, shotNum)

		return os.path.join(baseDir, self.get('dirName'), seq.getDirectoryName(), shot.getDirectoryName())

	def diff(self, other, path=[]):
		diffs = DiffSet()

		if type(self) != type(other):
			raise ValueError('Can only perform diff between objects of the same type')

		self.translateTable()
		other.translateTable()

		path.append(self.get('name'))

		# First check our data dict keys to see if they:
		# 1. Exist in "other"'s data dict
		# 2. Match in value to "other"
		for key, val in self._data.iteritems():
			if key in ('sequences', 'elements'): # Skip for now
				continue

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

		# Do the same for other dict, but ignore keys that exist in
		# the current data dict since we already added those differences
		# in the last iteration. We just want keys in "other" that don't exist
		# anymore in the current data dict.
		for key, val in other._data.iteritems():
			if key in ('sequences', 'elements'): # Skip for now
				continue

			if key not in self._data:
				diffs.add(path, key, self._data, other._data, None, val)

		if self._seqTable.keys() or other._seqTable.keys():
			selfSeq, otherSeq = zip(*list(itertools.izip_longest(self._seqTable.keys(), other._seqTable.keys(), fillvalue=None)))

			for seq, oSeq in zip(selfSeq, otherSeq):
				path.append('sequences')

				if seq:
					if seq not in other._seqTable.keys():
						diffs.add(path, seq, self._seqTable, other._seqTable, self._seqTable.get(seq), None)
					else:
						diffs.merge(self._seqTable.get(seq).diff(other._seqTable.get(seq), path))
				if oSeq:
					if oSeq not in self._seqTable.keys():
						diffs.add(path, oSeq, self._seqTable, other._seqTable, None, other._seqTable.get(oSeq))
					else:
						pass
						#diffs.merge(self._seqTable.get(seq).diff(other._seqTable.get(seq)))

				path.pop()

		diffs.merge(ElementContainer.diff(self, other, path))

		path.pop()

		return diffs

	def __repr__(self):
		return '{} ({})'.format(self.get('name', 'undefined'), ', '.join(self.get('aliases', [])))

class Sequence(ElementContainer):

	"""Represents a collection of shots. Shots are stored in a lookup table keying their number to the actual
	shot object.
	"""

	def __init__(self, *args, **kwargs):
		super(Sequence, self).__init__(*args, **kwargs)

		self._shotTable = {}
		shots = self._data.get('shots', [])

		for shot in shots:
			num = int(shot.get('num'))

			self._shotTable[num] = shot

	def translateTable(self):
		"""Translate the shot table back into the standard data dict.
		"""
		self._data['shots'] = self._shotTable.values()

		super(Sequence, self).translateTable()

	def addShot(self, shot, force=False):
		"""Adds the given shot to this sequence. If it already exists, then the shot will not be added
		unless force is set to True.

		Args:
		    shot (database.Shot): The shot to add to this sequence
		    force (bool, optional): By default, if the shot exists, it will not be overridden, but if set
		    	to True, the given shot will take the place of the existing one.

		Returns:
			bool: Whether the shot was successfully added or not
		"""
		num = shot.get('num')

		if num not in self._shotTable or force:
			self._shotTable[num] = shot
		else:
			raise DatabaseError('Shot {} already exists in database'.format(num))

	def removeShot(self, shotNum, clean=False):
		"""Removes the shot with the given number from this sequence, if it exists.

		Args:
		    shotNum (int | str): The number of the shot to remove
		    clean (bool, optional): Whether or not to remove the files associated with this shot from disk

		Returns:
		    database.Shot: The remove shot, or None if it didn't exist
		"""
		work = env.show.getShotDir(self.get('num', 0), shotNum)
		release = env.show.getShotDir(self.get('num', 0), shotNum, work=False)
		shot = self._shotTable.pop(int(shotNum), None)

		if shot and clean:
			if os.path.exists(work):
				shutil.rmtree(work)

			if os.path.exists(release):
				shutil.rmtree(release)

		return shot

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
			return self._shotTable[int(num)]
		except KeyError:
			print 'Shot {} does not exist for sequence {}'.format(num, self.get('num'))
			raise DatabaseError

	def getShots(self):
		"""Gets a list of all the shots in this sequence

		Returns:
		    list: All the shots
		"""
		return self._shotTable.values()

	def getDiskLocation(self, workDir=True):
		baseDir = env.getEnvironment('work') if workDir else env.getEnvironment('release')
		showDir = env.show.get('dirName')

		return os.path.join(baseDir, showDir, self.getDirectoryName())

	def getDirectoryName(self):
		return fileutils.SEQUENCE_FORMAT.format(str(self.get('num', 0)).zfill(env.SEQUENCE_SHOT_PADDING))

	def diff(self, other, path=[]):
		diffs = DiffSet()

		if type(self) != type(other):
			raise ValueError('Can only perform diff between objects of the same type')

		self.translateTable()
		other.translateTable()

		path.append(self.get('num'))

		for key, val in self._data.iteritems():
			if key in ('shots', 'elements'): # Skip for now
				continue

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

		# Do the same for other dict, but ignore keys that exist in
		# the current data dict since we already added those differences
		# in the last iteration. We just want keys in "other" that don't exist
		# anymore in the current data dict.
		for key, val in other._data.iteritems():
			if key in ('shots', 'elements'): # Skip for now
				continue

			if key not in self._data:
				diffs.add(path, key, self._data, other._data, None, val)

		if self._shotTable.keys() or other._shotTable.keys():
			selfShot, otherShot = zip(*list(itertools.izip_longest(self._shotTable.keys(), other._shotTable.keys(), fillvalue=None)))

			for shot, oShot in zip(selfShot, otherShot):
				path.append('shots')

				if shot:
					if shot not in other._shotTable.keys():
						diffs.add(path, shot, self._shotTable, other._shotTable, self._shotTable.get(shot), None)
					else:
						diffs.merge(self._shotTable.get(shot).diff(other._shotTable.get(shot), path))
				if oShot:
					if oShot not in self._shotTable.keys():
						diffs.add(path, oShot, self._shotTable, other._shotTable, None, other._shotTable.get(shot))

				path.pop()

		diffs.merge(ElementContainer.diff(self, other, path))
		path.pop()

		return diffs

	def __repr__(self):
		return 'Sequence {}'.format(self.get('num', -1))

class Shot(ElementContainer):

	"""Represents a collection of different types of Elements, including a particular Camera. Elements are
	stored in a nested dictionary keyed by their type and name. To retrieve a partocular element from the
	table, the type dictionary must be retrieved, and then the actual element by its name.
	"""

	def __init__(self, *args, **kwargs):
		super(Shot, self).__init__(*args, **kwargs)

	def translateTable(self):
		super(Shot, self).translateTable()

	def getDiskLocation(self, workDir=True):
		seq = env.show.getSequence(self.get('seq'))
		seqDir = seq.getDiskLocation(workDir)

		return os.path.join(seqDir, self.getDirectoryName())

	def getDirectoryName(self):
		ret = fileutils.SHOT_FORMAT.format(str(self.get('num', 0)).zfill(env.SEQUENCE_SHOT_PADDING))

		if self.get('clipName'):
			ret += '_' + self.get('clipName')

		return ret

	def diff(self, other, path=[]):
		diffs = DiffSet()

		if type(self) != type(other):
			raise ValueError('Can only perform diff between objects of the same type')

		self.translateTable()
		other.translateTable()

		path.append(self.get('num'))

		for key, val in self._data.iteritems():
			if key in ('elements'): # Skip for now
				continue

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

		# Do the same for other dict, but ignore keys that exist in
		# the current data dict since we already added those differences
		# in the last iteration. We just want keys in "other" that don't exist
		# anymore in the current data dict.
		for key, val in other._data.iteritems():
			if key in ('elements'): # Skip for now
				continue

			if key not in self._data:
				diffs.add(path, key, self._data, other._data, None, val)

		diffs.merge(ElementContainer.diff(self, other, path))
		path.pop()

		return diffs

	def __repr__(self):
		return 'Shot {} ({})'.format(self.get('num', -1), self.get('clipName'))

class WorkFile(DatabaseObject):
	FILE_TYPES = {'nuke': 'nk', 'maya': 'ma', 'houdini': 'hipnc'}

	def __init__(self, *args, **kwargs):
		super(WorkFile, self).__init__(*args, **kwargs)

		elType = kwargs.get('elType')

		self.set('version', self.getVersionNumberFromName())

		if not self.get('type') and elType:
			self.set('type', self.getFileTypeForType(elType))

		if not self.get('path'):
			self.set('path', os.path.join(self.get('root'), self.get('name')))

	def getVersionNumberFromName(self):
		match = re.match(r'[\._]v*(\d+)\..+$', self.get('name'))

		if match:
			return int(match.group(1))

		return 1

	def getFileTypeForType(self, elType):
		if elType in ('nuke', 'camera'):
			return WorkFile.FILE_TYPES['nuke']
		elif elType in ('prop', 'set', 'character'):
			return WorkFile.FILE_TYPES['maya']
		elif elType in ('effect'):
			return WorkFile.FILE_TYPES['houdini']

		return ''

	def exists(self):
		return os.path.exists(fileutils.expand(self.get('path')))

	def getVersions(self):
		import OrderedDict

		baseDir = os.path.join(fileutils.expand(self.get('root')))

		if not os.path.exists(baseDir):
			os.makedirs(baseDir)

		files = os.listdir(baseDir)
		versions = {}

		for f in files:
			match = re.match(r'^({})[\._]v*(\d+)\..+$'.format(self.get('name')), f)

			if match:
				ver = int(match.group(2))
				filesForVer = versions.get(ver, [])

				filesForVer.append(os.path.join(baseDir, f))

				versions[ver] = filesForVer

		return OrderedDict(sorted(versions.items(), key=lambda t: t[0]))

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
	    TEXTURE (str): An image representing a texture
	    PLATE (str): An image/image sequence (footage)
	    ELEMENT_TYPES (TYPE): A list of all the aforementioned types. Holds what can of elements can be retrieved
	    	from lookup tables.
	"""

	SET = 'set'
	CHARACTER = 'character'
	PROP = 'prop'
	TEXTURE = 'texture'
	EFFECT = 'effect'
	COMP = 'nuke'
	CAMERA = 'camera'
	PLATE = 'plate'
	ELEMENT_TYPES = [SET, CHARACTER, PROP, TEXTURE, EFFECT, COMP, CAMERA, PLATE]

	def getWorkFile(self):
		elType = self.get('type')
		wf = WorkFile(name=self.get('name'), elType=self.get('type'), root=fileutils.makeRelative(self.getDiskLocation(), 'work'))
		workFile = self.get('workFile', wf)

		self.set('workFile', workFile)

		return workFile

	def getPublishedVersions(self):
		versionInfo = self.get('versionInfo', {})
		versionSplit = [[version] + info.split('/') for version, info in versionInfo.iteritems()] # Gives us [[verNum1, user1, timestamp1], ...]

		return versionSplit

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
		sequence = self.get('seq', 'False') == 'True'
		baseName, ext = os.path.splitext(self.getFileName(sequence=sequence))
		currVersion = self.get('pubVersion', -1)
		currVersionFile = os.path.join(versionsDir, self.getVersionedFileName(versionNum=currVersion))
		prevVersion = int(currVersion) - 1 if not version else version

		if prevVersion < 1:
			raise PublishError('Cannot rollback prior to version 1. Current version found: {}'.format(currVersion))

		if sequence:
			prevVersionFile = os.path.join(versionsDir, '{}.v{}{}'.format(baseName, str(prevVersion).zfill(env.VERSION_PADDING), ext))
			prevSeq = glob.glob(prevVersionFile)

			if not prevSeq:
				raise PublishError('Rollback failed. Rollback version files are missing: {}'.format(prevVersionFile))

			for file in prevSeq:
				fileName = os.path.split(file)[1]
				match = re.match(r'^(.+)\.(\d+)\..+$', fileName)

				if match:
					versionlessFile = os.path.join(relDir, '{}.{}{}'.format(match.group(1), match.group(2), ext))

					print 'Updating link: {}'.format(versionlessFile), '-->', file

					if os.path.exists(versionlessFile):
						os.remove(versionlessFile)

					os.link(file, versionlessFile)

			self.set('pubVersion', prevVersion)
		else:
			prevVersionFile = os.path.join(versionsDir, self.getVersionedFileName(versionNum=prevVersion))

			if not os.path.exists(prevVersionFile):
				raise PublishError('Rollback failed. Rollback version file is missing: {}'.format(prevVersionFile))

			versionlessFile = os.path.join(relDir, '{}{}'.format(baseName, ext))

			print 'Updating link: {}'.format(versionlessFile), '-->', prevVersionFile

			if os.path.exists(versionlessFile):
				os.remove(versionlessFile)

			os.link(prevVersionFile, versionlessFile)
			self.set('pubVersion', prevVersion)

		return prevVersion

	def versionUp(self):
		"""Publishes the current element to the next version, copying the proper file(s) to the
		release directory and updating the versionless file to link to this new version.

		Versions are tagged in the element data with the creator and creation date for rollback purposes.

		"pubVersion" reflects what version the versionless file points to, regardless of whether it is the
		latest version or not. When a publish is executed, this is obviously updated to the version that
		was just published.

		Returns:
		    bool: Whether the publish action succeeded or not.
		"""
		workDir = self.getDiskLocation()
		relDir = self.getDiskLocation(workDir=False)
		versionsDir = os.path.join(relDir, '.versions')

		if not self.get('ext'):
			raise PublishError('Please set the expected extension first using "mod ext VALUE"')

		if not os.path.exists(versionsDir):
			os.makedirs(versionsDir)

		fileName = self.getFileName()
		workDirCopy = os.path.join(workDir, fileName)
		version = self.get('version')
		sequence = self.get('seq', False) == True

		print 'Publishing: {} (Sequence={})'.format(workDirCopy, sequence)

		if sequence:
			workDirCopy = os.path.join(workDir, self.getFileName(sequence=True))
			seq = glob.glob(workDirCopy)

			if not seq:
				raise PublishError('Could not find the expected sequence: {}'.format(os.path.join(workDir, '{}.{}.{}'.format(self.get('name'), '#' * env.FRAME_PADDING, self.get('ext')))))

			pubVersion = -1

			for file in seq:
				fileName = os.path.split(file)[1]
				match = re.match(r'^.+\.(\d+)\..+$', fileName)

				if match:
					pubVersion = self.publishFile(fileName, version=version, frameNum=int(match.group(1)))

			return pubVersion

		else:
			return self.publishFile(fileName)

	def publishFile(self, fileName, version=None, frameNum=None):
		"""Given a file name of the work directory file to publish to "release", copies
		the file to the release directory's versions folder and sets up the proper hard link.

		Args:
		    fileName (str): The current existing file to publish to the release directory
		    version (int, optional): The explicit version number to publish to
		    frameNum (int, optional): The frame number of the file to publish

		Returns:
		    int: The new version number that was just published
		"""
		workDir = self.getDiskLocation()
		relDir = self.getDiskLocation(workDir=False)
		versionsDir = os.path.join(relDir, '.versions')
		workDirCopy = os.path.join(workDir, fileName)

		if not os.path.exists(workDirCopy):
			# Artist hasn't made a file that matches what we expect to publish
			raise PublishError('Could not find the expected file: {}'.format(fileName))

		baseName, ext = os.path.splitext(fileName)
		versionedFileName = self.getVersionedFileName(versionNum=version, frameNum=frameNum)
		versionDest = os.path.join(versionsDir, versionedFileName)
		versionlessFile = os.path.join(relDir, fileName)

		shutil.copy(workDirCopy, versionDest)

		if os.path.exists(versionlessFile):
			os.remove(versionlessFile)

		os.link(versionDest, versionlessFile)

		# TODO: make versionless and versionDest read-only?

		#from stat import S_IREAD, S_IRGRP, S_SIROTH
		#os.chmod(versionDest, S_IREAD|S_IRGRP|S_SIROTH)
		#os.chmod(versionlessFile, S_IREAD|S_IRGRP|S_SIROTH)

		version = self.get('version') if not version else version
		versionInfo = self.get('versionInfo', {})
		versionInfo[int(version) + 1] = '{}/{}'.format(*env.getCreationInfo()) # Timestamp and user info for publish

		self.set('version', int(version) + 1)
		self.set('versionInfo', versionInfo)

		self.set('pubVersion', int(version))

		return self.get('pubVersion')

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
		ext = env.cfg.config.get('Elements', 'default_ext_' + elType) if env.cfg.config.has_option('Elements', 'default_ext_' + elType) else ''

		element.set('name', name)
		element.set('ext', ext)
		element.set('type', elType)
		element.set('author', user)
		element.set('creation', time)
		element.set('version', 1)

		if elType == 'plate':
			element.set('seq', True)
		else:
			element.set('seq', False)

		return element

	def __repr__(self):
		return '{} ({})'.format(self.get('name', 'undefined'), self.get('type'))

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

class Plate(Element):
	pass