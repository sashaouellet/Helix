import itertools

STATE_CHANGE = 'CHANGED'
STATE_ADD = 'ADDED'
STATE_REMOVE = 'REMOVED'
IGNORE = 'IGNORE'

class DiffItem(object):
	def __init__(self, path, key, obj1, obj2, val1, val2):
		self.path = [str(v) for v in path]
		self.key = key
		self.obj1 = obj1
		self.obj2 = obj2
		self.val1 = val1
		self.val2 = val2
		self.state = STATE_CHANGE

		if not self.val1 and self.val2:
			self.state = STATE_ADD

		if not self.val2 and self.val1:
			self.state = STATE_REMOVE

	def getFromSet(self, diffSet):
		for diff in diffSet.diffSet:
			if self.path == diff.path and self.key == diff.key:
				return diff

		return None

	def resolve(self, discard=True):
		current = self.obj2
		replacement = self.obj1

		if not discard:
			current = self.obj1
			replacement = self.obj2

		if type(current) in (list, dict) and type(replacement) in (list, dict):
			if len(current) < len(replacement):
				if type(current) != dict:
					current.extend([None] * (len(current) - self.key + 1))
				current[self.key] = replacement[self.key]
			elif len(current) > len(replacement):
				current.pop(self.key)
			else:
				current[self.key] = replacement[self.key]
		elif type(current) is tuple and type(replacement) is tuple:
			current = tuple([v if current.index(v) != self.key else replacement[self.key] for v in current])

			if discard:
				self.obj2 = current
			else:
				self.obj1 = current
		else:
			raise ValueError('Cannot resolve diff conflicts for objects without key-based access (lists, tuples, and dicts)')

	def __repr__(self):
		old = self.val1 if self.val1 else ''
		new = self.val2 if self.val2 else ''
		return '[{}] ({}/{}): {}{}{}'.format(self.state, '/'.join(self.path), self.key, old, ' --> ' if old and new else '', new)

class DiffSet(object):
	def __init__(self):
		self.diffSet = []

	def get(self, otherDiff):
		for diff in self.diffSet:
			if diff.path == otherDiff.path and diff.key == otherDiff.key:
				return diff

		return None

	def add(self, path, key, obj1, obj2, val1, val2):
		self.diffSet.append(DiffItem(path, key, obj1, obj2, val1, val2))

	def merge(self, diffSet):
		self.diffSet.extend(diffSet.diffSet)

	def __repr__(self):
		return '\n'.join(['{}: {}'.format(i, str(item)) for i, item in enumerate(self.diffSet)])

