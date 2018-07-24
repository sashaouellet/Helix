import helix.environment.environment as env
from helix.database.database import DatabaseObject

class ElementContainer(DatabaseObject):
	def __init__(self, show=None, sequence=None, shot=None):
		self.show = show if show else env.getEnvironment('show')

		if not self.show:
			raise ValueError('Tried to fallback to environment-set show, but it was null.')

		if not Show(self.show).exists():
			raise ValueError('No such show: {}'.format(self.show))

		self.sequence = sequence
		self.shot = shot

	def getElement(self, name, elType):
		from helix.database.element import Element

		try:
			el = Element(name, elType, show=self.show, sequence=self.sequence, shot=self.shot)

			if el.exists():
				return el
			else:
				return None
		except:
			return None

	def getElements(self, names=[], types=[], shows=[], seqs=[], shots=[], clips=[], authors=[], assignedTo=[], status=[], debug=False):
		from helix.database.sql import Manager
		from helix.database.element import Element

		with Manager(willCommit=False) as mgr:
			query = """SELECT * FROM {}""".format(
				Element.TABLE
			)

			statement = 'WHERE'

			if names is not None:
				if isinstance(names, basestring):
					names = [names]
				if names:
					query += " {} name IN ({})".format(statement, ','.join(["'{}'".format(n) for n in names]))
					statement = 'AND'

			if types is not None:
				if isinstance(types, basestring):
					types = [types]
				if types:
					query += " {} type IN ({})".format(statement, ','.join(["'{}'".format(n) for n in types]))
					statement = 'AND'

			if shows is not None:
				if isinstance(shows, basestring):
					shows = [shows]
				if shows:
					query += " {} show IN ({})".format(statement, ','.join(["'{}'".format(n) for n in shows]))
					statement = 'AND'

			if seqs is not None:
				if isinstance(seqs, int):
					seqs = [seqs]
				if seqs:
					if isinstance(seqs, basestring) and seqs.lower() == 'null':
						query += " {} sequence IS NULL".format(statement)
					else:
						query += " {} sequence IN ({})".format(statement, ','.join(["'{}'".format(n) for n in seqs]))
					statement = 'AND'

			if shots is not None:
				if isinstance(shots, int):
					shots = [shots]
				if shots:
					if isinstance(shots, basestring) and shots.lower() == 'null':
						query += " {} shot IS NULL".format(statement)
					else:
						query += " {} shot IN ({})".format(statement, ','.join(["'{}'".format(n) for n in shots]))
					statement = 'AND'

			if clips is not None:
				if isinstance(clips, basestring):
					clips = [clips]
				if clips:
					if clips[0].lower() != 'null':
						query += " {} shot_clipName IN ({})".format(statement, ','.join(["'{}'".format(n) for n in clips]))
					else:
						query += " {} shot_clipName IS NULL".format(statement)
					statement = 'AND'

			if status is not None:
				if isinstance(status, basestring):
					status = [status]
				if status:
					if status[0].lower() != 'null':
						query += " {} status IN ({})".format(statement, ','.join(["'{}'".format(n) for n in status]))
					else:
						query += " {} status IS NULL".format(statement)
					statement = 'AND'

			if authors is not None:
				if isinstance(authors, basestring):
					authors = [authors]
				if authors:
					if authors[0].lower() != 'null':
						query += " {} author IN ({})".format(statement, ','.join(["'{}'".format(n) for n in authors]))
					else:
						query += " {} author IS NULL".format(statement)
					statement = 'AND'

			if assignedTo is not None:
				if isinstance(assignedTo, basestring):
					assignedTo = [assignedTo]
				if assignedTo:
					if assignedTo[0].lower() != 'null':
						query += " {} assigned_to IN ({})".format(statement, ','.join(["'{}'".format(n) for n in assignedTo]))
					else:
						query += " {} assigned_to IS NULL".format(statement)
					statement = 'AND'

			elements = []

			if debug:
				print 'QUERY:', query

			for row in mgr.connection().execute(query).fetchall():
				elements.append(Element.dummy().unmap(row))

			return elements