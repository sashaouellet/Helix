"""Represents different collections/specifications for file(s) i.e. shots, sequences, image, scripts, etc.

__author__ = Sasha Ouellet (www.sashaouellet.com)
__version__ = 1.0.0
__date__ = 11/27/17
"""

import os, re, shutil

class FrameSequence():
	FRAME_NAME_PATTERN = r'^(?P<prefix>{})[\.\-_](?P<framePadding>\d+)\.(?P<ext>{})$'
	STANDARD_FRAME_FORMAT = '#'
	HOUDINI_FRAME_FORMAT = '$F'
	GLOB_FORMAT = '[0-9]'

	def __init__(self, path, range=(), prefix=r'[\w\-\.]+', ext=r'[a-zA-Z]+', padding=0):
		self._range = ()
		self._index = 0

		if os.path.isdir(path):
			self._dir = path
			self._frames = self._getFrameListFromDir(self._dir, prefix, ext, range, padding)
		else:
			self._dir, fileName = os.path.split(path)
			decomp = FrameSequence._decompose(fileName, prefix=prefix, ext=ext)

			if not decomp:
				self._frames = []
			elif isinstance(decomp, tuple):
				prefix, _, ext = decomp

			if not prefix or not ext:
				# Not part of a sequence
				self._frames = []
			else:
				# Version number could have been accidentally interpreted as a frame number, check if there are multiple frames
				self._frames = self._getFrameListFromDir(self._dir, prefix, ext, range, padding)

				if len(self._frames) == 1:
					# Only 1 frame in this supposed "sequence," probably just a version number
					self._frames = []

		if self._frames:
			self._range = (self._frames[0].getNumber(), self._frames[-1].getNumber())

	def isValid(self):
		"""A Sequence is valid if frames have been found and the range of these frames
		has been calculated.

		Returns:
		    bool: If this Sequence is valid or not
		"""
		return len(self._frames) > 0 and self._range != ()

	def _getFrameListFromDir(self, dir, prefix, ext, range, padding):
		"""Given a directory to look in, retrieves the first found sequence that fits
		the given specifications for prefix and extension. If the range specified
		is not an empty tuple, the frame list returned is limited to that range

		Args:
			dir (str): The directory path to look for a sequence in
			prefix (str): A pattern to match the prefix of the file name against
			ext (str): A pattern to match the extension of the file against
			range (tuple): A tuple representing the allowed start and end range of
				the returned frame lisr. If empty, the full range found is returned

		Returns:
			list: The frame list for the sequence found, empty if no sequence was found
		"""
		frameList = []
		foundArbitrary = False

		for f in os.listdir(dir):
			parts = FrameSequence._decompose(f, prefix=prefix, ext=ext)

			if parts:
				frame = Frame(parts[0], parts[1], parts[2], dir)

				if not foundArbitrary:
					prefix = parts[0].replace('.', '\.').replace('-', '\-')
					ext = parts[2]
					padding = frame.getPadding()

					foundArbitrary = True
				else:
					if len(parts[1]) != padding: # Must continue to match padding length
						continue

				# Is the found frame within the range, if we have specified a range to look for?
				if range != ():
					if frame.getNumber() < range[0] or frame.getNumber() > range[1]: # Nope, out of range
						continue

				frameList.append(frame)

		frameList.sort(key=lambda f: f.getNumber())

		return frameList

	@staticmethod
	def _decompose(file, prefix, ext):
		"""Decomposes the given file name into its 3 parts: prefix, frame
		padding, and extension

		Returns None if any of the 3 parts are missing

		This makes some assumptions on the standard convention of how frames are
		labeled, in that the frame number occurs as the last string of digits before
		the extension, and is separated from the rest of the file name by one of: '. _ -'

		Args:
			file (str): The file name to check, assumed to be only the file
				name, not a full path
			prefix (str, optional): The prefix pattern that must be matched, by default
				is a generic alphanumeric regex
			ext (str, optional): The extension pattern to match, by default is any extension

		Returns:
			tuple: A tuple containing the value of the 3 parts: file name prefix, frame padding,
				and extension. Returns None if any of these 3 parts was not matched in the file
				given
		"""

		pattern = FrameSequence.FRAME_NAME_PATTERN.format(prefix, ext)
		regx = re.compile(pattern)
		match = regx.match(file)

		if match:
			return match.groups()

		return None

	def getFrames(self):
		return self._frames

	def getFramesAsFilePaths(self):
		return [os.path.join(self._dir, f.getPath()) for f in self._frames]

	def getFramesAsNumberList(self):
		return [f.getNumber() for f in self._frames]

	def getDir(self):
		return self._dir

	def setDir(self, dir):
		self._dir = dir

		for f in self._frames:
			f._dir = dir

	def getRange(self):
		return self._range

	def getLength(self):
		return self._range[1] - self._range[0] + 1

	def getPadding(self):
		return self._frames[0].getPadding()

	def getPrefix(self):
		return self._frames[0].getPrefix()

	def getExt(self):
		return self._frames[0].getExt()

	def update(self, padding=None, ext=None, prefix=None, changeOnDisk=True):
		for f in self._frames:
			f.update(padding=padding, ext=ext, prefix=prefix, changeOnDisk=changeOnDisk)

	def offset(self, amount):
		for f in self._frames:
			newNum = f.getNumber() + amount

			f.update(number=newNum)

		self._range = (self.range[0] + amount, self.range[1] + amount)

	def copyTo(self, dest):
		"""Copies the entire FrameSequence (simply all of its Frames) to the given destination,
		which must be a directory.

		Args:
		    dest (str): The directory to copy the Frames to

		Returns:
		    FrameSequence: A FrameSequence object representing the newly copied frames (the frames at the destination).
		    	This is a convenience for then modifying the copied Frames.

		Raises:
		    ValueError: When the given destination 'dest' does not exist or is not a directory
		"""
		if not os.path.exists(dest):
			raise ValueError('The given destination does not exist')

		if not os.path.isdir(dest):
			raise ValueError('This operation can only be performed when copying to a directory. {} is not a directory.'.format(dest))

		for f in self._frames:
			shutil.copy2(f.getPath(), dest)

		seq = FrameSequence(dest, range=self._range, ext=self.getExt(), prefix=self.getPrefix(), padding=self.getPadding())

		assert seq.isValid()

		return seq

	def getMissingFrames(self, format=False):
		"""Gets the list of frame numbers that are missing from this sequence

		Returns:
			list: The list of missing frame numbers

		Args:
			format (bool, optional): Convenience for immediately returning a formatted
				list of the missing frames. By default still returns the list, when True
				returns a string with the pretty-printed list
		"""
		current = self.getFramesAsNumberList()
		missing = []

		for i in range(*self._range):
			if i not in current:
				missing.append(i)

		if format:
			return FrameSequence.prettyPrintFrameList(missing)

		return missing

	def getFormatted(self, format='#', includeDir=False):
		"""Constructs the string format of the file name that represents the
		entire sequence, using the given format as the wildcard replacement
		for the frame number in the file name

		Ex (default behavior):

		fooBar.####.exr where '####' is the frame number replacement for 4-digit padding

		Houdini format ('$F') is handled like so:

		fooBar.$F4.exr (again for 4-digit padding)

		Args:
			format (str, optional): The format of the wildcard for the frame number
				replacement. By default uses the standard wildcard '#'
			includeDir (bool, optional): Whether the returned representative string
				should be the full path to the file, or just the file name. By default,
				only the file name is returned

		Returns:
			str: The formatted string representing the whole sequence
		"""
		padding = self.getPadding()
		framePadding = format * padding

		if format == self.HOUDINI_FRAME_FORMAT:
			framePadding = self.HOUDINI_FRAME_FORMAT + padding if padding > 1 else self.HOUDINI_FRAME_FORMAT

		fileName = '{}.{}.{}'.format(self.getPrefix(), framePadding, self.getExt())

		if includeDir:
			return os.path.join(self.getDir(), fileName)

		return fileName

	def __iter__(self):
		return self

	def next(self):
		if self._index == len(self._frames):
			raise StopIteration

		frame = self._frames[self._index]
		self._index += 1

		return frame

	def __next__(self):
		if self._index == len(self._frames):
			raise StopIteration

		frame = self._frames[self._index]
		self._index += 1

		return frame

	@staticmethod
	def prettyPrintFrameList(frames):
		"""Given a list of frames (represented as their
		integers), builds a string representing the combination
		of discrete frames and frame ranges.

		i.e. a list [1, 2, 3, 4, 5, 9, 10, 13, 15] would be formatted
		as: '1-5, 9-10, 13, 15'

		Args:
		    frames (list): The frame list to format

		Returns:
		    str: The formmated frame list
		"""
		parts = []
		currRangeStart = None
		last = None

		for f in frames:
			if not currRangeStart: # First frame of streak
				currRangeStart = f
				last = f

				continue

			if f != last + 1: # End streak
				# Finalize streak
				if currRangeStart == last: # no streak
					parts.append(str(last))
				elif last - currRangeStart == 1: # don't use range format for 1 length streaks
					parts.append(str(currRangeStart))
					parts.append(str(last))
				else:
					parts.append('{}-{}'.format(currRangeStart, last))

				currRangeStart = f # Reset streak and last
				last = f
			else:
				last = f

		if currRangeStart == last:
			parts.append(str(last))
		elif last - currRangeStart == 1:
			parts.append(str(currRangeStart))
			parts.append(str(last))
		else:
			parts.append('{}-{}'.format(currRangeStart, last))

		return ', '.join(parts)

	@staticmethod
	def parseFrameString(frameString):
		"""Given a string representing a sequence of discrete frames and
		ranges of frames, compiles the complete list of the frames.

		i.e. the string '1-3, 5, 9, 10-20:2' will produce [1, 2, 3, 5, 9,
		10, 12, 14, 16, 18, 20]

		Args:
		    frameString (str): The string representing the sequence of discrete
		    	and ranges of frames

		Returns:
		    list: The complete expanded list of the frames compiled from the frame string

		Raises:
		    ValueError: When one of the sequences contains a match, but does not properly match for
		    	the start of the range. Should never occur.
		"""
		blocks = frameString.split(',')
		blockRegex = re.compile(r'(?P<start>\-?\d+)(\-(?P<end>\-?\d+))?(:(?P<inc>\d+))?')
		frameList = []

		for block in blocks:
			block = block.strip()
			match = blockRegex.match(block)

			if match:
				start = match.group('start')
				end = match.group('end')
				end = end if end else start
				inc = match.group('inc')
				inc = inc if inc else 1

				if not start: # not even a single frame number present
					raise ValueError('Error in frame string. Invalid block: {} (expected at least 1 frame number)'.format(block))
					return None

				if end:
					assert int(end) >= int(start), 'End frame in range cannot be smaller than start frame (Block: {})'.format(block)

				for i in range(int(start), int(end) + 1, int(inc)):
					frameList.append(i)

		frameList = list(set(frameList))

		frameList.sort()

		return frameList

	@staticmethod
	def getSequence(file):
		"""Determines the entire image sequence from the single given image file that is a
		part of that sequence

		Args:
		    file (str): The file path for 1 image in the sequence that should be obtained
		"""
		pass

class Frame():
	def __init__(self, prefix, framePadding, ext, directory, frameNumSep='.'):
		self._prefix = prefix
		self._padding, self._number = self._interpretFramePadding(framePadding)
		self._ext = ext
		self._frameNumSep = frameNumSep
		self._dir = directory

	def _interpretFramePadding(self, framePadding):
		"""Given a string that represents the frame padding portion
		of a file, interprets what the actual frame number is and how
		many digits of padding it is composed of

		Ex:

		'0000' --> (4, 0)
		'010'  --> (3, 10)
		'200'  --> (3, 200)

		Args:
			framePadding (str): The frame padding portion of the file name

		Returns:
			tuple: A tuple with the number of digits of padding (0020 is 4 digit padding),
				and the integer value of the frame that the string represents

		Raises:
			ValueError: In the case where we cannot determine the integer value of the
				given frame padding, which means that the string passed is not of the
				expected format of pure digits
		"""

		try:
			frameNum = int(framePadding)

			return (len(framePadding), frameNum)
		except ValueError:
			raise ValueError('Malformed frame padding string: {}'.format(framePadding))

	def getPrefix(self):
		return self._prefix

	def getExt(self):
		return self._ext

	def getPadding(self):
		return self._padding

	def update(self, prefix=None, padding=None, ext=None, number=None, changeOnDisk=True):
		oldName = self.getPath()

		if prefix:
			self._prefix = prefix

		if padding:
			self._padding = padding

		if ext:
			self._ext = ext

		if number:
			self._number = number

		newName = self.getPath()

		if newName != oldName and changeOnDisk: # Don't waste the operation if nothing changed
			os.rename(oldName, newName)

	def getNumber(self):
		return self._number

	def getPath(self):
		fileName = '{}{}{}.{}'.format(self._prefix, self._frameNumSep, str(self._number).zfill(self._padding), self._ext)

		return os.path.join(self._dir, fileName)

	def __str__(self):
		return 'Frame {} from: {} ({})'.format(self._number, self._prefix, self._ext)

# path1 = '/Volumes/Macintosh MD/Users/spaouellet/Downloads/helixImportElTest/foo/foo.0001.txt'
path2 = '/Volumes/Macintosh MD/Users/spaouellet/Documents/houdini/toolTests/render'
dest = '/Volumes/Macintosh MD/Users/spaouellet/Documents/houdini/toolTests/render2'
# seq1 = FrameSequence(path1)
# seq2 = FrameSequence(path2)

# newSeq = seq2.copyTo(dest)

# newSeq.update(prefix='foo.001', padding=6)

# print seq1.getFramesAsNumberList(), seq1.isValid()
# print seq2.getFramesAsNumberList(), seq2.isValid()
