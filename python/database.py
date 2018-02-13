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

	def getShows(self):
		return self._showTable.values()

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

	def set(self, key, val, checkKey=False):
		if checkKey and key not in self._data:
			print 'Attribute {} doesn\'t exist'.format(key)
			raise DatabaseError

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
		try:
			return self._seqTable[num]
		except KeyError:
			print 'Sequence {} does not exist for {}'.format(num, self.get('name'))
			raise DatabaseError

	def getSequences(self):
		return self._seqTable.values()

	def getShot(self, seqNum, shotNum):
		return self.getSequence(seqNum).getShot(shotNum)

	def getElement(self, seqNum, shotNum, elementType, elementName):
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
		try:
			return self._shotTable[num]
		except KeyError:
			print 'Shot {} does not exist for sequence {}'.format(num, self.get('num'))
			raise DatabaseError

	def getShots(self):
		return self._shotTable.values()

	def __repr__(self):
		return 'Sequence {}'.format(self.get('num', -1))

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
		for elType, elList in elements.iteritems():
			for el in elList:
				name = el.get('name') # TODO: sanitize data

				self._elementTable[elType][name] = el

	def translateTable(self):
		if not self._data.get('elements'):
			self._data['elements'] = {}

		for elType, nameDict in self._elementTable.iteritems():
			self._data['elements'][elType] = nameDict.values()

	def addElement(self, el, force=False):
		name = el.get('name')
		elType = el.get('type')

		if name not in self._elementTable[elType] or force:
			self._elementTable[elType][name] = el
		else:
			print 'Element {} ({}) already exists in database'.format(name, elType)

	def getElement(self, elType, name):
		return self._elementTable[elType].get(name)

	def getElements(self):
		return [el for nested in self._elementTable.values() for el in nested.values()]

	def destroyElement(self, elType, name):
		self._elementTable[elType].pop(name)

	def __repr__(self):
		return 'Shot {}'.format(self.get('num', -1))

class Element(DatabaseObject):
	SET = 'set'
	CHARACTER = 'character'
	PROP = 'prop'
	EFFECT = 'effect'
	COMP = 'comp'
	CAMERA = 'camera'
	ELEMENT_TYPES = [SET, CHARACTER, PROP, EFFECT, COMP, CAMERA]

	def clone(self, newSeq, newShot):
		pass

	def rollback(self):
		pass

	def versionUp(self, sequence=False):
		workDir = self.getDiskLocation()
		relDir = self.getDiskLocation(workDir=False)
		versionsDir = os.path.join(relDir, '.versions')

		if not os.path.exists(versionsDir):
			os.makedirs(versionsDir)

		workDirCopy = os.path.join(workDir, '{}.{}'.format(self.get('name'), self.get('ext'))) # TODO: determine format for publish file name
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

			# TODO: make versionless and versionDest read-only?

			#from stat import S_IREAD, S_IRGRP, S_SIROTH
			#os.chmod(versionDest, S_IREAD|S_IRGRP|S_SIROTH)
			#os.chmod(versionlessFile, S_IREAD|S_IRGRP|S_SIROTH)

			versionInfo = self.get('versionInfo', {})
			versionInfo[version] = '{}/{}'.format(*env.getCreationInfo())

			self.set('version', int(version) + 1)
			self.set('versionInfo', versionInfo)

			return True

	def getDiskLocation(self, workDir=True):
		baseDir = env.getEnvironment('work') if workDir else env.getEnvironment('release')
		show = env.show
		seq, shot = self.get('parent').split('/')

		return os.path.join(baseDir, show.get('dirName'), fileutils.formatShotDir(seq, shot), self.get('type'), self.get('name'))

	@staticmethod
	def factory(seqNum, shotNum, elType, name):
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

if __name__ == '__main__':
	dbLoc = env.getEnvironment('db')
	db = Database(dbLoc)
	env.show = db.getShow('wblock')
	e = Element.factory('100', '1', 'prop', 'foo')

	print e
