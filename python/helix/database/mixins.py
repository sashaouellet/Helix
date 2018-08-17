import collections

class FixMixin(object):
	@property
	def completion(self):
		from helix.database.sql import Manager
		from helix import Fix, Show

		if isinstance(self, Show):
			idQualifier = None
			show = self.alias
		else:
			idQualifier = self.__class__.__name__.lower() + 'Id'
			show = self.show

		with Manager(willCommit=False) as mgr:
			query = """SELECT status, COUNT(*) FROM {} WHERE show='{}' and type='task'""".format(Fix.TABLE, show)

			if idQualifier is not None:
				query += " AND {}='{}'".format(idQualifier, self.id)

			query += "GROUP BY status"

			rows = mgr.connection().execute(query).fetchall()

			if rows:
				done = 0
				total = 0

				for r in rows:
					total += r[1] # Add count for this status to total
					if r[0] == 'done':
						done += r[1]

				return float(done) / total
			else:
				# No tasks at all, 0% completion. Maybe we want no tasks to mean 100% completion?
				return 0

	def numTasksBy(self, qualifier, type='task', status=None):
		from helix.database.sql import Manager
		from helix import Fix, Show

		if isinstance(self, Show):
			idQualifier = None
			show = self.alias
		else:
			idQualifier = self.__class__.__name__.lower() + 'Id'
			show = self.show

		with Manager(willCommit=False) as mgr:
			query = """SELECT {}, COUNT(*) FROM {} WHERE show='{}' and type='{}'""".format(qualifier, Fix.TABLE, show, type)

			if idQualifier is not None:
				query += " AND {}='{}'".format(idQualifier, self.id)

			if status is not None:
				query += " AND status='{}'".format(status)

			query += " GROUP BY {}".format(qualifier)

			rows = mgr.connection().execute(query).fetchall()
			results = collections.defaultdict(int)

			if rows:
				for r in rows:
					if not r[0]:
						results['_'] += r[1]
					else:
						results[r[0]] += r[1]

				return results
			else:
				return results

	def numTasks(self, type='task', status=None, department=None, user=None):
		from helix.database.sql import Manager
		from helix import Fix, Show

		if isinstance(self, Show):
			idQualifier = None
			show = self.alias
		else:
			idQualifier = self.__class__.__name__.lower() + 'Id'
			show = self.show

		with Manager(willCommit=False) as mgr:
			query = """SELECT COUNT(*) FROM {} WHERE show='{}' and type='{}'""".format(Fix.TABLE, show, type)

			if idQualifier is not None:
				query += " AND {}='{}'".format(idQualifier, self.id)

			if status is not None:
				query += " AND status='{}'".format(status)

			if department is not None:
				query += " AND for_dept='{}'".format(department)

			if user is not None:
				query += " AND fixer='{}'".format(user)

			row = mgr.connection().execute(query).fetchone()

			if row and row[0]:
				return row[0]
			else:
				return 0