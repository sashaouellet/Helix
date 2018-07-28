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

	"""Externally referred to as "Assets", Elements are the children of ElementContainers
	(Shows, Sequences, Shots). They represent any particular asset that can be composed
	together in a shot to produce the final look of the shot. Additionally, an Element
	can be used to create other assets (i.e. texture for a prop or prop in a set).

	Most elements will live under the "Show" scope, unless specifically needed at a more
	granular level. For example, a "plate" element would not live at the Show level,
	since it makes more sense to be tied to a shot - it is the plate for that specific
	shot. The same is true for a "camera" element - it should be tied to a specific shot.

	At an element's work tree location, all files relevant to construction that particular
	element exist. For example, a "prop" element may have a Maya project directory
	structure, some test files, and anything else the artist needs to produce this element.

	At an element's release tree location, all published versions of the element's outcome
	exist. In reality, this is also whatever is chosen by the artist but the theory is that
	for the example "prop" element, the artist would publish versions of an .OBJ (or whatever
	format is chosen).

	Attributes:
	    CAMERA (str): A camera, probably producing an .FBX of the camera location/animation. Usually a part of the shot scope.
	    CHARACTER (str): A character. the model and/or rig could fall under this element type.
	    COMP (str): A Nuke composite. Usually part of the shot scope.
	    EFFECT (str): An effect/simulation, i.e. cloth or hair sim, pyro sim, etc.
	    LIGHT (str): A light or group of lights (light rig). You might produce a sequence scoped light rig that gets used by default, then build shot scoped light rig overrides during the shot lighting stage.
	    PLATE (str): Represents any background element. Could be footage, a matte painting, etc.
	    PROP (str): A model
	    SET (str): An entire set where most other elements will eventually be placed into. The set element would probably be made during the layout stage and would be used for set dressing/final shot creation.
	    TEXTURE (str): Texture map (even a texture set) grouped for a specific other element (i.e a prop or character)

	    ELEMENT_TYPES (list): The list of all the aforementioned element types.
	    STATUS (dict): Maps status number to its string equivalent. Represents the stage within the pipeline that this element's production is in.
		TABLE (str): Description
	    PK (str): Description

	    assigned_to (str): The user the element is assigned to.
	    author (str): The user the element was created by.
	    creation (datetime): When the element was created.
	    name (str): The name of the element. Could be considered "nameless" (only for shot scoped elements). In this case, the element is named after the sequence and shot it's a part of.
	    pubVersion (int): The current version the published files for the element point to. This number is affected by new version and rollbacks.
	    release_path (str): The path to the element's directory in the release tree of the show.
	    sequence (int): The sequence number this element is under the scope of. Could be None if it's a show scoped element.
	    sequenceId (str): The sequence id (PK of the sequence in the sequence table). Could be None if it's a show scoped element.
	    shot (int): The shot number this element is under the scope of. Could be None if it's not in the shot scope.
	    shot_clipName (str): The shot clip name for the shot this element is under the scope of. Could be None if it's not in the shot scope.
	    shotId (str): The shot id (PK of the shot in the shot table). Could be None if it's not in the shot scope.
	    show (str): The alias of the show (PK of the show in the show table) this element is under. All elements are at the very least in the show scope.
	    status (str): The status of this element's production. See STATUS.
	    table (str): The table this element exists in the database. Should be equal to Element.TABLE.
	    thumbnail (str): Path to a thumbnail image showcasing what this element looks like.
	    type (str): One of the element types described above.
	    version (int): The current version that the element is being modified as in the work tree. The next publish of this element will produce this number.
	    work_path (str): The path to the element's directory in the work tree of the show.

	"""

	TABLE = 'elements'
	PK = 'id'
	STATUS = {
		0: 'new',		# The element has just been created
		1: 'assigned',	# The element is assigned to an artist
		2: 'ip',		# The assigned artist has started working on the element
		3: 'review',	# The element may toggle back and forth between 'ip' and 'review' depending on dailies and needs of the production. Review indicates the element is finished as of now and needs to be reviewed.
		4: 'done'		# The production of the element is completely finished.
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

		if name is not None:
			sanitary, reasons = utils.isSanitary(name)

			if not sanitary:
				raise ValueError('Invalid element name specified:' + '\n'.join(reasons))

		self.name = name
		self.type = elType.lower()
		self.show = show if show else env.getEnvironment('show')
		self.sequence = sequence
		self.shot = shot
		self._exists = None

		self.sequenceId = None
		self.shotId = None

		if dummy:
			return

		if name is None:
			if shot is None or sequence is None:
				raise ValueError('Element\'s name can only be None (considered nameless) if shot and sequence are also specified')
			else:
				self.name = '_{}{}{}'.format(
						fileutils.SEQUENCE_FORMAT.format(str(self.sequence).zfill(env.SEQUENCE_SHOT_PADDING)),
						fileutils.SHOT_FORMAT.format(str(self.shot).zfill(env.SEQUENCE_SHOT_PADDING)),
						clipName if clipName else ''
					)

		if not self.type:
			raise ValueError('Element\'s type can\'t be None')

		if self.type not in Element.ELEMENT_TYPES:
			raise ValueError('Invalid element type: {}. Must be one of: {}'.format(self.type, ', '.join(Element.ELEMENT_TYPES)))

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

	@property
	def parent(self):
		if self.shotId is not None:
			return Shot.fromPk(self.shotId)
		elif self.sequenceId is not None:
			return Sequence.fromPk(self.sequenceId)
		else:
			return Show.fromPk(self.show)

	@staticmethod
	def dummy():
		return Element('aa', Element.ELEMENT_TYPES[0])
