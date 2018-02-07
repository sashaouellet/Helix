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

def mke(seqNum, shotNum, type, name):
	try:
		seq, shot, element = env.show.getElement(seqNum, shotNum, type.lower(), name)

		if element:
			print 'Element already exists (did you mean to use "ge"?)'
			return

		shot.addElement(Element.factory(seqNum, shotNum, type.lower(), name))
		db.save()

	except DatabaseError:
		return

def ge(seqNum, shotNum, type, name):
	try:
		seq, shot, element = env.show.getElement(seqNum, shotNum, type.lower(), name)

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

	element.versionUp(sequence)

	print 'Published new version: {}'.format(int(element.get('version')) - 1)

def mod(attribute, value):
	element = env.element

	if not element:
		print 'Element could not be retrieved, try getting it again with "ge"'
		return

	element.set(attribute, value)

	print 'Set {} to {}'.format(attribute, value)

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
		parser.add_argument('type', help='The type of element (Set, Character, Prop, Effect) to make')
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
		parser.add_argument('type', help='The type of element')
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
		parser.add_argument('value', help='The value to set the given attribute to')

		args = {k:v for k,v in vars(parser.parse_args(argv)).items() if v is not None}

		mod(**args)
	elif cmd == 'cwe':
		# Cannot publish if element hasn't been retrieved to work on yet
		if not env.getEnvironment('element'):
			print 'Please get an element to work on first'
			return

		element = env.element

		if not element:
			print 'Element could not be retrieved, try getting it again with "ge"'
			return

		print element
	elif cmd == 'help' or cmd == 'h':
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
