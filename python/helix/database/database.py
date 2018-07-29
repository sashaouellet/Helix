"""This module defines the base type for all items stored in the database, DatabaseObject.
It is responsible for retrieving the values of individual columns for an object as well
as setting those values. DatabaseObjects are delegated their DB insertion functionality.

A DatabaseObject can also check for existence in the database and provides an interface
for static creation with only the primary key (PK) provided.

Finally, the module allows for retrieving all shows or a single show from the database.

__author__  = Sasha Ouellet (sashaouellet@gmail.com / www.sashaouellet.com)
__version__ = 2.0.0
__date__    = 07/28/18
"""
import sqlite3
import hashlib
from helix.database.sql import Manager

with Manager() as mgr:
	mgr.initTables()

class DatabaseObject(object):
	def get(self, attr, default=None):
		with Manager(willCommit=False) as mgr:
			try:
				return mgr.connection().execute('SELECT {} FROM {} WHERE {}="{}"'.format(attr, self.table, self.pk, getattr(self, self.pk, None))).fetchone()[0]
			except sqlite3.OperationalError as e:
				print 'No such attribute: {}, defaulting to {}'.format(attr, default)
				return default

	def set(self, attr, val, insertIfMissing=False):
		with Manager() as mgr:
			if self.exists():
				mgr.connection().execute("UPDATE {} SET {}='{}' WHERE {}='{}'".format(self.table, attr, val, self.pk, getattr(self, self.pk)))
			else:
				setattr(self, attr, val)
				if insertIfMissing:
					self.insert()

	def insert(self):
		with Manager() as mgr:
			self._exists = mgr._insert(self.table, self)

			return self._exists

	def exists(self, fetch=False):
		# we cache the exists after construction because we either fetched
		# it from the DB or made a new one
		if self._exists is not None and not fetch:
			return self._exists

		with Manager(willCommit=False) as mgr:
			try:
				rows = mgr.connection().execute('SELECT * FROM {} WHERE {}="{}"'.format(self.table, self.pk, getattr(self, self.pk, None))).fetchall()

				if fetch:
					return rows[0] if rows else None
				else:
					return len(rows) > 0
			except sqlite3.OperationalError as e:
				print e
				if fetch:
					return None
				else:
					return False

	@classmethod
	def fromPk(cls, pk):
		if not pk:
			return None

		with Manager(willCommit=False) as mgr:
			query = """SELECT * FROM {} WHERE {}='{}'""".format(
				cls.TABLE,
				cls.PK,
				pk
			)

			row = mgr.connection().execute(query).fetchone()

			if row:
				return cls.dummy().unmap(row)

		return None

	def _id(self, token=''):
		# It's useless to call this on a subclass that hasn't
		# overwritten this method.. which is fine, not all of them
		# need to have an id.
		return hashlib.md5(token).hexdigest()

	def map(self):
		with Manager(willCommit=False) as mgr:
			values = ()

			for c, notNull in mgr.getColumnNames(self.table):
				val = getattr(self, c, None)

				if val is None and notNull:
					raise ValueError('{} for {} cannot be null'.format(c, type(self).__name__))

				values += (val, )

			return values

	def unmap(self, values):
		with Manager(willCommit=False) as mgr:
			for col, val in zip([c[0] for c in mgr.getColumnNames(self.table)], list(values)):
				try:
					setattr(self, col, val)
				except:
					# Gross, but for private variables we are
					# probably calculating them a different way anyway
					# when we retrieve them later
					pass

			self._exists = True

			return self

	@property
	def pk(self):
		raise NotImplementedError()

	def __repr__(self):
		with Manager(willCommit=False) as mgr:
			vals = []

			for c, _ in mgr.getColumnNames(self.table):
				val = getattr(self, c, None)

				if val is None:
					val = 'NULL'

				vals.append((c + '=' + str(val)))

			return type(self).__name__ + ' (' + ', '.join(vals) + ')'

	def __eq__(self, other):
		if not isinstance(other, type(self)):
			return False

		return self.__dict__ == other.__dict__

	def __ne__(self, other):
		return not (self == other)

def getShows():
	from helix.database.show import Show
	with Manager(willCommit=False) as mgr:
		query = """SELECT * FROM {}""".format(Show.TABLE)
		rows = mgr.connection().execute(query).fetchall()
		shows = []

		for r in rows:
			shows.append(Show.dummy().unmap(r))

		return shows

def getShow(alias):
	from helix.database.show import Show
	with Manager(willCommit=False) as mgr:
		query = """SELECT * FROM {} WHERE alias='{}'""".format(Show.TABLE, alias)
		row = mgr.connection().execute(query).fetchone()

		if row and row[0]:
			return Show.dummy().unmap(row)

		return None

def getElements():
	from helix.database.element import Element
	with Manager(willCommit=False) as mgr:
		query = """SELECT * FROM {}""".format(Element.TABLE)
		rows = mgr.connection().execute(query).fetchall()
		elements = []

		for r in rows:
			elements.append(Element.dummy().unmap(r))

		return elements

