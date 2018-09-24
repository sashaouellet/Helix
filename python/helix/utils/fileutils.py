import os, re, shutil, time
import helix.environment.environment as env
import uuid

cfg = env.getConfig()

SEQUENCE_FORMAT = 'sq{}'
SHOT_FORMAT = 's{}'

class FileLockException(Exception): pass

class FileLock(object):
	def __init__(self, file, timeout=5, keepVersions=5, tempFileDir=None):
		"""Create an exclusive write lock on the specified file

		Args:
		    file (str): Full path to the file to obtain a lock on
		    timeout (int, optional): The time, in seconds, before attempting to obtain the lock fails
		    keepVersions (int, optional): Right before exiting, we create a backup of the file
		    	in question. This specifies how many backup versions to keep. 0 indicates no backup
		    	should be performed.
		"""
		self._file = file
		self.timeout = timeout
		self.keepVersions = keepVersions
		self.uuid = str(uuid.uuid4())
		self.lockFile = self._file + '.lock'
		self.tempFile = self._file + '.' + self.uuid

		if tempFileDir is not None:
			_, f = os.path.split(self._file)
			self.tempFile = os.path.join(tempFileDir, f + '.' + self.uuid)

	def __enter__(self):
		self.open()
		return self

	def open(self):
		if not os.path.exists(self._file):
			# We should try one more time after a brief delay, the file could be
			# in the middle of being moved by another process
			time.sleep(1)
			if not os.path.exists(self._file):
				raise ValueError("File doesn't exist: {}".format(self._file))

		attempts = 10
		interval = self.timeout / float(attempts)
		curr = 0
		hasLock = False

		# Try to obtain the lock until we get it or we timeout
		while curr < self.timeout and not hasLock:
			hasLock = self.getLock()
			curr += interval

			time.sleep(interval)
			# What do we do with dead locks?

		if not hasLock:
			raise FileLockException('Unable to obtain lock on: {}'.format(self._file))
		
		#database disk image is malformed
		shutil.copy2(self._file, self.tempFile)

	def release(self):
		# Don't perform any operations if we don't have a valid lock
		try:
			if self.validLock():
				if self.keepVersions > 0:
					bumpFileVersion(self._file, self.keepVersions)

				# We've hopefully been operating on the temp file, so finalize all write
				# operations by copying it to the original path, now that we've bumped
				# the original path to version 1
				shutil.move(self.tempFile, self._file)

				os.remove(self.lockFile)
		except:
			os.remove(self.lockFile)

	def getLock(self):
		if not os.path.exists(self.lockFile):
			with open(self.lockFile, 'w+') as lock:
				lock.write(self.uuid)

			time.sleep(1)
			return self.validLock()
		else:
			return self.validLock()

	def validLock(self):
		if os.path.exists(self.lockFile):
			# A lock exists, but is it ours?
			with open(self.lockFile, 'r') as lock:
				uuid = lock.read().strip()

				if uuid != self.uuid:
					return False
				else:
					return True
		else:
			return False

	def __exit__(self, exception_type, exception_value, traceback):
		self.release()

	@property
	def file(self):
		return self.tempFile

def bumpFileVersion(file, maxVersion):
	folder, file = os.path.split(file)
	prefix, ext = os.path.splitext(file)
	regx = re.compile(r'{}(\d+){}'.format(prefix, ext))
	matches = filter(lambda x: regx.match(x), os.listdir(folder))
	matches = sorted(matches, reverse=True, key=lambda x: int(regx.match(x).group(1)))

	# Traverse versions from highest to lowest, discarding higher versions and moving up
	# the rest by 1
	for f in matches:
		version = int(regx.match(f).group(1))

		if version >= maxVersion:
			# Delete versions exceeding max version
			os.remove(os.path.join(folder, f))
		else:
			src = os.path.join(folder, f)
			dest = os.path.join(folder, '{}{}{}'.format(prefix, version + 1, ext))
			shutil.copy2(src, dest)

	# Original file goes to version 1
	src = os.path.join(folder, file)
	dest = os.path.join(folder, '{}{}{}'.format(prefix, 1, ext))
	shutil.copy2(src, dest)

def makeRelative(path, envVar):
	envValue = env.getEnvironment(envVar)

	return path.replace(envValue, '${}{}'.format(env.VAR_PREFIX, envVar.upper()))

def pathIsRelativeTo(path, dir):
	if not os.path.isdir(dir):
		raise ValueError('Can only check for relative locations against directories, {} is not a directory.'.format(dir))

	return path.startswith(dir)

def parseFilePath(filePath):
	fileName = os.path.split(filePath)[1]
	match = re.match(r'^([\w\-_]+?)([\._]?v?(\d+))\..+$', fileName)

	if match:
		_, ext = os.path.splitext(fileName)

		# (baseName without version number or ext, versionString, ext)
		return (match.group(1), match.group(3), ext)

	return (os.path.splitext(fileName)[0], '', os.path.splitext(fileName)[1])

def relativeCopyTree(src, dst, overwriteOption=0):
	working_dir = os.getcwd()
	os.chdir(src)

	for root, dirs, files in os.walk('.'):
		curdest = os.path.join(dst, root)

		for d in dirs:
			dirDest = os.path.join(curdest, d)

			if not os.path.isdir(dirDest):
				os.mkdir(dirDest)
		for f in files:
			fromfile = os.path.join(root, f)
			to = os.path.join(curdest, f)

			if os.path.exists(to):
				# Evaluate based on overwriteOption
				if overwriteOption == 0: # Overwrite
					shutil.copy2(fromfile, to)
				elif overwriteOption == 1: # Version up
					shutil.copy2(fromfile, getNextVersionOfFile(to))
				else: # Skip
					if env.DEBUG:
						print 'Skipped copying {}'.format(fromfile)
					continue
			else:
				shutil.copy2(fromfile, to)

	os.chdir(working_dir)

def linkPath(src, dest):
	if os.path.isdir(src):
		working_dir = os.getcwd()
		os.chdir(src)

		for root, dirs, files in os.walk('.'):
			curdest = os.path.join(dest, root)
			for d in dirs:
				os.mkdir(os.path.join(curdest, d))
			for f in files:
				fromfile = os.path.join(root, f)
				to = os.path.join(curdest, f)
				os.link(fromfile, to)

		os.chdir(working_dir)
	else:
		os.link(src, dest)

def getNextVersionOfFile(file, asPath=True):
	baseName, _, ext = parseFilePath(file)
	fileRegexPattern = baseName + '_?([0-9]+)' + ext
	regex = re.compile(fileRegexPattern)
	fileDir = os.path.dirname(file)
	files = filter(lambda f: regex.match(f), os.listdir(fileDir))
	vers = sorted([regex.match(f).group(1) for f in files], key=lambda f: int(f))

	num = int(vers[-1]) + 1 if vers else 1
	padding = len(vers[-1]) if vers else 3

	if not asPath:
		return (num, padding)
	else:
		baseDir, _ = os.path.split(file)

		return os.path.join(baseDir, baseName + '_' + str(num).zfill(padding) + ext)

def expand(path):
	parts = path.split(os.path.sep)
	newParts = []

	for p in parts:
		if p.startswith('$' + env.VAR_PREFIX):
			p = p.replace('$' + env.VAR_PREFIX, '')
			repl = env.getEnvironment(p)

			newParts.append(repl)
		else:
			newParts.append(p)

	return os.path.sep.join(newParts)

def copytree(src, dst, symlinks=False, ignore=None):
	"""Reimplementation that doesn't fail when the directories
	already exist.
	"""
	names = os.listdir(src)
	if ignore is not None:
		ignored_names = ignore(src, names)
	else:
		ignored_names = set()

	if not os.path.exists(dst):
		os.makedirs(dst)

	errors = []
	for name in names:
		if name in ignored_names:
			continue
		srcname = os.path.join(src, name)
		dstname = os.path.join(dst, name)
		try:
			if symlinks and os.path.islink(srcname):
				linkto = os.readlink(srcname)
				os.symlink(linkto, dstname)
			elif os.path.isdir(srcname):
				copytree(srcname, dstname, symlinks, ignore)
			else:
				shutil.copy2(srcname, dstname)
			# XXX What about devices, sockets etc.?
		except (IOError, os.error) as why:
			errors.append((srcname, dstname, str(why)))
		# catch the Error from the recursive copytree so that we can
		# continue with other files
		except shutil.Error as err:
			errors.extend(err.args[0])
	try:
		shutil.copystat(src, dst)
	except WindowsError:
		# can't copy file access times on Windows
		pass
	except OSError as why:
		errors.extend((src, dst, str(why)))
	if errors:
		raise shutil.Error(errors)

def openPathInExplorer(path):
	import platform, subprocess

	if platform.system() == 'Windows':
		os.startfile(path)
	elif platform.system() == 'Darwin':
		subprocess.Popen(['open', path])
	else:
		subprocess.Popen(['xdg-open', path])

def formatShotDir(seqNum, shotNum=None):
	if shotNum:
		return os.path.join(SEQUENCE_FORMAT.format(str(seqNum).zfill(env.SEQUENCE_SHOT_PADDING)), SHOT_FORMAT.format(str(shotNum).zfill(env.SEQUENCE_SHOT_PADDING)))

	return SEQUENCE_FORMAT.format(str(seqNum).zfill(env.SEQUENCE_SHOT_PADDING))

def getFramePadding(fileName, versioned=True):
	frameRegex = re.compile(r'(\.\d+)')
	search = frameRegex.findall(fileName)

	if search:
		if len(search) == 1 and versioned:
			# Matched number string is assumed to be the version number
			return None
		else:
			return search[-1][1:] # Return last match, stripping off the '.'

	return None

def convertToCamelCase(input, firstIsLowercase=False):
	"""Given an input string of words (separated by space), converts
	it back to camel case.
	'Foo Bar' (firstIsLowercase=False)  --> 'FooBar'
	'Foo Bar' (firstIsLowercase=True)   --> 'fooBar'
	'foo bar' (firstIsLowercase=False)  --> 'FooBar'

	Args:
		input (str): The string of words to convert
		firstIsLowercase (bool, optional): By default, title cases all words
			in the input string (i.e. 'foo bar' will become
			'FooBar' rather than 'fooBar'). If True, the first word is forced
			to become lowercase

	Returns:
		str: The camelcased string
	"""
	words = input.split()

	for i, word in enumerate(words):
		if i == 0 and firstIsLowercase:
			words[0] = words[0].lower()
		else:
			words[i] = words[i].title()

	return ''.join(words)

def sanitize(input):
	"""Given an input string, sanitizes it by removing any non-alphanumeric
	characters.

	Args:
		input (str): The string to clean

	Returns:
		str: The clean string

	Raises:
		ValueError: If the input is not a string
	"""
	if not isinstance(input, str):
		raise ValueError('Can only clean strings')

	return re.sub('[^A-Za-z0-9]+', '', input)