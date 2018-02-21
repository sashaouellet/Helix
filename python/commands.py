import sys, os
import argparse
import environment as env
from database import *
from permissions import PermissionHandler

dbLoc = env.getEnvironment('db')

if not dbLoc:
	raise KeyError('Database location not set in your environment')

db = Database(dbLoc)
perms = PermissionHandler()

# User commands
def pop(showName):
	show = db.getShow(showName)

	if not show:
		print 'Didn\'t recognize show name/alias: {}'.format(showName)
		return

	showName = show.get('name')

	env.setEnvironment('show', showName)
	env.show = show

	print 'Set environment for {}'.format(showName)

def mke(elType, name, seqNum, shotNum):
	try:
		seq, shot, element = env.show.getElement(seqNum, shotNum, elType.lower(), name)

		if element:
			print 'Element already exists (did you mean to use "ge"?)'
			return

		shot.addElement(Element.factory(seqNum, shotNum, elType.lower(), name))
		db.save()

	except DatabaseError:
		return

def get(elType, name, seqNum, shotNum):
	try:
		seq, shot, element = env.show.getElement(seqNum, shotNum, elType.lower(), name)

		if not element:
			print 'Element doesn\'t exist (Check for typos in the name, or make a new element using "mke")'
			return

		env.setEnvironment('element', element.getDiskLocation())
		env.element = element

	except DatabaseError:
		return

# Element-context commands
def pub(sequence=False):
	element = env.element

	if not element:
		print 'Element could not be retrieved, try getting it again with "ge"'
		return

	newVersion = element.versionUp(sequence)

	if newVersion:
		print 'Published new version: {}'.format(newVersion)
		db.save()

def roll(version=None):
	element = env.element

	if not element:
		print 'Element could not be retrieved, try getting it again with "ge"'
		return

	newVersion = element.rollback(version=version)

	if newVersion:
		print 'Rolled back published file to version: {}'.format(newVersion)
		db.save()

def mod(attribute, value=None):
	element = env.element

	if not element:
		print 'Element could not be retrieved, try getting it again with "ge"'
		return

	if value:
		try:
			element.set(attribute, value, checkKey=True)
			db.save()

			print 'Set {} to {}'.format(attribute, value)
		except DatabaseError:
			return

	else:
		print element.get(attribute)

def clone(shot, seq=None):
	element = env.element

	if not element:
		print 'Element could not be retrieved, try getting it again with "ge"'
		return

	element.clone(shot, seq)

	seq = seq if seq else element.get('parent').split('/')[0]

	print 'Cloned to shot {} sequence {}'.format(shot, seq)

	db.save()

def rmclone(shot, seq=None):
	element = env.element

	if not element:
		print 'Element could not be retrieved, try getting it again with "ge"'
		return

	seq = seq if seq else element.get('parent').split('/')[0]

	try:
		element.rmclone(shot, seq)

		print 'Removed clone from shot {} sequence {}'.format(shot, seq)

		db.save()
	except DatabaseError:
		print 'Element clone for shot {} sequence {} does\'t exist'

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

def elements(seq, shot, elType=None, date=None):
	try:
		els = []
		if seq == -1:
			seqs = env.show.getSequences()
			for s in [s for sq in seqs for s in sq.getShots()]:
				if shot != -1 and s.get('num') != shot:
					continue

				els.extend(s.getElements())

		elif shot == -1:
			for s in env.show.getSequence(seq).getShots():
				els.extend(s.getElements())
		else:
			s = env.show.getShot(seq, shot)

			els.extend(s.getElements())

		if elType:
			elType = elType.lower()
			els = [e for e in els if e.get('type') == elType]

		if date:
			els = [e for e in els if e.isMoreRecent(date)]

		# TODO sort by pubVersion

		print '\n'.join([str(el) for el in els])
	except DatabaseError:
		return

def rme(elType, name, seqNum, shotNum):
	elType = elType.lower()
	# TODO: sanitize name input
	try:
		seq, shot, element = env.show.getElement(seqNum, shotNum, elType, name)

		if not element:
			print 'Element doesn\'t exist'
			return

		shot.destroyElement(elType, name)
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
	elif cmd == 'mke':
		# Command is irrelevant without the show context set
		if not env.getEnvironment('show'):
			print 'Please pop into a show first'
			return

		parser = argparse.ArgumentParser(prog='mke', description='Make an element (Set, Character, Prop, Effect)')

		parser.add_argument('elType', help='The type of element (Set, Character, Prop, Effect) to make')
		parser.add_argument('name', help='The name of the element that will be made (i.e. Table)')
		parser.add_argument('seqNum', help='The sequence number')
		parser.add_argument('shotNum', help='The shot number')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		mke(**args)
	elif cmd == 'get':
		# Command is irrelevant without the show context set
		if not env.getEnvironment('show'):
			print 'Please pop into a show first'
			return

		parser = argparse.ArgumentParser(prog='get', description='Get an already existing element to work on')

		parser.add_argument('elType', help='The type of element')
		parser.add_argument('name', help='The name of the element')
		parser.add_argument('seqNum', help='The sequence number')
		parser.add_argument('shotNum', help='The shot number')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		get(**args)
	elif cmd == 'pub':
		# Cannot publish if element hasn't been retrieved to work on yet
		if not env.getEnvironment('element'):
			print 'Please get an element to work on first'
			return

		parser = argparse.ArgumentParser(prog='pub', description='Publish a new version of the current working element')

		parser.add_argument('--sequence', action='store_true', help='Whether you are publishing a sequence of files or not. By default, if omitted, this will be a publish for a standard single file. Add this flag if you are publishing a sequence of files (image sequence, geometry cache, etc.)')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		pub(**args)
	elif cmd == 'roll':
		# Cannot publish if element hasn't been retrieved to work on yet
		if not env.getEnvironment('element'):
			print 'Please get an element to work on first'
			return

		parser = argparse.ArgumentParser(prog='roll', description='Rolls back the current element\'s published file to the previous version, or a specific one if specified.')

		parser.add_argument('--version', '-v', default=None, help='Specify a specific version to rollback to.')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		roll(**args)
	elif cmd == 'mod':
		# Cannot publish if element hasn't been retrieved to work on yet
		if not env.getEnvironment('element'):
			print 'Please get an element to work on first'
			return

		parser = argparse.ArgumentParser(prog='mod', description='Modify attributes regarding the current working element')

		parser.add_argument('attribute', help='The name of the attribute you are trying to modify (i.e. ext if you wish to change the expected extension this element produces')
		parser.add_argument('value', nargs='?', default=None, help='The value to set the given attribute to. Can be omitted to retrieve the current value instead')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		mod(**args)
	elif cmd == 'clone':
		# Cannot publish if element hasn't been retrieved to work on yet
		if not env.getEnvironment('element'):
			print 'Please get an element to work on first'
			return

		parser = argparse.ArgumentParser(prog='clone', description='Clones the given element to the specified sequence/shot so that it can exist across multiple sequence/shots')

		parser.add_argument('shot', help='The shot number to clone to')
		parser.add_argument('--seq', '-sq', help='The sequence number to clone to. By default will use the current sequence this element is in.', default=None)

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		clone(**args)
	elif cmd == 'rmclone':
		# Cannot publish if element hasn't been retrieved to work on yet
		if not env.getEnvironment('element'):
			print 'Please get an element to work on first'
			return

		parser = argparse.ArgumentParser(prog='rmclone', description='Removes a previously made clone of the current element')

		parser.add_argument('shot', help='The shot number of the clone to remove')
		parser.add_argument('--seq', '-sq', help='The sequence number of the clone to remove. By default will use the current sequence this element is in.', default=None)

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		rmclone(**args)
	elif cmd == 'els' or cmd == 'elements':
		if not env.getEnvironment('show'):
			print 'Please pop into a show first'
			return

		parser = argparse.ArgumentParser(prog='elements', description='List all elements for the current show, given a sequence and shot number.')

		parser.add_argument('--seq', '-sq', help='The sequence number', default=-1)
		parser.add_argument('--shot', '-s', help='The shot number', default=-1)
		parser.add_argument('elType', help='The type of element to filter to list by', default=None, nargs='?')

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
	elif cmd == 'rme':
		if not env.getEnvironment('show'):
			print 'Please pop into a show first'
			return

		parser = argparse.ArgumentParser(prog='rme', description='Remove an exisiting element')

		parser.add_argument('elType', help='The type of element')
		parser.add_argument('name', help='The name of the element')
		parser.add_argument('seqNum', help='The sequence number')
		parser.add_argument('shotNum', help='The shot number')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		rme(**args)
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
		pass # TODO: implement help output

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
		argv = c.split()

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
