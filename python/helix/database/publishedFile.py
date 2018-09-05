import os
import glob

from helix.database.database import DatabaseObject
import helix.environment.environment as env
from helix.database.show import Show
from helix.database.fix import Fix
from helix.database.element import Element
from helix.database.person import Person
from helix.utils.fileclassification import FrameSequence
import helix.utils.utils as utils

class PublishedFile(DatabaseObject):
	TABLE='publishedFiles'
	PK='id'

	def __init__(self, elementName, elementType, filePath, versionlessFilePath, show=None, sequence=None, shot=None, comment=None, fix=None, dummy=False):
		self.table = PublishedFile.TABLE

		if dummy:
			return

		self.elementName = elementName
		self.elementType = elementType
		self.show = show if show else env.getEnvironment('show')
		self.elementId = None
		self.fixId = None
		self._exists = None

		if not self.show:
			raise ValueError('Tried to fallback to environment-set show, but it was null.')

		if filePath is None:
			raise ValueError('Must provide a file path')

		if versionlessFilePath is None:
			raise ValueError('Must provide a versionless file path')

		if self.elementType is None:
			raise ValueError('Must provide an element type to attach this Published File to')

		e = Element(self.elementName, self.elementType, show=self.show, sequence=sequence, shot=shot)

		if not e.exists():
			raise ValueError(
				'No such element to attach to: {} ({}) in {}{}{}'.format(
					e.name,
					e.type,
					e.show,
					' in sequence {}'.format(e.sequence),
					' in shot {}'.format(e.shot)
				)
			)
		else:
			self.elementId = e.id

		self.version = PublishedFile.nextVersion(self.show, self.elementId)

		fetched = self.exists(fetch=True)

		if fetched:
			self.unmap(fetched)
			self._exists = True
		else:
			self._exists = False

			creationInfo = env.getCreationInfo(format=False)

			self.author = creationInfo[0]
			self.creation = creationInfo[1]
			self.comment = comment
			self.file_path = filePath
			self.versionless_path = versionlessFilePath

			s = Show.fromPk(self.show)
			p = Person(self.author)

			if not s:
				raise ValueError('No such show: {}'.format(self.show))

			if not p.exists():
				raise ValueError('No such user: {}'.format(self.author))

			if fix:
				f = Fix.byNum(fix, self.show)

				if not f or not f.exists():
					raise ValueError('No such fix number: {} in show {}'.format(fix, self.show))
				else:
					self.fixId = f.id

	def getFilePaths(self):
		globString = FrameSequence.asGlobString(self.file_path)

		return glob.glob(globString)

	@staticmethod
	def fromPath(path):
		if not os.path.isdir(os.path.dirname(path)):
			return None

		fs = FrameSequence(path)

		if fs.isValid():
			path = fs.getFormatted(includeDir=True)

		from helix.database.sql import Manager
		with Manager(willCommit=False) as mgr:
			res = mgr.connection().execute(
				'''
					SELECT * from {} WHERE file_path='{}' OR versionless_path='{}'
				'''.format(PublishedFile.TABLE, path, path)
			).fetchone()

			if res:
				return PublishedFile.dummy().unmap(res)

		return None

	@property
	def id(self):
		return super(PublishedFile, self)._id(
			'{}_{}_{}'.format(
				self.show,
				self.elementId,
				str(self.version)
			)
		)

	@property
	def pk(self):
		return PublishedFile.PK

	@staticmethod
	def nextVersion(show, element):
		from helix.database.sql import Manager

		with Manager(willCommit=False) as mgr:
			res = mgr.connection().execute(
				'''
					SELECT MAX(version) from {} WHERE show='{}' AND elementId='{}'
				'''.format(PublishedFile.TABLE, show, element)
			).fetchone()

			if res and res[0]:
				return int(res[0]) + 1
			else:
				return 1

	@staticmethod
	def dummy():
		return PublishedFile('', '', '', '', dummy=True)

