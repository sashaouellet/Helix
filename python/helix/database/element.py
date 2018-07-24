import os
import shutil

from helix.database.database import DatabaseObject
from helix.database.show import Show
from helix.database.sequence import Sequence
from helix.database.shot import Shot
from helix.database.person import Person
import helix.environment.environment as env
import helix.utils.utils as utils
from helix.utils.fileclassification import FrameSequence
import helix.utils.fileutils as fileutils
from helix.api.exceptions import PublishError

class Element(DatabaseObject):
	TABLE = 'elements'
	PK = 'id'
	STATUS = {
		0: 'new',
		1: 'assigned',
		2: 'ip',
		3: 'review',
		4: 'done'
	}
	SET = 'set'
	LIGHT = 'light'
	CHARACTER = 'character'
	PROP = 'prop'
	TEXTURE = 'texture'
	EFFECT = 'effect'
	COMP = 'comp'
	CAMERA = 'camera'
	PLATE = 'plate'
	ELEMENT_TYPES = [SET, LIGHT, CHARACTER, PROP, TEXTURE, EFFECT, COMP, CAMERA, PLATE]

	def __init__(self, name, elType, show=None, sequence=None, shot=None, clipName=None, author=None, makeDirs=False, dummy=False):
		self.table = Element.TABLE

		if name:
			sanitary, reasons = utils.isSanitary(name)

			if not sanitary:
				raise ValueError('Invalid element name specified:' + '\n'.join(reasons))

		self.name = name
		self.type = elType
		self.show = show if show else env.getEnvironment('show')
		self.sequence = sequence
		self.shot = shot
		self._exists = None

		self.sequenceId = None
		self.shotId = None

		if dummy:
			return

		if name is None:
			if not shot or not sequence:
				raise ValueError('Element\'s name can only be None (considered nameless) if shot and sequence are also specified')
			else:
				self.name = '_{}{}{}'.format(
						fileutils.SEQUENCE_FORMAT.format(str(self.sequence).zfill(env.SEQUENCE_SHOT_PADDING)),
						fileutils.SHOT_FORMAT.format(str(self.shot).zfill(env.SEQUENCE_SHOT_PADDING)),
						clipName if clipName else ''
					)

		if not elType:
			raise ValueError('Element\'s type can\'t be None')

		self.elType = elType.lower()

		if self.elType not in Element.ELEMENT_TYPES:
			raise ValueError('Invalid element type: {}. Must be one of: {}'.format(self.elType, ', '.join(Element.ELEMENT_TYPES)))

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
			self.status = Element.STATUS[0]
			self.assigned_to = None
			self.pubVersion = 0
			self.version = 1
			self.thumbnail = None
			self.shot_clipName = clipName

			s = Show(self.show)

			if not s.exists():
				raise ValueError('No such show: {}'.format(show))

			p = Person(self.author)

			if not p.exists():
				raise ValueError('No such user: {}'.format(self.author))

			baseWorkDir = s.work_path
			baseReleaseDir = s.release_path

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

				baseWorkDir = sq.work_path
				baseReleaseDir = sq.release_path

			if self.shot is not None and self.sequence is not None:
				try:
					self.shot = int(shot)
				except ValueError:
					raise ValueError('Shot number must be a number, not: {}'.format(shot))

				sh = Shot(self.shot, self.sequence, show=self.show, clipName=self.shot_clipName)

				if not sh.exists():
					raise ValueError('No such shot {} in sequence {} in show {}'.format(sh.num, sh.sequence, sh.show))
				else:
					self.shotId = sh.id

				baseWorkDir = sh.work_path
				baseReleaseDir = sh.release_path

			self.work_path = os.path.join(baseWorkDir, self.directory)
			self.release_path = os.path.join(baseReleaseDir, self.directory)

			if makeDirs:
				if not os.path.isdir(self.work_path):
					os.makedirs(self.work_path)

				if not os.path.isdir(self.release_path):
					os.makedirs(self.release_path)

	def rollback(self, version=None):
		"""Switches the current version of this file to an already existing published version.
		The on disk versionless file in the release directory has its link updated to reflect
		this change.

		If version is not specified, tries to rollback to the previous version.

		Args:
			version (int, optional): The version to change to. If this version doesn't exist on
				disk, or is less than 1 the rollback fails.

		Returns:
			bool: If the rollback succeeded or not.
		"""
		versionsDir = os.path.join(self.release_path, '.versions')
		currVersion = self.pubVersion
		prevVersion = int(currVersion) - 1 if not version else int(version)

		if currVersion == 0:
			raise PublishError('No published records for this element.')

		if prevVersion < 1:
			raise PublishError('Cannot rollback prior to version 1. Current version found: {}'.format(currVersion))

		if prevVersion == currVersion:
			raise PublishError('The asset is already set to version {}'.format(prevVersion))

		prevPf = self.getPublishedFileByVersion(prevVersion)

		if not prevPf:
			raise PublishError('Unable to find record of PublishedFile with version: {}'.format(prevVersion))

		prevFiles = prevPf.getFilePaths()

		if not prevFiles:
			# Nothing found by glob, files deleted?
			raise PublishError('No files found for previously published version: {}'.format(prevVersion))

		# Remove old versionless
		for root, dirs, files in os.walk(self.release_path):
			if '.versions' in root.split(os.sep):
				continue
			for d in dirs:
				if d == '.versions':
					continue
				shutil.rmtree(os.path.join(root, d))
			for f in files:
				os.remove(os.path.join(root, f))

		for path in prevFiles:
			framePadding = fileutils.getFramePadding(os.path.split(path)[-1])
			_, ext = os.path.splitext(path)
			versionlessName = '{}{}{}'.format(self.name, '.' + framePadding if framePadding else '', ext if not os.path.isdir(path) else '')
			versionlessDest = os.path.join(self.release_path, versionlessName)

			if os.path.isdir(path):
				if not os.path.isdir(versionlessDest):
					os.mkdir(versionlessDest)

			fileutils.linkPath(path, versionlessDest)

		self.set('pubVersion', prevVersion)

	def versionUp(self, sourceFile, range=(), ignoreMissing=False):
		"""Publishes the current element to the next version, copying the proper file(s) to the
		release directory and updating the versionless file to link to this new version.

		Versions are tagged in the element data with the creator and creation date for rollback purposes.

		"pubVersion" reflects what version the versionless file points to, regardless of whether it is the
		latest version or not. When a publish is executed, this is obviously updated to the version that
		was just published.

		Returns:
			bool: Whether the publish action succeeded or not.
		"""

		# If the source file is not an absolute path, the user probably meant it to be
		# passed in relative to the element's work directory
		from helix.database.publishedFile import PublishedFile

		if not os.path.isabs(sourceFile):
			sourceFile = os.path.join(self.work_path, sourceFile)

		if not os.path.exists(sourceFile):
			raise PublishError('The given file doesn\'t exist: {}'.format(sourceFile))

		versionsDir = os.path.join(self.release_path, '.versions')

		if not os.path.exists(versionsDir):
			os.makedirs(versionsDir)

		sequence = FrameSequence(sourceFile, range=range)
		isSeq = sequence.getRange() != ()

		if isSeq:
			if not sequence.isValid():
				raise PublishError('No associated sequence found for the file given: {}'.format(sourceFile))

			missing = sequence.getMissingFrames()

			if missing and not ignoreMissing:
				raise PublishError('Missing frames from sequence: {}'.format(FrameSequence.prettyPrintFrameList(missing)))

			versionedSeq = self.publishFile(sequence)
			pf = PublishedFile(self.name, self.type, versionedSeq, show=self.show, sequence=self.sequence, shot=self.shot)
			pf.insert()
			self.set('pubVersion', pf.version)
		else:
			versioned = self.publishFile(sourceFile)
			pf = PublishedFile(self.name, self.type, versioned, show=self.show, sequence=self.sequence, shot=self.shot)
			pf.insert()
			self.set('pubVersion', pf.version)

		self.set('version', self.version + 1)

	def publishFile(self, fileName):
		"""Given any arbitrary file name, determines if the file is a single file, part of a sequence, or
		a directory and copies it accordingly to the release versions directory of the element. This also
		sets up the hardlink(s) to the new versioned file(s).

		If the incoming file name has a prefix that doesn't match the element's name, it will be
		renamed accordingly.

		Args:
			fileName (str): The current existing file/file from a sequence/directory to publish to the
				release directory

		Returns:
			str: The complete file path to the versioned file/file sequence/directory that was created as a result of the copy process
		"""
		versionsDir = os.path.join(self.release_path, '.versions')

		if isinstance(fileName, FrameSequence):
			print 'Publishing sequence...'
			# Publishing a whole sequence
			newSeq = fileName.copyTo(versionsDir)
			prefix = '{}.{}'.format(self.get('name'), str(self.version).zfill(env.VERSION_PADDING))

			fileName.update(prefix=self.get('name'), changeOnDisk=False)
			fileName.setDir(self.release_path)

			# Update destination file sequence to conform to the expected base name and frame padding
			newSeq.update(prefix=prefix, padding=env.FRAME_PADDING)

			# Remove old versionless
			for root, dirs, files in os.walk(self.release_path):
				if '.versions' in root.split(os.sep):
					continue
				for d in dirs:
					if d == '.versions':
						continue
					shutil.rmtree(os.path.join(root, d))
				for f in files:
					os.remove(os.path.join(root, f))

			# Hard link to versionless
			for versionless, versioned in zip(fileName.getFramesAsFilePaths(), newSeq.getFramesAsFilePaths()):
				os.link(versioned, versionless)

			return newSeq.getFormatted(includeDir=True)
		elif os.path.isdir(fileName):
			print 'Publishing folder...'
			# Directory publish
			baseDirectory = os.path.split(fileName)[-1]
			versionedName = '{}.{}'.format(self.get('name'), str(self.version).zfill(env.VERSION_PADDING))
			versionedDest = os.path.join(versionsDir, versionedName)
			versionlessName = self.get('name')
			versionless = os.path.join(self.release_path, versionlessName)

			# Remove old versionless
			for root, dirs, files in os.walk(self.release_path):
				if '.versions' in root.split(os.sep):
					continue
				for d in dirs:
					if d == '.versions':
						continue
					shutil.rmtree(os.path.join(root, d))
				for f in files:
					os.remove(os.path.join(root, f))

			if not os.path.isdir(versionless):
				os.mkdir(versionless)

			shutil.copytree(fileName, versionedDest)
			fileutils.linkPath(versionedDest, versionless)

			return versionedDest
		else:
			print 'Publishing single file...'
			# Single file publish
			baseName, ext = os.path.splitext(fileName)
			versionedName = '{}.{}{}'.format(self.get('name'), str(self.version).zfill(env.VERSION_PADDING), ext)
			versionedDest = os.path.join(versionsDir, versionedName)
			versionlessName = '{}{}'.format(self.get('name'), ext)
			versionless = os.path.join(self.release_path, versionlessName)

			# Remove old versionless
			for root, dirs, files in os.walk(self.release_path):
				if '.versions' in root.split(os.sep):
					continue
				for d in dirs:
					if d == '.versions':
						continue
					shutil.rmtree(os.path.join(root, d))
				for f in files:
					os.remove(os.path.join(root, f))

			shutil.copy2(fileName, versionedDest)
			os.link(versionedDest, versionless)

			return versionedDest

		# # TODO: make versionless and versionDest read-only?

		# #from stat import S_IREAD, S_IRGRP, S_SIROTH
		# #os.chmod(versionDest, S_IREAD|S_IRGRP|S_SIROTH)
		# #os.chmod(versionlessFile, S_IREAD|S_IRGRP|S_SIROTH)

	def getPublishedVersions(self):
		from helix.database.sql import Manager
		from helix.database.publishedFile import PublishedFile

		with Manager(willCommit=False) as mgr:
			query = """SELECT version FROM {} WHERE show='{}' AND elementId='{}'""".format(PublishedFile.TABLE, self.show, self.id)
			rows = mgr.connection().execute(query).fetchall()

			return [r[0] for r in rows]

	def getPublishedFiles(self, authors=[]):
		from helix.database.sql import Manager
		from helix.database.publishedFile import PublishedFile

		with Manager(willCommit=False) as mgr:
			query = """SELECT * FROM {} WHERE show='{}' AND elementId='{}'""".format(PublishedFile.TABLE, self.show, self.id)

			if authors is not None:
				if isinstance(authors, str):
					authors = [authors]
				if authors:
					query += " AND author in ({})".format(','.join(["'{}'".format(n) for n in authors]))

			pfs = []

			for row in mgr.connection().execute(query).fetchall():
				pfs.append(PublishedFile.dummy().unmap(row))

			return pfs

	def getPublishedFileByVersion(self, version, authors=[]):
		from helix.database.sql import Manager
		from helix.database.publishedFile import PublishedFile

		version = int(version)

		with Manager(willCommit=False) as mgr:
			query = """SELECT * FROM {} WHERE show='{}' AND elementId='{}' AND version='{}'""".format(PublishedFile.TABLE, self.show, self.id, version)

			if authors is not None:
				if isinstance(authors, str):
					authors = [authors]
				if authors:
					query += " AND author in ({})".format(','.join(["'{}'".format(n) for n in authors]))

			row = mgr.connection().execute(query).fetchone()

			if row and row[0]:
				return PublishedFile.dummy().unmap(row)
			else:
				return None

	def clone(self, container):
		el = container.getElement(self.name, self.type)

		if el:
			raise DatabaseError('Element already exists at the given location')

		el = Element(self.name, self.type, show=container.show, sequence=container.sequence, shot=container.shot)
		el.insert()

		return el

	def __str__(self):
		return self.name + ' (' + self.type + ')'

	@property
	def id(self):
		return super(Element, self)._id(
			'{}_{}_{}_{}_{}'.format(
				self.show,
				self.sequence if self.sequence else '',
				self.shot if self.shot else '',
				self.name,
				self.type
			)
		)

	@property
	def directory(self):
		nameDir = '' if self.name.startswith('_') else self.name
		return os.path.join(self.type, nameDir)

	@property
	def pk(self):
		return Element.PK

	@staticmethod
	def dummy():
		return Element('aa', Element.ELEMENT_TYPES[0])
