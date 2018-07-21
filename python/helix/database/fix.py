import os

from helix.database.database import DatabaseObject
from helix.database.show import Show
from helix.database.sequence import Sequence
from helix.database.shot import Shot
from helix.database.element import Element
import helix.environment.environment as env

class Fix(DatabaseObject):
	TABLE = 'fixes'
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

	def __init__(self, title, body, show=None, sequence=None, shot=None, elementName=None, elementType=None, author=None, status=STATUS[0], priority=PRIORITY[3]):
		self.table = Fix.TABLE
		self.title = title
		self.body = body
		self.show = show if show else env.show
		self.sequence = sequence
		self.shot = shot
		self.elementName = elementName
		self.elementType = elementType
		self._exists = None

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

			# Checks if given value is one of the string values of the priority dict
			# Falls back to checking if the given priority is one of the number values
			# Finally defaults to PRIORITY[3]
			self.priority = priority if priority in Fix.PRIORITY.values() else Fix.PRIORITY.get(priority, Fix.PRIORITY[3])

			self.fixer = None
			self.fix_date = None
			self.deadline = None
			self.assign_date = None
			self.num = Fix.nextFixNum(self.show)

			s = Show(self.show)

			if not s.exists():
				raise ValueError('No such show: {}'.format(show))

			if self.sequence:
				try:
					self.sequence = int(self.sequence)
				except ValueError:
					raise ValueError('Sequence number must be a number, not: {}'.format(self.sequence))

				sq = Sequence(self.sequence, show=self.show)

				if not sq.exists():
					raise ValueError('No such sequence {} in show {}'.format(sq.num, sq.show))
				else:
					self.sequenceId = sq.id

			if self.shot and self.sequence:
				try:
					self.shot = int(shot)
				except ValueError:
					raise ValueError('Sequence number must be a number, not: {}'.format(shot))

				sh = Shot(self.shot, self.sequence, show=self.show)

				if not sh.exists():
					raise ValueError('No such shot {} in sequence {} in show {}'.format(sh.num, sh.sequence, sh.show))
				else:
					self.shotId = sh.id

			if self.elementName and self.elementType:
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

	@property
	def id(self):
		return super(Fix, self)._id(
			'{}_{}_{}_{}_{}_{}_{}'.format(
				self.show,
				self.sequence if self.sequence else '',
				self.shot if self.shot else '',
				self.elementName if self.elementName else '',
				self.elementType if self.elementType else '',
				self.title,
				self.body
			)
		)

	@property
	def pk(self):
		return 'id'

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
				return int(res) + 1
			else:
				return 1
