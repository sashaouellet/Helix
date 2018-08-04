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

	fileChosen = pyqtSignal(str)

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
		self.fileChosen.emit(str(self.LNE_selection.text()))

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
			self.fileChosen.emit(file)

class ElementListWidgetItem(QListWidgetItem):
	def __init__(self, element, parent=None):
		super(ElementListWidgetItem, self).__init__(parent=parent)

		self.element = element

	def data(self, role):
		if role == Qt.DisplayRole:
			return str(self.element)

class Node(object):
	def __init__(self, data=None, defaultVal=None):
		self._data = data

		if type(data) == tuple:
			self._data = list(data)

		if type(data) in (str, unicode) or not hasattr(data, '__getitem__'):
			self._data = [data]

		self._colCount = len(self._data)
		self._children = []
		self._parent = None
		self._row = 0
		self.default = defaultVal

	def data(self, col):
		if col >= 0 and col < len(self._data):
			return self._data[col]

		return self.default

	def columnCount(self):
		return self._colCount

	def childCount(self):
		return len(self._children)

	def child(self, row):
		if row >= 0 and row < self.childCount():
			return self._children[row]

	def parent(self):
		return self._parent

	def row(self):
		return self._row

	def addChild(self, child):
		child._parent = self
		child._row = len(self._children)
		self._children.append(child)
		self._colCount = max(child.columnCount(), self._colCount)

		return child

class Operation(object):
	def __init__(self, numOps=0, parent=None):
		self.progressDialog = None

		if numOps > 0:
			self.progressDialog = QProgressDialog(parent, Qt.Popup|Qt.WindowStaysOnTopHint|Qt.X11BypassWindowManagerHint)
			self.progressDialog.setMaximum(numOps)
			self.progressDialog.setAutoClose(False)
			self.progressDialog.setMinimumDuration(0)

	def __enter__(self):
		QApplication.instance().setOverrideCursor(QCursor(Qt.WaitCursor))

		if self.progressDialog:
			self.progressDialog.show()
			self.progressDialog.setWindowState(self.progressDialog.windowState() & Qt.WindowMinimized | Qt.WindowActive)
			self.progressDialog.raise_()
			self.progressDialog.activateWindow()
			self.progressDialog.setValue(0)

		return self

	def updateLabel(self, label):
		if self.progressDialog:
			self.progressDialog.setLabelText(label)

	def tick(self):
		if self.progressDialog:
			self.progressDialog.setValue(self.progressDialog.value() + 1)

	def __exit__(self, exception_type, exception_value, traceback):
		if self.progressDialog:
			self.progressDialog.setValue(self.progressDialog.maximum())
			self.progressDialog.close()
		QApplication.instance().restoreOverrideCursor()



