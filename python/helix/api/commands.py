import sys, os, shlex
import argparse
import helix.environment.environment as env
from helix.database.database import *
from helix.environment.permissions import PermissionHandler

dbLoc = env.getEnvironment('db')

if not dbLoc:
	raise KeyError('Database location not set in your environment')

db = Database(dbLoc)
perms = PermissionHandler()

# User commands
def mkshow(showName):
	show = Show(name=showName)

	if db.addShow(show):
		print 'Successfully created new show'
		show.set('dirName', show.getSafeName())
		db.save()

def rmshow(showName, clean=False):
	show = db.removeShow(showName, clean)

	if not show:
		print 'Didn\'t recognize show: {}'.format(showName)
		return
	else:
		print 'Successfully removed show'
		db.save()

def mkseq(seqNum):
	seq = Sequence(num=int(seqNum))

	if env.show.addSequence(seq):
		print 'Successfully created sequence'
		db.save()

def rmseq(seqNum, clean=False):
	seq = env.show.removeSequence(int(seqNum), clean)

	if not seq:
		print 'Sequence {} doesn\'t exist'.format(seqNum)
		return
	else:
		print 'Successfully removed sequence'
		db.save()

def mkshot(seqNum, shotNum):
	try:
		seq = env.show.getSequence(seqNum)
		shot = Shot(seq=int(seqNum), num=int(shotNum))

		if seq.addShot(shot):
			print 'Successfully created shot'
			db.save()
	except DatabaseError:
		return

def rmshot(seqNum, shotNum, clean=False):
	try:
		seq = env.show.getSequence(seqNum)
		shot = seq.removeShot(int(shotNum), clean)

		if not shot:
			print 'Shot {} doesn\'t exist for sequence {}'.format(shotNum, seqNum)
			return
		else:
			print 'Successfully removed shot'
			db.save()
	except DatabaseError:
		return

def pop(showName):
	show = db.getShow(showName)

	if not show:
		print 'Didn\'t recognize show: {}'.format(showName)
		return

	showName = show.get('name')

	env.setEnvironment('show', showName)
	env.show = show

	print 'Set environment for {}'.format(showName)

def mke(elType, name, sequence=None, shot=None):
	try:
		container = env.show # Where to get element from

		if sequence and shot:
			_, container = env.show.getShot(sequence, shot)
		elif sequence:
			container = env.show.getSequence(sequence)

		element = container.getElement(elType.lower(), name) # TODO sanitize name

		if element:
			print 'Element already exists (did you mean to use "ge"?)'
			return

		container.addElement(Element.factory(elType.lower(), name))
		db.save()
	except DatabaseError:
		return

def get(elType, name, sequence=None, shot=None):
	try:
		element = env.show.getElement(elType.lower(), name, sequence, shot)

		if not element:
			print 'Element doesn\'t exist (Check for typos in the name, or make a new element using "mke")'
			return

		env.setEnvironment('element', element.getDiskLocation())
		env.element = element

		print 'Working on {}'.format(element)

	except DatabaseError:
		return

# Element-context commands
def pub():
	element = env.element
	newVersion = element.versionUp()

	if newVersion:
		print 'Published new version: {}'.format(newVersion)
		db.save()

def roll(version=None):
	element = env.element
	newVersion = element.rollback(version=version)

	if newVersion:
		print 'Rolled back published file to version: {}'.format(newVersion)
		db.save()

def mod(attribute, value=None):
	element = env.element

	if value:
		try:
			element.set(attribute, value, checkKey=True)
			db.save()

			print 'Set {} to {}'.format(attribute, value)
		except DatabaseError:
			return
	else:
		print element.get(attribute)

def override(sequence=None, shot=None):
	if sequence and shot:
		try:
			seq, s = env.show.getShot(sequence, shot)

			if env.element.makeOverride(seq, s):
				print 'Created override for sequence {} shot {}'.format(sequence, shot)
				db.save()
			else:
				print 'Override creation failed'
		except DatabaseError:
			return
	elif sequence:
		try:
			seq = env.show.getSequence(sequence)

			if env.element.makeOverride(seq):
				print 'Created override for sequence {}'.format(sequence)
				db.save()
			else:
				print 'Override creation failed'
		except DatabaseError:
			return
	else:
		# User is looking for overrides of the current element
		try:
			overrides = env.element.getOverrides()

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
		except DatabaseError:
			return

def shows():
	print '\n'.join([str(s) for s in db.getShows()])

def sequences():
	print '\n'.join([str(s) for s in sorted(env.show.getSequences(), key=lambda x: x.get('num'))])

def shots(seqNum):
	try:
		seq = env.show.getSequence(seqNum)

		print '\n'.join([str(s) for s in sorted(seq.getShots(), key=lambda x: x.get('num'))])
	except DatabaseError:
		return

def elements(elType=None, date=None):
	if elType:
		elType = elType.split(',')

	els = env.show.getElements(types=elType)

	if date:
		els = [e for e in els if e.isMoreRecent(date)]

	# TODO sort by pubVersion

	print '\n'.join([str(el) for el in els])

def rme(elType, name, sequence=None, shot=None):
	try:
		container = env.show # Where to get element from

		if sequence and shot:
			_, container = env.show.getShot(sequence, shot)
		elif sequence:
			container = env.show.getSequence(sequence)

		element = container.getElement(elType.lower(), name) # TODO sanitize name

		container.destroyElement(elType, name)
		db.save()
	except DatabaseError:
		return

# Debug and dev commands
def dump(expanded=False):
	if expanded:
		print DatabaseObject.encode(db._data)
	else:
		print db._data

def getenv():
	print env.getAllEnv()

def main(cmd, argv):
	if cmd == 'pop':
		parser = argparse.ArgumentParser(prog='pop', description='Pop into a specific show')

		parser.add_argument('showName', help='The 4-5 letter code for the show name')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		pop(**args)
	elif cmd == 'mkshow':
		parser = argparse.ArgumentParser(prog='mkshow', description='Make a new show')

		parser.add_argument('showName', help='The name of the show. Surround in quotes for multi-word names.')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		mkshow(**args)
	elif cmd == 'rmshow':
		parser = argparse.ArgumentParser(prog='rmshow', description='Delete an existing show. Optionally also remove associated files from disk.')

		parser.add_argument('showName', help='The name of the show. Surround in quotes for multi-word names.')
		parser.add_argument('--clean', '-c', action='store_true', help='Remove associated files/directories for this show')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		rmshow(**args)
	elif cmd == 'mkseq':
		if not env.getEnvironment('show'):
			print 'Please pop into a show first'
			return

		parser = argparse.ArgumentParser(prog='mkseq', description='Make a new sequence in the current show')

		parser.add_argument('seqNum', help='The number of the sequence')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		mkseq(**args)
	elif cmd == 'rmseq':
		if not env.getEnvironment('show'):
			print 'Please pop into a show first'
			return

		parser = argparse.ArgumentParser(prog='rmseq', description='Remove an existing sequence from the current show')

		parser.add_argument('seqNum', help='The number of the sequence')
		parser.add_argument('--clean', '-c', action='store_true', help='Remove associated files/directories for this sequence')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		rmseq(**args)
	elif cmd == 'mkshot':
		if not env.getEnvironment('show'):
			print 'Please pop into a show first'
			return

		parser = argparse.ArgumentParser(prog='mkshot', description='Make a new shot in the current show for the given sequence.')

		parser.add_argument('seqNum', help='The number of the sequence to make the shot in')
		parser.add_argument('shotNum', help='The number of the shot to make')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		mkshot(**args)
	elif cmd == 'rmshot':
		if not env.getEnvironment('show'):
			print 'Please pop into a show first'
			return

		parser = argparse.ArgumentParser(prog='rmshot', description='Remove an existing shot in the current show for the given sequence.')

		parser.add_argument('seqNum', help='The number of the sequence to remove the shot from')
		parser.add_argument('shotNum', help='The number of the shot to remove')
		parser.add_argument('--clean', '-c', action='store_true', help='Remove associated files/directories for this shot')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		rmshot(**args)
	elif cmd == 'mke':
		# Command is irrelevant without the show context set
		if not env.getEnvironment('show'):
			print 'Please pop into a show first'
			return

		parser = argparse.ArgumentParser(prog='mke', description='Make an element (Set, Character, Prop, Effect, etc.)')

		parser.add_argument('elType', help='The type of element (Set, Character, Prop, Effect, etc.) to make')
		parser.add_argument('name', help='The name of the element that will be made (i.e. Table)')
		parser.add_argument('--sequence', '-sq', default=None, help='The sequence number')
		parser.add_argument('--shot', '-s', default=None, help='The shot number')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		mke(**args)
	elif cmd == 'rme':
		if not env.getEnvironment('show'):
			print 'Please pop into a show first'
			return

		parser = argparse.ArgumentParser(prog='rme', description='Remove an exisiting element')

		parser.add_argument('elType', help='The type of element')
		parser.add_argument('name', help='The name of the element')
		parser.add_argument('--sequence', '-sq', default=None, help='The sequence number')
		parser.add_argument('--shot', '-s', default=None, help='The shot number')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		rme(**args)
	elif cmd == 'get':
		# Command is irrelevant without the show context set
		if not env.getEnvironment('show'):
			print 'Please pop into a show first'
			return

		parser = argparse.ArgumentParser(prog='get', description='Get an already existing element to work on')

		parser.add_argument('elType', help='The type of element')
		parser.add_argument('name', help='The name of the element')
		parser.add_argument('--sequence', '-sq', default=None, help='The sequence number')
		parser.add_argument('--shot', '-s', default=None, help='The shot number')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		get(**args)
	elif cmd == 'pub':
		# Cannot publish if element hasn't been retrieved to work on yet
		if not env.getEnvironment('element'):
			print 'Please get an element to work on first'
			return

		parser = argparse.ArgumentParser(prog='pub', description='Publish a new version of the current working element')
		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		pub(**args)
	elif cmd == 'roll':
		if not env.getEnvironment('element'):
			print 'Please get an element to work on first'
			return

		parser = argparse.ArgumentParser(prog='roll', description='Rolls back the current element\'s published file to the previous version, or a specific one if specified.')

		parser.add_argument('--version', '-v', default=None, help='Specify a specific version to rollback to.')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		roll(**args)
	elif cmd == 'mod':
		if not env.getEnvironment('element'):
			print 'Please get an element to work on first'
			return

		parser = argparse.ArgumentParser(prog='mod', description='Modify attributes regarding the current working element')

		parser.add_argument('attribute', help='The name of the attribute you are trying to modify (i.e. ext if you wish to change the expected extension this element produces')
		parser.add_argument('value', nargs='?', default=None, help='The value to set the given attribute to. Can be omitted to retrieve the current value instead')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		mod(**args)
	elif cmd == 'override':
		if not env.getEnvironment('element'):
			print 'Please get an element to work on first'
			return

		parser = argparse.ArgumentParser(prog='override', description='Override the current element for work in a different sequence or shot. If both sequence and shot are omitted, prints the current overrides instead. By omitting shot, the element can be overridden for a sequence in general.')

		parser.add_argument('--sequence', '-sq', default=None, help='The sequence number to override the element into')
		parser.add_argument('--shot', '-s', default=None, help='The shot number to override the element into.')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		override(**args)
	elif cmd == 'els' or cmd == 'elements':
		if not env.getEnvironment('show'):
			print 'Please pop into a show first'
			return

		parser = argparse.ArgumentParser(prog='elements', description='List all elements for the current show')

		parser.add_argument('elType', help='A comma separated list of elements to filter by', default=None, nargs='?')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		elements(**args)
	elif cmd == 'shots':
		if not env.getEnvironment('show'):
			print 'Please pop into a show first'
			return

		parser = argparse.ArgumentParser(prog='shots', description='List all shots for the current show, given a sequence number.')

		parser.add_argument('seqNum', help='The sequence number')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		shots(**args)
	elif cmd == 'seqs' or cmd == 'sequences':
		if not env.getEnvironment('show'):
			print 'Please pop into a show first'
			return

		parser = argparse.ArgumentParser(prog='sequences', description='List all sequences for the current show.')
		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		sequences(**args)
	elif cmd == 'shows':
		parser = argparse.ArgumentParser(prog='shows', description='List all shows in this database')
		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		shows(**args)
	elif cmd == 'pwe':
		# Cannot publish if element hasn't been retrieved to work on yet
		if not env.getEnvironment('element'):
			print 'Please get an element to work on first'
			return

		element = env.element

		if not element:
			print 'Element could not be retrieved, try getting it again with "ge"'
			return

		print element
	elif cmd == 'help' or cmd == 'h' or cmd == '?':
		with open(env.getEnvironment('HELP')) as file:
			line = file.readline()

			while line:
				print line,

				line = file.readline()

	# Debug commands
	elif cmd == 'dump':
		parser = argparse.ArgumentParser(prog='dump', description='Dumps the database contents to stdout')

		parser.add_argument('--expanded', '-e', action='store_true', help='Whether each DatabaseObject is fully expanded in the print out')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		dump(**args)
	elif cmd == 'getenv':
		parser = argparse.ArgumentParser(prog='getenv', description='Gets the custom environment variables that have been set by the Helix system')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		getenv(**args)
	else:
		print 'Unknown command: {}'.format(cmd)

def exit():
	db.save()
	sys.exit(0)

def handleInput(line):
	cmds = line.split('|')

	for c in cmds:
		argv = shlex.split(c)

		if not argv:
			exit()

		cmd = argv[0]

		try:
			if perms.canExecute(cmd):
				main(cmd, argv[1:])
			else:
				print 'You don\'t have permission to do this'
		except SystemExit as e:
			# I really don't like this, but not sure how to handle
			# the exception argparse raises when typing an invalid command
			pass

if __name__ == '__main__':
	if len(sys.argv) > 2:
		handleInput(' '.join(sys.argv[2:]))
	try:
		while True:
			print '\r[HELIX] ',
			line = sys.stdin.readline()

			handleInput(line)

	except KeyboardInterrupt:
		exit()
