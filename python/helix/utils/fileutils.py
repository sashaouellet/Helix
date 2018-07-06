import os, re, shutil
import helix.environment.environment as env

cfg = env.getConfig()

SEQUENCE_FORMAT = 'sq{}'
SHOT_FORMAT = 's{}'

def makeRelative(path, envVar):
	envValue = env.getEnvironment(envVar)

	return path.replace(envValue, '${}{}'.format(env.VAR_PREFIX, envVar.upper()))

def pathIsRelativeTo(path, dir):
	if not os.path.isdir(dir):
		raise ValueError('Can only check for relative locations against directories, {} is not a directory.'.format(dir))

	return path.startswith(dir)

def parseFilePath(filePath):
	fileName = os.path.split(filePath)[1]
	match = re.match(r'^([\w\-_]+)([\._]v*(\d+))?\..+$', fileName)

	if match:
		_, ext = os.path.splitext(fileName)

		# (baseName without version number or ext, versionString, ext)
		return (match.group(1), match.group(3), ext)

	return (None, None, None)

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