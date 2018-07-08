from PyQt4.QtCore import *
from PyQt4.QtGui import *
import os

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

class FileChooserLayout(QHBoxLayout):
	FILE = 0
	FOLDER = 1
	ANY = 2

	fileChosenSignal = pyqtSignal(str)

	def __init__(self, parent, label=None, defaultText='', browseCaption='', filter='', selectionMode=FILE, completer=True):
		super(FileChooserLayout, self).__init__()

		self.parent = parent
		self.selectionMode = selectionMode
		self.caption = browseCaption
		self.filter = filter

		self.LNE_selection = QLineEdit()

		if defaultText:
			self.LNE_selection.setText(defaultText)

		if completer:
			self.completer = FilePathCompleter(self.LNE_selection, startDir=self.LNE_selection.text())
			self.LNE_selection.setCompleter(self.completer)

		iconProvider = QFileIconProvider()
		self.BTN_select = QPushButton(iconProvider.icon(QFileIconProvider.Folder), '')

		if label:
			self.addWidget(QLabel(label))

		self.addWidget(self.LNE_selection)
		self.addWidget(self.BTN_select)

		self.makeConnections()

	def getFile(self):
		return str(self.LNE_selection.text())

	def makeConnections(self):
		self.BTN_select.clicked.connect(self.handleBrowse)
		self.LNE_selection.textChanged.connect(self.handleFileChange)

	def handleFileChange(self):
		self.fileChosenSignal.emit(str(self.LNE_selection.text()))

	def handleBrowse(self):
		start = str(self.LNE_selection.text()) if os.path.exists(str(self.LNE_selection.text())) else os.path.expanduser('~')
		fileMode = QFileDialog.AnyFile
		option = 0

		if self.selectionMode == FileChooserLayout.FILE:
			fileMode = QFileDialog.ExistingFile
		elif self.selectionMode == FileChooserLayout.FOLDER:
			fileMode = QFileDialog.Directory
			option = QFileDialog.ShowDirsOnly

		dialog = QFileDialog(self.parent, caption=self.caption if self.caption else 'Browse', filter=self.filter, directory=start, options=option)
		dialog.setFileMode(fileMode)
		dialog.exec_()

		selected = dialog.selectedFiles()
		file = None

		if len(selected) >= 1:
			file = str(selected[0])

		if file and os.path.exists(file):
			self.LNE_selection.setText(file)
			self.fileChosenSignal.emit(file)
