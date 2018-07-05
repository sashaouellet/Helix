from PyQt4.QtCore import *
from PyQt4.QtGui import *

class FilePathCompleter(QCompleter):
	def __init__(self, target, startDir=''):
		super(FilePathCompleter, self).__init__(target)

		self.model = QFileSystemModel(self)
		self.model.setRootPath(startDir)

		self.setModel(self.model)