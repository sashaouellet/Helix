from helix.database.database import *
import sqlite3
import helix.environment.environment as env
from helix.database.person import Person
from helix.database.show import Show

class Manager(object):
	TABLE_LIST = [
					'shows',
					'sequences',
					'shots',
					'elements',
					'takes',
					'publishedFiles',
					'fixes',
					'people'
				]

	def __init__(self, location=None, willCommit=True):
		if location:
			self.location = location
		else:
			# TODO put in env var
			self.location = env.getEnvironment('db')
		self.willCommit = willCommit

	def __enter__(self):
		self.conn = sqlite3.connect(self.location)
		self.conn.execute('PRAGMA foreign_keys = ON')

		return self

	def __exit__(self, exception_type, exception_value, traceback):
		if self.willCommit:
			self.conn.commit()

		self.conn.close()

	def connection(self):
		return self.conn

	def getColumnNames(self, table):
		return [(str(r[1]), bool(r[3])) for r in self.conn.execute('PRAGMA TABLE_INFO ({})'.format(table)).fetchall()]

	def _insert(self, table, obj):
		if isinstance(obj, tuple):
			values = obj
		elif isinstance(obj, DatabaseObject):
			values = obj.map()

		valuesString = ','.join(['?'] * len(values))

		try:
			self.conn.execute('INSERT INTO {} VALUES({})'.format(table, valuesString), values)
			return True
		except sqlite3.IntegrityError as e:
			print str(e)
			return False

	def initTables(self):
		self.conn.execute(
		'''
			CREATE TABLE IF NOT EXISTS 'people' (
				'username'		VARCHAR(10) NOT NULL UNIQUE,
				'full_name'		TEXT,
				'department'	TEXT,
				PRIMARY KEY('username')
			)
		'''
		)
		self.conn.execute(
		'''
			CREATE TABLE IF NOT EXISTS 'shows' (
				'alias'			VARCHAR(10) NOT NULL UNIQUE,
				'name'			TEXT,
				'work_path'		TEXT NOT NULL,
				'release_path'	TEXT NOT NULL,
				'author'		VARCHAR(10) NOT NULL,
				'creation'		DATE NOT NULL,
				FOREIGN KEY('author') REFERENCES 'people'('username'),
				PRIMARY KEY('alias')
			)
		'''
		)
		self.conn.execute(
		'''
			CREATE TABLE IF NOT EXISTS 'sequences' (
				'id'			VARCHAR(32) PRIMARY KEY NOT NULL UNIQUE,
				'num'			INTEGER NOT NULL,
				'show'			VARCHAR(10) NOT NULL,
				'work_path'		TEXT NOT NULL,
				'release_path'	TEXT NOT NULL,
				'author'		VARCHAR(10) NOT NULL,
				'creation'		DATE NOT NULL,
				FOREIGN KEY('show') REFERENCES 'shows'('alias'),
				FOREIGN KEY('author') REFERENCES 'people'('username')
			)
		'''
		)
		self.conn.execute(
		'''
			CREATE TABLE IF NOT EXISTS 'shots' (
				'id'			VARCHAR(32) PRIMARY KEY NOT NULL UNIQUE,
				'show'			VARCHAR(10) NOT NULL,
				'sequence'		INTEGER NOT NULL,
				'sequenceId'	VARCHAR(32) NOT NULL,
				'num'			INTEGER NOT NULL,
				'start'			INTEGER,
				'end'			INTEGER,
				'clipName'		TEXT,
				'status'		TEXT NOT NULL,
				'assigned_to'	VARCHAR(10),
				'take'			INTEGER,
				'thumbnail'		TEXT,
				'work_path'		TEXT NOT NULL,
				'release_path'	TEXT NOT NULL,
				'author'		VARCHAR(10) NOT NULL,
				'creation'		DATE NOT NULL,
				FOREIGN KEY('author') REFERENCES 'people'('username'),
				FOREIGN KEY('show') REFERENCES 'shows'('alias'),
				FOREIGN KEY('assigned_to') REFERENCES 'people'('username'),
				FOREIGN KEY('sequenceId') REFERENCES 'sequences'('id')
			)
		'''
		)
		self.conn.execute(
		'''
			CREATE TABLE IF NOT EXISTS 'elements' (
				'id'			VARCHAR(32) PRIMARY KEY NOT NULL UNIQUE,
				'name'			TEXT NOT NULL,
				'type'			TEXT NOT NULL,
				'author'		VARCHAR(10) NOT NULL,
				'creation'		DATE NOT NULL,
				'show'			VARCHAR(10) NOT NULL,
				'sequence'		INTEGER,
				'sequenceId'	VARCHAR(32),
				'shot'			INTEGER,
				'shotId'		VARCHAR(32),
				'work_path'		TEXT NOT NULL,
				'release_path'	TEXT NOT NULL,
				'status'		TEXT NOT NULL,
				'assigned_to'	TEXT,
				'pubVersion'	INTEGER NOT NULL,
				'version'		INTEGER NOT NULL,
				'thumbnail'		TEXT,
				FOREIGN KEY('show') REFERENCES 'shows'('alias'),
				FOREIGN KEY('author') REFERENCES 'people'('username'),
				FOREIGN KEY('shotId') REFERENCES 'shots'('id'),
				FOREIGN KEY('sequenceId') REFERENCES 'sequences'('id')
			)
		'''
		)
		self.conn.execute(
		'''
			CREATE TABLE IF NOT EXISTS 'fixes' (
				'id'			VARCHAR(32) PRIMARY KEY NOT NULL UNIQUE,
				'num'			INTEGER NOT NULL,
				'author'		VARCHAR(10) NOT NULL,
				'creation'		DATE NOT NULL,
				'fixer'			VARCHAR(10),
				'fix_date'		DATE,
				'deadline'		DATE,
				'status'		TEXT NOT NULL,
				'priority'		INTEGER,
				'title'			TEXT NOT NULL,
				'body'			TEXT NOT NULL,
				'assign_date'	DATE,
				'show'			VARCHAR(10) NOT NULL,
				'sequence'		INTEGER,
				'sequenceId'	VARCHAR(32),
				'shot'			INTEGER,
				'shotId'		VARCHAR(32),
				'elementId'		VARCHAR(32),
				FOREIGN KEY('author') REFERENCES 'people'('username'),
				FOREIGN KEY('fixer') REFERENCES 'people'('username'),
				FOREIGN KEY('show') REFERENCES 'shows'('alias'),
				FOREIGN KEY('sequenceId') REFERENCES 'sequences'('id'),
				FOREIGN KEY('shotId') REFERENCES 'shots'('id'),
				FOREIGN KEY('elementId') REFERENCES 'elements'('id')
			)
		'''
		)
		self.conn.execute(
		'''
			CREATE TABLE IF NOT EXISTS 'publishedFiles' (
				'id'		VARCHAR(32) PRIMARY KEY NOT NULL UNIQUE,
				'version'	INTEGER NOT NULL,
				'author'	VARCHAR(10) NOT NULL,
				'creation'	DATE NOT NULL,
				'comment'	TEXT,
				'file_path'	TEXT NOT NULL,
				'elementId'	VARCHAR(32) NOT NULL,
				'fixId'		VARCHAR(32),
				'show'		VARCHAR(10),
				FOREIGN KEY('author') REFERENCES 'people'('username'),
				FOREIGN KEY('elementId') REFERENCES 'elements'('id')
				FOREIGN KEY('fixId') REFERENCES 'fixes'('id')
				FOREIGN KEY('show') REFERENCES 'shows'('alias')
			)
		'''
		)
		self.conn.execute(
		'''
			CREATE TABLE IF NOT EXISTS 'takes' (
				'id'			VARCHAR(32) PRIMARY KEY NOT NULL UNIQUE,
				'num'			INTEGER NOT NULL,
				'author'		VARCHAR(10) NOT NULL,
				'creation'		DATE NOT NULL,
				'show'			VARCHAR(10) NOT NULL,
				'sequence'		INTEGER NOT NULL,
				'sequenceId'	VARCHAR(32) NOT NULL,
				'shot'			INTEGER NOT NULL,
				'shotId'		VARCHAR(32) NOT NULL,
				'comment'		TEXT,
				'first_frame'	INTEGER,
				'last_frame'	INTEGER,
				'file_path'		TEXT NOT NULL,
				'thumbnail'		TEXT,
				FOREIGN KEY('author') REFERENCES 'people'('username'),
				FOREIGN KEY('show') REFERENCES 'shows'('alias'),
				FOREIGN KEY('sequenceId') REFERENCES 'sequences'('id'),
				FOREIGN KEY('shotId') REFERENCES 'shots'('id')
			)
		'''
		)

	def dropTables(self, tables=TABLE_LIST):
		for t in [t for t in tables if t in Manager.TABLE_LIST]:
			try:
				self.conn.execute('DROP TABLE {}'.format(t))
			except sqlite3.OperationalError as e:
				import traceback
				print traceback.format_exc(e)
				continue