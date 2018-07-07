from PyQt4.QtCore import *
from PyQt4.QtGui import *

class FilePathCompleter(QCompleter):
	def __init__(self, target, startDir=''):
		super(FilePathCompleter, self).__init__(target)

		self.model = QFileSystemModel(self)
		self.model.setRootPath(startDir)

		self.setModel(self.model)

class ExceptionDialog(QMessageBox):
	def __init__(self, exception, msg='', buttons=QMessageBox.Cancel|QMessageBox.Ok, parent=None):
		"""Given any exception, creates a generic dialog to show the user the exception details

		The body of the dialog will default to the exception's message, unless msg is specified.
		In this case, the exception message will be included as detailed text instead.

		The title will be set to the formatted name of the exception, but will not be visible on
		Mac OS X (yay thanks OS X "guidelines" - http://doc.qt.io/archives/qt-4.8/qmessagebox.html#setWindowTitle)
		Args:
		    exception (Exception): The exception to create the dialog for
		    msg (str, optional): Specific message details to include. If present, the exception
		    	message will be included as detail text rather then the main body text of the
		    	dialog
		    buttons (StandardButtons, optional): The buttons to include on the dialog, defaulting
		    	to Cancel and Ok. These should be from the StandardButtons enum in QMessageBox
		    parent (QWidget, optional): The parent of the dialog, usually the application window
		    	the exception originated from.
		"""
		super(ExceptionDialog, self).__init__(QMessageBox.Warning, '', '', buttons=buttons, parent=parent)

		if msg:
			self.setText(msg)
			self.setDetailedText(str(exception))
		else:
			self.setText(str(exception))

		self.setWindowTitle(exception.__class__.__name__)