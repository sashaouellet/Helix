import sys, os
import argparse
import environment as env
from database import *

dbLoc = env.getEnvironment('db')

if not dbLoc:
	raise KeyError('Database location not set in your environment')

db = Database(dbLoc)

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

def mke(seqNum, shotNum, elType, name):
	try:
		seq, shot, element = env.show.getElement(seqNum, shotNum, elType.lower(), name)

		if element:
			print 'Element already exists (did you mean to use "ge"?)'
			return

		shot.addElement(Element.factory(seqNum, shotNum, elType.lower(), name))
		db.save()

	except DatabaseError:
		return

def ge(seqNum, shotNum, elType, name):
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

	if element.versionUp(sequence):
		print 'Published new version: {}'.format(int(element.get('version')) - 1)

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

def elements(seq, shot, elType=None):
	print seq, shot
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

		print '\n'.join([str(el) for el in els])
	except DatabaseError:
		return

def rme(seqNum, shotNum, elType, name):
	elType = elType.lower()
	# TODO: sanitize name input
	try:
		seq, shot, element = env.show.getElement(seqNum, shotNum, elType, name)

		if not element:
			print 'Element doesn\'t exist'
			return

		shot.destroyElement(elType, name)

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

		parser.add_argument('seqNum', help='The sequence number')
		parser.add_argument('shotNum', help='The shot number')
		parser.add_argument('elType', help='The type of element (Set, Character, Prop, Effect) to make')
		parser.add_argument('name', help='The name of the element that will be made (i.e. Table)')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		mke(**args)
	elif cmd == 'ge':
		# Command is irrelevant without the show context set
		if not env.getEnvironment('show'):
			print 'Please pop into a show first'
			return

		parser = argparse.ArgumentParser(prog='ge', description='Navigate to an already existing element')

		parser.add_argument('seqNum', help='The sequence number')
		parser.add_argument('shotNum', help='The shot number')
		parser.add_argument('elType', help='The type of element')
		parser.add_argument('name', help='The name of the element')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		ge(**args)
	elif cmd == 'pub':
		# Cannot publish if element hasn't been retrieved to work on yet
		if not env.getEnvironment('element'):
			print 'Please get an element to work on first'
			return

		parser = argparse.ArgumentParser(prog='pub', description='Publish a new version of the current working element')

		parser.add_argument('--sequence', action='store_true', help='Whether you are publishing a sequence of files or not. By default, if omitted, this will be a publish for a standard single file. Add this flag if you are publishing a sequence of files (image sequence, geometry cache, etc.)')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		pub(**args)
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

		parser.add_argument('seqNum', help='The sequence number')
		parser.add_argument('shotNum', help='The shot number')
		parser.add_argument('type', help='The type of element')
		parser.add_argument('name', help='The name of the element')

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

if __name__ == '__main__':
	try:
		while True:
			print '\r[HELIX] ',
			line = sys.stdin.readline()

			argv = line.split()

			if not argv:
				exit()

			cmd = argv[0]

			try:
				main(cmd, argv[1:])
			except SystemExit as e:
				# I really don't like this, but not sure how to handle
				# the exception argparse raises when typing an invalid command
				pass
	except KeyboardInterrupt:
		exit()
