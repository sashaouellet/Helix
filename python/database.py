import json
import os, sys, shutil, glob
import environment as env
import fileutils

class Database(object):
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
		self._showTable = {}
		shows = self._data.get('shows', [])

		for show in shows:
			name = show.get('name').lower()

			self._showTable[name] = show

	def _translateTables(self):
		self._data['shows'] = self._showTable.values()

	def getShow(self, name):
		name = name.lower()

		# Check trivial case of name being the full show name
		if name in self._showTable:
			return self._showTable.get(name)

		for show in self._showTable.values():
			if name in show.get('aliases'):
				return show

		return None

	def addShow(self, show, force=False):
		showName = show.get('name').lower()

		if showName not in self._showTable or force:
			self._showTable[showName] = show
		else:
			print 'Show {} already exists in database'.format(showName)

	def save(self):
		print 'Saving DB...'
		# Might consider moving to destructor
		self._translateTables()

		with open(self._dbPath, 'w+') as f:
			json.dump(DatabaseObject.encode(self._data), f, sort_keys=True, indent=4, separators=(',', ': '))

		print 'Done saving'

	@staticmethod
	def decode(data):
		ret = {}

		for key, val in data.iteritems():
			if isinstance(val, list):
				l = []

				for v in val:
					if isinstance(v, dict):
						l.append(DatabaseObject.decode(v))
					else:
						l.append(v)

				ret[key] = l

class DatabaseError(KeyError):
	pass

class DatabaseObject(object):
	def __init__(self, data=None):
		self._data = data if data is not None else {}
		self._data['_DBOType'] = self.__class__.__name__

	def set(self, key, val):
		self._data[key] = val

	def get(self, key, default=None):
		return self._data.get(key, default)

	def translateTable(self):
		pass

	@staticmethod
	def encode(data):
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

			classLookup = {'Show':Show, 'Sequence':Sequence, 'Shot':Shot, 'Set':Set, 'Character':Character, 'Prop':Prop, 'Effect':Effect}
			obj = classLookup.get(clazz)

			if obj:
				return obj(DatabaseObject.decode(data))
			else:
				raise ValueError('Invalid type to decode: {}'.format(clazz))

	#def __repr__(self):
	#	return str(self.__dict__)

class Show(DatabaseObject):
	def __init__(self, data=None, aliases=None):
		super(Show, self).__init__(data)

		self._seqTable = {}
		seqs = self._data.get('sequences', [])

		for seq in seqs:
			num = seq.get('num') # TODO: sanitize data

			self._seqTable[num] = seq

	def translateTable(self):
		self._data['sequences'] = self._seqTable.values()

	def addSequence(self, seq, force=False):
		num = seq.get('num')

		if num not in self._seqTable or force:
			self._seqTable[num] = seq
		else:
			print 'Sequence {} already exists in database'.format(num)

	def getSequence(self, num):
		return self._seqTable.get(num)

	def getElement(self, seqNum, shotNum, elementType, elementName):
		seq = self.getSequence(seqNum)

		if not seq:
			print 'Sequence {} does not exist for {}'.format(seqNum, self.get('name'))
			raise DatabaseError

		shot = seq.getShot(shotNum)

		if not shot:
			print 'Shot {} does not exist for sequence {}'.format(shotNum, seqNum)
			raise DatabaseError

		if elementType not in Element.ELEMENT_TYPES:
			print 'Element type specified ({}) does not exist'.format(elementType)
			print 'Must be one of: {}'.format(', '.join(Element.ELEMENT_TYPES))
			raise DatabaseError

		return (seq, shot, shot.getElement(elementType, elementName))

class Sequence(DatabaseObject):
	def __init__(self, data=None):
		super(Sequence, self).__init__(data)

		self._shotTable = {}
		shots = self._data.get('shots', [])

		for shot in shots:
			num = shot.get('num') # TODO: sanitize data

			self._shotTable[num] = shot

	def translateTable(self):
		self._data['shots'] = self._shotTable.values()

	def addShot(self, shot, force=False):
		num = shot.get('num')

		if num not in self._shotTable or force:
			self._shotTable[num] = shot
		else:
			print 'Shot {} already exists in database'.format(num)

	def getShot(self, num):
		return self._shotTable.get(num)

class Shot(DatabaseObject):
	def __init__(self, data=None):
		super(Shot, self).__init__(data)

		self._elementTable = {}

		# Populate element table with empty dicts for each element type
		for elType in Element.ELEMENT_TYPES:
			self._elementTable[elType] = {}

		# Get elements from shot database record, defaults to empty
		elements = self._data.get('elements', {})

		# Translate them into the element table
		for type, elList in elements.iteritems():
			for el in elList:
				name = el.get('name') # TODO: sanitize data

				self._elementTable[type][name] = el

	def translateTable(self):
		if not self._data.get('elements'):
			self._data['elements'] = {}

		for type, nameDict in self._elementTable.iteritems():
			self._data['elements'][type] = nameDict.values()

	def addElement(self, el, force=False):
		name = el.get('name')
		type = el.get('type')

		if name not in self._elementTable[type] or force:
			self._elementTable[type][name] = el
		else:
			print 'Element {} ({}) already exists in database'.format(name, type)

	def getElement(self, type, name):
		return self._elementTable[type].get(name)

class Element(DatabaseObject):
	SET = 'set'
	CHARACTER = 'character'
	PROP = 'prop'
	EFFECT = 'effect'
	ELEMENT_TYPES = [SET, CHARACTER, PROP, EFFECT]

	def versionUp(self, sequence=False): # TODO: also implement rollback function
		workDir = self.getDiskLocation()
		relDir = self.getDiskLocation(workDir=False)
		versionsDir = os.path.join(relDir, '.versions')

		if not os.path.exists(versionsDir):
			os.makedirs(versionsDir)

		# TODO: Is 'ext' determined by project manager? Does the artist set the ext they will be handing off?

		workDirCopy = os.path.join(workDir, '{}.{}'.format(self.get('name'), self.get('ext'))) # TODO: determine format for publish file name
		version = self.get('version')

		if sequence:
			workDirCopy = os.path.join(workDir, '{}.{}.{}'.format(self.get('name'), '[0-9]' * env.FRAME_PADDING, self.get('ext')))
			seq = glob.glob(workDirCopy)

			if not seq:
				print 'Could not find the expected sequence: {}'.format(os.path.join(workDir, '{}.{}.{}'.format(self.get('name'), '#' * env.FRAME_PADDING, self.get('ext'))))
				return
		else:
			fileName = os.path.split(workDirCopy)[1]

			if not os.path.exists(workDirCopy):
				# Artist hasn't made a file that matches what we expect to publish
				print 'Could not find the expected file: {}'.format(fileName)
				return

			baseName, ext = os.path.splitext(fileName)
			versionedFileName = '{baseName}.{version}{ext}'.format(
					baseName=baseName,
					version='v{}'.format(str(version).zfill(env.VERSION_PADDING)),
					ext=ext
				)
			versionDest = os.path.join(versionsDir, versionedFileName)
			versionlessFile = os.path.join(relDir, fileName)

			shutil.copy(workDirCopy, versionDest)

			if os.path.exists(versionlessFile):
				os.remove(versionlessFile)

			os.link(versionDest, versionlessFile)

			self.set('version', version + 1)

	def getDiskLocation(self, workDir=True):
		baseDir = env.getEnvironment('work') if workDir else env.getEnvironment('release')
		show = env.show
		seq, shot = self.get('parent').split('/')

		return os.path.join(baseDir, show.get('dirName'), fileutils.formatShotDir(seq, shot), self.get('type'), self.get('name'))

	@staticmethod
	def factory(seqNum, shotNum, type, name):
		element = None

		if type == Element.SET:
			element = Set()
		elif type == Element.CHARACTER:
			element = Character()
		elif type == Element.PROP:
			element = Prop()
		elif type == Element.EFFECT:
			element = Effect()
		else:
			raise ValueError('Invalid element type specified')

		user, time = env.getCreationInfo()

		element.set('name', name)
		element.set('type', type)
		element.set('author', user)
		element.set('creation', time)
		element.set('version', 1)
		element.set('parent', '{}/{}'.format(seqNum, shotNum))

		os.makedirs(element.getDiskLocation())

		return element

class Set(Element):
	pass

class Character(Element):
	pass

class Prop(Element):
	pass

class Effect(Element):
	pass

if __name__ == '__main__':
	e = Element.factory('100', '1', 'prop', 'foo')
