import sys, os, shlex, shutil, getpass, traceback
import argparse
import helix.environment.environment as env
import helix.database.database as db
from helix.database.show import Show
from helix.database.sequence import Sequence
from helix.database.shot import Shot
from helix.database.element import Element
from helix.api.exceptions import *
from helix.environment.permissions import PermissionHandler
import helix.utils.fileutils as fileutils

dbLoc = env.getEnvironment('db')

if not dbLoc:
	raise KeyError('Database location not set in your environment')

perms = PermissionHandler()

# User commands
def mkshow(alias, name=None):
	perms.check('helix.create.show')

	if Show(alias, name=name, makeDirs=True).insert():
		print 'Successfully created new show'
		return True
	else:
		raise DatabaseError('Failed to create show. Does this alias already exist?')

def rmshow(showName, clean=False):
	perms.check('helix.delete.show')

	show = db.removeShow(showName, clean)

	if not show:
		raise DatabaseError('Didn\'t recognize show: {}'.format(showName))


	print 'Successfully removed show'

def mkseq(seqNum):
	perms.check('helix.create.sequence')

	if Sequence(seqNum, makeDirs=True).insert():
		print 'Successfully created sequence {}'.format(seqNum)
		return True
	else:
		raise DatabaseError('Failed to create sequence. Does this number already exist?')

def rmseq(seqNum, clean=False):
	perms.check('helix.delete.sequence')

	seq = env.getShow().removeSequence(int(seqNum), clean)

	if not seq:
		raise DatabaseError('Sequence {} doesn\'t exist'.format(seqNum))


	print 'Successfully removed sequence'

def mkshot(seqNum, shotNum, start=0, end=0, clipName=None):
	perms.check('helix.create.shot')

	if Shot(shotNum, seqNum, start=start, end=end, clipName=clipName, makeDirs=True).insert():
		print 'Successfully created shot {}'.format(shotNum)
		return True
	else:
		raise DatabaseError('Failed to create shot. Does this number already exist?')

def rmshot(seqNum, shotNum, clean=False):
	perms.check('helix.delete.shot')

	seq = env.getShow().getSequence(seqNum)
	shot = seq.removeShot(int(shotNum), clean)

	if not shot:
		raise DatabaseError('Shot {} doesn\'t exist for sequence {}'.format(shotNum, seqNum))


	print 'Successfully removed shot'

def pop(showName):
	perms.check('helix.pop')

	show = db.getShow(showName)

	if not show:
		raise DatabaseError('Didn\'t recognize show: {}'.format(showName))

	env.setEnvironment('show', show.alias)

	print 'Set environment for {}'.format(show.alias)

def mke(elType, name, sequence=None, shot=None, clipName=None):
	perms.check('helix.create.element')

	if name == '-':
		name = None

	el = Element(name, elType, sequence=sequence, shot=shot, clipName=clipName, makeDirs=True)

	if el.insert():
		print 'Successfully created element {}'.format(el)
		return True
	else:
		raise DatabaseError('Failed to create element. Does it already exist?')

def get(elType, name=None, sequence=None, shot=None):
	perms.check('helix.get')

	if name == '-':
		name = None

	element = Element(name, elType, show=env.getShow(), sequence=sequence, shot=shot)

	if not element:
		raise DatabaseError('Element doesn\'t exist (Check for typos in the name, or make a new element)')

	env.setEnvironment('element', element.id)

	print 'Working on {}'.format(element)

# Element-context commands
def pub(file, range=(), force=False):
	perms.check('helix.publish')
	env.getWorkingElement().versionUp(file, range=range, ignoreMissing=force)

	print 'Published version: {}'.format(env.getWorkingElement().pubVersion)

def roll(version=None):
	perms.check('helix.rollback')

	element = env.getWorkingElement()
	newVersion = element.rollback(version=version)

	if newVersion:

		print 'Rolled back published file to version: {}'.format(newVersion)

def mod(attribute, value=None):
	element = env.getWorkingElement()

	if value:
		perms.check('helix.mod.set')
		element.set(attribute, value)

		print 'Set {} to {}'.format(attribute, value)
	else:
		perms.check('helix.mod.get')
		print element.get(attribute)

def importEl(dir, elType, name=None, sequence=None, shot=None, clipName=None, overwriteOption=0):
	"""Imports the files in the given directory into an element's work directory. This element
	either already exists (based on name/elType/sequence/shot) or a new one will be made with
	the given parameters.

	Args:
	    dir (str): Path to the directory to import files from into the element
	    name (str): The name of the element to import to/create.
	    elType (str): The element type of the element to import to/create.
	    sequence (int, optional): The sequence number of the element to import to/create. Defaults
	    	to a show-level element.
	    shot (int, optional): The shot number of the element to import to/create. Defaults to a
	    	show-level element.
	    clipName (str, optional): The clip name of the specified shot number where the element will
	    	imported to/created in.
	    overwriteOption (int, optional): The action to take when encountering files of the same name
	    	that already exist when importing into an already existing element.

	    	0: DEFAULT. Duplicate files will be overwritten by the incoming source.
	    	1: Version up. Incoming source files will be appended with a number.
	    	2: Skip. Incoming source files will not be imported if they are duplicates.

	Raises:
	    ImportError: If the specified directory does not exist or is not a directory.
	"""
	perms.check('helix.import.element')

	if not os.path.isdir(dir):
		raise ImportError('Not a directory: {}'.format(dir))

	el = Element(name, elType, show=env.getEnvironment('show'), sequence=sequence, shot=shot, clipName=clipName, makeDirs=True)

	if not el.exists():
		el.insert()

	fileutils.relativeCopyTree(dir, el.work_path, overwriteOption)

def export(dir, show, elType, name=None, sequence=None, shot=None, clipName=None, work=False, release=False):
	perms.check('helix.export.element')

	if not os.path.isdir(dir):
		raise ValueError('Not a directory: {}'.format(dir))

	el = Element(name, elType, show=show, sequence=sequence, shot=shot, clipName=clipName)

	if not el.exists():
		raise ValueError('Given element does not exist')

	date = str(env.getCreationInfo(format=False)[1].date())

	if work:
		finalDest = os.path.join(dir, 'work_' + el._rawId + '_' + date)

		if not os.path.exists(finalDest):
			os.makedirs(finalDest)

		fileutils.relativeCopyTree(el.work_path, finalDest)

	if release:
		finalDest = os.path.join(dir, 'release_' + el._rawId + '_' + date)

		if not os.path.exists(finalDest):
			os.makedirs(finalDest)

		fileutils.relativeCopyTree(el.release_path, finalDest)

def clone(show=None, sequence=None, shot=None):
	# TODO: consider an option for also cloning the work and/or release dirs of the element
	perms.check('helix.clone')
	show = env.getShow() if not show else db.getShow(show)
	container = None

	if not show:
		raise DatabaseError('Invalid show specified: {}'.format(show))

	if sequence and shot:
		_, container = show.getShot(sequence, shot)
	elif sequence:
		container = show.getSequence(sequence)
	elif not sequence and not shot:
		container = show
	else:
		raise HelixException('If specifying a shot to clone into, the sequence number must also be provided.')

	cloned = env.getWorkingElement().clone(container)

	os.path.makedirs(cloned.getDiskLocation())

def override(sequence=None, shot=None):
	perms.check('helix.override')
	if sequence and shot:
		seq, s = env.getShow().getShot(sequence, shot)

		if env.getWorkingElement().makeOverride(seq, s):
			print 'Created override for sequence {} shot {}'.format(sequence, shot)
		else:
			print 'Override creation failed'
	elif sequence:
		seq = env.getShow().getSequence(sequence)

		if env.getWorkingElement().makeOverride(seq):
			print 'Created override for sequence {}'.format(sequence)
		else:
			print 'Override creation failed'
	else:
		# User is looking for overrides of the current element
		overrides = env.getWorkingElement().getOverrides()

		print 'Sequence overrides:'

		if overrides[0]:
			print '\n'.join([str(s) for s in overrides[0]])
		else:
			print 'None'

		print 'Shot overrides:'

		if overrides[1]:
			print '\n'.join([str(s) for s in overrides[1]])
		else:
			print 'None'

def createFile(path=None):
	if not path:
		perms.check('helix.workfile.get')
		wf = env.getWorkingElement().getWorkFile('')
		# User trying to retrieve the work file
	else:
		perms.check('helix.workfile.create')
		if not os.path.exists(path):
			raise HelixException('Cannot create work file from path: {} (File does not exist)'.format(path))

		wf = env.getWorkingElement().getWorkFile(path)


def shows():
	perms.check('helix.view.show')
	print '\n'.join([str(s) for s in db.getShows()])

def sequences():
	perms.check('helix.view.sequence')
	print '\n'.join([str(s) for s in sorted(env.getShow().getSequences(), key=lambda x: x.get('num'))])

def shots(seqNum):
	perms.check('helix.view.shot')
	seq = env.getShow().getSequence(seqNum)

	print '\n'.join([str(s) for s in sorted(seq.getShots(), key=lambda x: x.get('num'))])

def elements(elType=None, sequence=None, shot=None, date=None):
	perms.check('helix.view.element')
	if elType:
		elType = elType.split(',')

	container = env.getShow()

	if sequence and shot:
		_, container = env.getShow().getShot(sequence, shot)
	elif sequence:
		container = env.getShow().getSequence(sequence)

	els = container.getElements(types=elType)

	if isinstance(container, Show):
		for sequence in container.getSequences():
			els.extend(sequence.getElements(types=elType))

			for shot in sequence.getShots():
				els.extend(shot.getElements(types=elType))

	if date:
		els = [e for e in els if e.isMoreRecent(date)]

	# TODO sort by pubVersion

	print '\n'.join([str(el) for el in els])

def rme(elType, name, sequence=None, shot=None, clean=False):
	perms.check('helix.delete.element')
	container = env.getShow() # Where to get element from

	if sequence and shot:
		_, container = env.getShow().getShot(sequence, shot)
	elif sequence:
		container = env.getShow().getSequence(sequence)

	element = container.getElement(elType.lower(), name) # TODO sanitize name

	container.destroyElement(elType, name, clean)

	print 'Successfully removed element {}'.format(element)

# Debug and dev commands
def dump(expanded=False):
	perms.check('helix.dump')
	if expanded:
		print DatabaseObject.encode(db._data)
	else:
		print db._data

def getenv():
	perms.check('helix.getenv')
	print env.getAllEnv()

def main(cmd, argv):
	if cmd == 'pop':
		parser = HelixArgumentParser(prog='pop', description='Pop into a specific show')

		parser.add_argument('showName', help='The 4-5 letter code for the show name')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		return pop(**args)
	elif cmd == 'mkshow':
		parser = HelixArgumentParser(prog='mkshow', description='Make a new show')

		parser.add_argument('alias', help='The alias of the show. Has character restrictions (i.e. no spaces or special characters)')
		parser.add_argument('--name', '-n', help='The full name of the show. Please surround with double quotes (").')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		return mkshow(**args)
	elif cmd == 'rmshow':
		parser = HelixArgumentParser(prog='rmshow', description='Delete an existing show. Optionally also remove associated files from disk.')

		parser.add_argument('showName', help='The name of the show. Surround in quotes for multi-word names.')
		parser.add_argument('--clean', '-c', action='store_true', help='Remove associated files/directories for this show')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}
		showName = args['showName']

		print 'You are about to delete the show: {}. {}Are you sure you want to proceed? (y/n) '.format(showName, 'All files on disk associated with the show will also be deleted. ' if clean else ''),

		resp = sys.stdin.readline().strip().lower()

		if resp in ('y', 'yes'):
			return rmshow(**args)
	elif cmd == 'mkseq':
		if not env.getEnvironment('show'):
			print 'Please pop into a show first'
			return

		parser = HelixArgumentParser(prog='mkseq', description='Make a new sequence in the current show')

		parser.add_argument('seqNum', help='The number of the sequence')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		return mkseq(**args)
	elif cmd == 'rmseq':
		if not env.getEnvironment('show'):
			print 'Please pop into a show first'
			return

		parser = HelixArgumentParser(prog='rmseq', description='Remove an existing sequence from the current show')

		parser.add_argument('seqNum', help='The number of the sequence')
		parser.add_argument('--clean', '-c', action='store_true', help='Remove associated files/directories for this sequence')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		return rmseq(**args)
	elif cmd == 'mkshot':
		if not env.getEnvironment('show'):
			print 'Please pop into a show first'
			return

		parser = HelixArgumentParser(prog='mkshot', description='Make a new shot in the current show for the given sequence.')

		parser.add_argument('seqNum', help='The number of the sequence to make the shot in')
		parser.add_argument('shotNum', help='The number of the shot to make')
		parser.add_argument('--start', '-s', default=0, help='Start frame of the shot')
		parser.add_argument('--end', '-e', default=0, help='End frame of the shot')
		parser.add_argument('--clipName', '-c', default=None, help='The name of the clip associated with this shot')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		return mkshot(**args)
	elif cmd == 'rmshot':
		if not env.getEnvironment('show'):
			print 'Please pop into a show first'
			return

		parser = HelixArgumentParser(prog='rmshot', description='Remove an existing shot in the current show for the given sequence.')

		parser.add_argument('seqNum', help='The number of the sequence to remove the shot from')
		parser.add_argument('shotNum', help='The number of the shot to remove')
		parser.add_argument('--clean', '-c', action='store_true', help='Remove associated files/directories for this shot')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		return rmshot(**args)
	elif cmd == 'mke':
		# Command is irrelevant without the show context set
		if not env.getEnvironment('show'):
			print 'Please pop into a show first'
			return

		parser = HelixArgumentParser(prog='mke', description='Make an element (Set, Character, Prop, Effect, etc.)')

		parser.add_argument('elType', help='The type of element (Set, Character, Prop, Effect, etc.) to make')
		parser.add_argument('name', help='The name of the element that will be made (i.e. Table). Specify "-" to indicate no name (but sequence and shot must be specified)')
		parser.add_argument('--sequence', '-sq', default=None, help='The sequence number')
		parser.add_argument('--shot', '-s', default=None, help='The shot number')
		parser.add_argument('--clipName', '-c', default=None, help='The clip name of the shot')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		return mke(**args)
	elif cmd == 'clone':
		if not env.getEnvironment('element'):
			print 'Please get an element to work on first'
			return

		parser.add_argument('--show', default=None, help='The show to clone into. If not provided, clones into the current environment\'s show.')
		parser.add_argument('--sequence', '-sq', default=None, help='The sequence number to clone into. If not provided, will clone into the current show or the show provided.')
		parser.add_argument('--shot', '-s', default=None, help='The shot number to clone into. If not provided, will clone into the sequence (if provided), otherwise the show.')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		return clone(**args)
	elif cmd == 'rme':
		if not env.getEnvironment('show'):
			print 'Please pop into a show first'
			return

		parser = HelixArgumentParser(prog='rme', description='Remove an exisiting element')

		parser.add_argument('elType', help='The type of element')
		parser.add_argument('name', help='The name of the element')
		parser.add_argument('--sequence', '-sq', default=None, help='The sequence number')
		parser.add_argument('--shot', '-s', default=None, help='The shot number')
		parser.add_argument('--clean', '-c', action='store_true', help='Remove associated files/directories for this element')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		return rme(**args)
	elif cmd == 'get':
		# Command is irrelevant without the show context set
		if not env.getEnvironment('show'):
			print 'Please pop into a show first'
			return

		parser = HelixArgumentParser(prog='get', description='Get an already existing element to work on')

		parser.add_argument('elType', help='The type of element')
		parser.add_argument('name', help='The name of the element')
		parser.add_argument('--sequence', '-sq', default=None, help='The sequence number')
		parser.add_argument('--shot', '-s', default=None, help='The shot number')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		return get(**args)
	elif cmd == 'pub':
		# Cannot publish if element hasn't been retrieved to work on yet
		if not env.getEnvironment('element'):
			print 'Please get an element to work on first'
			return

		parser = HelixArgumentParser(prog='pub', description='Publish a new version of the current working element')

		parser.add_argument('file', help='The path to the file OR frame from a sequence OR directory to publish')
		parser.add_argument('--range', '-r', type=int, nargs='+', default=None, help='The number range to publish a given frame sequence with. By default will attempt to publish the largest range found.')
		parser.add_argument('--force', '-f', action='store_true', help='By default, frame sequences will not publish if any frames are missing within the range (specified or found). Use this flag to force the publish to occur anyway.')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		if 'range' in args:
			if len(args['range']) == 1:
				args['range'] = (args['range'], args['range'])
			else:
				args['range'] = (args['range'][0], args['range'][1])

		return pub(**args)
	elif cmd == 'roll':
		if not env.getEnvironment('element'):
			print 'Please get an element to work on first'
			return

		parser = HelixArgumentParser(prog='roll', description='Rolls back the current element\'s published file to the previous version, or a specific one if specified.')

		parser.add_argument('--version', '-v', default=None, help='Specify a specific version to rollback to.')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		return roll(**args)
	elif cmd == 'mod':
		if not env.getEnvironment('element'):
			print 'Please get an element to work on first'
			return

		parser = HelixArgumentParser(prog='mod', description='Modify attributes regarding the current working element')

		parser.add_argument('attribute', help='The name of the attribute you are trying to modify (i.e. ext if you wish to change the expected extension this element produces')
		parser.add_argument('value', nargs='?', default=None, help='The value to set the given attribute to. Can be omitted to retrieve the current value instead')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		return mod(**args)
	elif cmd == 'override':
		if not env.getEnvironment('element'):
			print 'Please get an element to work on first'
			return

		parser = HelixArgumentParser(prog='override', description='Override the current element for work in a different sequence or shot. If both sequence and shot are omitted, prints the current overrides instead. By omitting shot, the element can be overridden for a sequence in general.')

		parser.add_argument('--sequence', '-sq', default=None, help='The sequence number to override the element into')
		parser.add_argument('--shot', '-s', default=None, help='The shot number to override the element into.')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		return override(**args)
	elif cmd == 'file':
		if not env.getEnvironment('element'):
			print 'Please get an element to work on first'
			return

		parser = HelixArgumentParser(prog='file', description='Assigns the given file path to be this element\'s work file.')

		parser.add_argument('path', nargs='?', default=None, help='The path to the file that should become the work file for this element')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		return createFile(**args)
	elif cmd == 'import':
		if not env.getEnvironment('show'):
			print 'Please pop into a show first'
			return

		parser = HelixArgumentParser(prog='import', description='Imports a directory to become a new element if it doesn\'t exist, or into an existing element.')

		parser.add_argument('dir', help='The full path to the directory of files associated with the element to import into or create.')
		parser.add_argument('elType', help='The element type of the element')
		parser.add_argument('--name', '-n', help='The name of the element', default=None, nargs='?')
		parser.add_argument('--sequence', '-sq', default=None, help='The sequence number of the element')
		parser.add_argument('--shot', '-s', default=None, help='The shot number of the element')
		parser.add_argument('--clipName', '-c', default=None, help='The clip name of the element\'s shot')
		parser.add_argument('--overwriteOption', '-o', default=0, type=int, choices=[0, 1, 2], help='When encountering duplicate files on import for an element that already exists, 0 will overwrite, 1 will version up the incoming file, and 2 will skip the file.')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		return importEl(**args)
	elif cmd == 'export':
		parser = HelixArgumentParser(prog='import', description='Imports a directory to become a new element if it doesn\'t exist, or into an existing element.')

		parser.add_argument('dir', help='The full path to the directory where the exported element should be placed.')
		parser.add_argument('show', help='The element\'s show')
		parser.add_argument('elType', default=None, help='The name of the element to export. Will be considered a nameless element if this flag is excluded.')
		parser.add_argument('--name', '-n', default=None, help='The name of the element to export. Will be considered a nameless element if this flag is excluded.')
		parser.add_argument('--sequence', '-sq', default=None, help='The sequence number of the element')
		parser.add_argument('--shot', '-s', default=None, help='The shot number of the element')
		parser.add_argument('--clipName', '-c', default=None, help='The clip name of the element\'s shot')
		parser.add_argument('--work', '-w', default=False, action='store_true', help='If included, the element\'s work tree is exported.')
		parser.add_argument('--release', '-r', default=None, action='store_true', help='If included, the element\'s release tree is exported.')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		return export(**args)
	elif cmd == 'els' or cmd == 'elements':
		if not env.getEnvironment('show'):
			print 'Please pop into a show first'
			return

		parser = HelixArgumentParser(prog='elements', description='List all elements for the current show')

		parser.add_argument('elType', help='A comma separated list of elements to filter by', default=None, nargs='?')
		parser.add_argument('--sequence', '-sq', default=None, help='The sequence number to get elements from')
		parser.add_argument('--shot', '-s', default=None, help='The shot number to get elements from')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		return elements(**args)
	elif cmd == 'shots':
		if not env.getEnvironment('show'):
			print 'Please pop into a show first'
			return

		parser = HelixArgumentParser(prog='shots', description='List all shots for the current show, given a sequence number.')

		parser.add_argument('seqNum', help='The sequence number')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		return shots(**args)
	elif cmd == 'seqs' or cmd == 'sequences':
		if not env.getEnvironment('show'):
			print 'Please pop into a show first'
			return

		parser = HelixArgumentParser(prog='sequences', description='List all sequences for the current show.')
		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		return sequences(**args)
	elif cmd == 'shows':
		parser = HelixArgumentParser(prog='shows', description='List all shows in this database')
		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		return shows(**args)
	elif cmd == 'pwe':
		element = env.getEnvironment('element')

		if not element:
			print 'Element could not be retrieved, try getting it again with "ge"'
			return

		print element
	elif cmd == 'help' or cmd == 'h' or cmd == '?':
		if not os.path.exists(env.getEnvironment('HELP')):
			print 'Helix help has not been properly configured'
			return

		with open(env.getEnvironment('HELP')) as file:
			line = file.readline()

			while line:
				print line,

				line = file.readline()

	# Debug commands
	elif cmd == 'dump':
		parser = HelixArgumentParser(prog='dump', description='Dumps the database contents to stdout')

		parser.add_argument('--expanded', '-e', action='store_true', help='Whether each DatabaseObject is fully expanded in the print out')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		return dump(**args)
	elif cmd == 'getenv':
		parser = HelixArgumentParser(prog='getenv', description='Gets the custom environment variables that have been set by the Helix system')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		return getenv(**args)
	elif cmd == 'debug':
		env.DEBUG = not env.DEBUG

		if env.DEBUG:
			print 'Enabled debug mode'
		else:
			print 'Disabled debug mode'
	elif cmd == 'exit' or cmd == 'quit':
		exit()
	else:
		print 'Unknown command: {}'.format(cmd)

class HelixArgumentParser(argparse.ArgumentParser):
	def error(self, message):
		raise CommandError(message)

	def exit(self, status=0, message=None):
		if message:
			print message

def exit():
	sys.exit(0)

def handleInput(line):
	cmds = line.split('|')

	for c in cmds:
		argv = shlex.split(c)

		if not argv:
			exit()

		cmd = argv[0]

		try:
			return main(cmd, argv[1:])
		except Exception as e:
			if env.DEBUG:
				print traceback.format_exc()
			elif env.HAS_UI and not isinstance(e, CommandError):
				from PyQt4.QtGui import QApplication
				from helix.utils.qtutils import ExceptionDialog

				ExceptionDialog(traceback.format_exc(e), str(e), parent=QApplication.instance().activeWindow()).exec_()
			else:
				print str(e)

			return False

if __name__ == '__main__':
	if len(sys.argv) > 2:
		if sys.argv[2] == '--debug':
			env.DEBUG = True
			print 'Enabled debug mode'
			if len(sys.argv) > 3:
				handleInput(' '.join(sys.argv[3:]))
		else:
			handleInput(' '.join(sys.argv[2:]))
	try:
		while True:
			print '\r{user} {show}@{element}>>> '.format(
				user=getpass.getuser(),
				show=env.getShow().alias if os.environ.get('HELIX_SHOW') else 'SHOW',
				element=env.getWorkingElement().name if os.environ.get('HELIX_ELEMENT') else 'ELEMENT'
			),
			line = sys.stdin.readline()

			handleInput(line)

	except KeyboardInterrupt:
		exit()
