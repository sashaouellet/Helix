import os

from datetime import datetime

from helix.database.database import DatabaseObject
from helix.database.show import Show
from helix.database.sequence import Sequence
from helix.database.shot import Shot
from helix.database.element import Element
from helix.database.person import Person
import helix.environment.environment as env
import helix.utils.utils as utils

class Fix(DatabaseObject):
	TABLE = 'fixes'
	PK = 'id'
	STATUS = {
		0: 'new',
		1: 'assigned',
		2: 'ip',
		3: 'review',
		4: 'done'
	}
	PRIORITY = {
		0: 'Very Low',
		1: '',
		2: '',
		3: 'Normal',
		4: '',
		5: 'Medium',
		6: '',
		7: '',
		8: '',
		9: '',
		10: 'Critical'
	}

	def __init__(self, title, body, dept, show=None, sequence=None, shot=None, clipName=None, elementName=None, elementType=None, author=None, status=STATUS[0], priority=3, dummy=False):
		self.table = Fix.TABLE
		self.title = title
		self.body = body
		self.show = show if show else env.getEnvironment('show')
		self.sequence = sequence
		self.shot = shot
		self.elementName = elementName
		self.elementType = elementType
		self._exists = None

		self.sequenceId = None
		self.shotId = None
		self.elementId = None

		if dummy:
			return

		if not title:
			raise ValueError('Must specify a fix title')

		if not body:
			raise ValueError('Must specify details for the fix in the body text')

		if not self.show:
			raise ValueError('Tried to fallback to environment-set show, but it was null.')

		fetched = self.exists(fetch=True)

		if fetched:
			self.unmap(fetched)
			self._exists = True
		else:
			creationInfo = env.getCreationInfo(format=False)
			self.author = author if author else creationInfo[0]
			self.creation = creationInfo[1]
			self.status = status if status in Fix.STATUS.values() else Fix.STATUS[0]
			self.priority = priority if priority in Fix.PRIORITY.keys() else 3
			self.fixer = None
			self.fix_date = None
			self.deadline = None
			self.assign_date = None
			self.num = Fix.nextFixNum(self.show)
			self.for_dept = dept.lower()

			if self.for_dept not in env.cfg.departments and self.for_dept != 'general':
				raise ValueError('Invalid department ({}) to assign fix to. Options are: {}'.format(self.for_dept, ', '.join(['general'] + env.cfg.departments)))

			s = Show(self.show)

			if not s.exists():
				raise ValueError('No such show: {}'.format(show))

			p = Person(self.author)

			if not p.exists():
				raise ValueError('No such user: {}'.format(self.author))

			if self.sequence is not None:
				try:
					self.sequence = int(self.sequence)
				except ValueError:
					raise ValueError('Sequence number must be a number, not: {}'.format(self.sequence))

				sq = Sequence(self.sequence, show=self.show)

				if not sq.exists():
					raise ValueError('No such sequence {} in show {}'.format(sq.num, sq.show))
				else:
					self.sequenceId = sq.id

			if self.shot is not None and self.sequence is not None:
				try:
					self.shot = int(shot)
				except ValueError:
					raise ValueError('Sequence number must be a number, not: {}'.format(shot))

				sh = Shot(self.shot, self.sequence, show=self.show, clipName=clipName)

				if not sh.exists():
					raise ValueError('No such shot {}{} in sequence {} in show {}'.format(sh.num, sh.clipName if sh.clipName else '', sh.sequence, sh.show))
				else:
					self.shotId = sh.id

			if self.elementType:
				el = Element(self.elementName, self.elementType, self.show, self.sequence, self.shot)

				if not el.exists():
					raise ValueError(
						'No such element {} ({}){}{} in show {}'.format(
							el.name,
							el.type,
							' in shot {}'.format(el.shot) if el.shot else '',
							' in sequence {}'.format(el.sequence) if el.sequence else '',
							el.show
						)
					)
				else:
					self.elementId = el.id

	@property
	def id(self):
		return super(Fix, self)._id(
			'{}_{}_{}_{}_{}_{}'.format(
				self.show,
				self.sequence if self.sequence else '',
				self.shot if self.shot else '',
				self.elementId if self.elementId else '',
				self.title,
				self.body
			)
		)

	@property
	def pk(self):
		return Fix.PK

	@property
	def target(self):
		if self.elementId:
			return Element.fromPk(self.elementId)
		elif self.shotId:
			return Shot.fromPk(self.shotId)
		elif self.sequenceId:
			return Sequence.fromPk(self.sequenceId)
		elif self.show:
			return Show.fromPk(self.show)

	@property
	def bid(self):
		if self.deadline is not None and self.creation is not None:
			return (utils.dbTimetoDt(self.deadline) - utils.dbTimetoDt(self.creation)).days + 1

		return None

	@property
	def days(self):
		if self.deadline is not None:
			return (utils.dbTimetoDt(self.deadline) - datetime.now()).days + 1

		return None

	@staticmethod
	def nextFixNum(show=None):
		show = show if show else env.show
		if not show:
			raise ValueError('Tried to fallback to environment-set show, but it was null.')

		from helix.database.sql import Manager

		with Manager(willCommit=False) as mgr:
			res = mgr.connection().execute(
				'''
					SELECT MAX(num) from {} WHERE show='{}'
				'''.format(Fix.TABLE, show)
			).fetchone()

			if res and res[0]:
				return int(res[0]) + 1
			else:
				return 1

	@staticmethod
	def byNum(fixNum, show=None):
		show = show if show else env.show
		if not show:
			raise ValueError('Tried to fallback to environment-set show, but it was null.')

		from helix.database.sql import Manager

		with Manager(willCommit=False) as mgr:
			res = mgr.connection().execute(
				'''
					SELECT * from {} WHERE num='{}' AND show='{}'
				'''.format(Fix.TABLE, fixNum, show)
			).fetchone()

			if res:
				return Fix('.', '.', show).unmap(res)
			else:
				return None

	@staticmethod
	def dummy():
		return Fix('', '', '', dummy=True)
