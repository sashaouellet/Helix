class HelixException(BaseException):
	pass

class DatabaseError(HelixException):
	"""Defines an error that took place with certain database operations. This custom error
	is necessary for certain try statements so that we do not preemptively quit while the user
	is operating on elements, shots, etc.
	"""
	pass

class MergeConflictError(HelixException):
	"""Represents an error that occurs during attempting the save the Database object. Any conflicting changes
	with what is on disk vs. in memory will raise this error.
	"""
	pass

class PublishError(HelixException):
	"""Represents an error that occurs during publishing, i.e. the publish file not being found
	"""
	pass

class ImportError(HelixException):
    """Represents an error that occurs when an Element is imported from pre-existing files
    """
    pass
