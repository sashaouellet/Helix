import helix
from helix.database.database import *
import helix.api.commands as cmds
import helix.environment.environment as env
import helix.utils.fileutils as fileutils
from helix.manager.dailies import SlapCompDialog
from helix.manager.config import ConfigEditorDialog
from helix.utils.qtutils import ExceptionDialog

import qdarkstyle

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic

import os
from datetime import datetime

class Node(object):
	def __init__(self, data=None):
		self._data = data

		if type(data) == tuple:
			self._data = list(data)

		if type(data) in (str, unicode) or not hasattr(data, '__getitem__'):
			self._data = [data]

		self._colCount = len(self._data)
		self._children = []
		self._parent = None
		self._row = 0

	def data(self, col):
		if col >= 0 and col < len(self._data):
			return self._data[col]

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

class ShowModel(QAbstractItemModel):
	def __init__(self, shows, parent=None):
		super(ShowModel, self).__init__(parent)

		self.setShows(shows)

	def setShows(self, shows):
		self.beginResetModel()

		self._root = Node()

		shows.sort(key=lambda s: s.get('name'))

		for show in shows:
			showNode = self._root.addChild(Node(show))
			seqs = show.getSequences()

			seqs.sort(key=lambda s: s.get('num'))

			for seq in seqs:
				seqNode = showNode.addChild(Node(seq))
				shots = seq.getShots()

				shots.sort(key=lambda s: s.get('num'))

				for shot in shots:
					seqNode.addChild(Node(shot))

		self.endResetModel()

	def columnCount(self, index):
		if index.isValid():
			return index.internalPointer().columnCount()

		return self._root.columnCount()

	def rowCount(self, index):
		if index.isValid():
			return index.internalPointer().childCount()

		return self._root.childCount()

	def data(self, index, role):
		if not index.isValid():
			return QVariant()

		node = index.internalPointer()

		if node and role == Qt.DisplayRole:
			return str(node.data(index.column()))

		return QVariant()

	def addChild(self, node, parent):
		if not parent or not parent.isValid():
			parent = self._root
		else:
			parent = parent.internalPointer()
		parent.addChild(node)

	def index(self, row, col, parent=QModelIndex()):
		if not self.hasIndex(row, col, parent):
			return QModelIndex()

		if not parent or not parent.isValid():
			parent = self._root
		else:
			parent = parent.internalPointer()

		child = parent.child(row)

		if child:
			return self.createIndex(row, col, child)
		else:
			return QModelIndex()

	def parent(self, index):
		if index.isValid():
			p = index.internalPointer().parent()

			if p:
				if p == self._root:
					return QModelIndex()
				else:
					return QAbstractItemModel.createIndex(self, p.row(), 0, p)

		return QModelIndex()

class ElementTableItem(QLabel):
	DATA_MAPPING = ['type', 'name']

	def __init__(self, el, col, parent):
		super(ElementTableItem, self).__init__('')

		self.parent = parent
		self.element = el
		self.setText(self.element.get(ElementTableItem.DATA_MAPPING[col]))

		self.explorerAction = QAction('Open file location', self)
		self.exploreReleaseAction = QAction('Open release directory', self)
		self.publishAction = QAction('Publish', self)
		self.rollbackAction = QAction('Rollback...', self)
		self.propertiesAction = QAction('Properties...', self)

		# No rollback option if we have no publishes for the element
		if not self.element.get('pubVersion'):
			self.rollbackAction.setEnabled(False)

		self.setContextMenuPolicy(Qt.ActionsContextMenu)

		self.addAction(self.explorerAction)
		self.addAction(self.exploreReleaseAction)
		self.addAction(self.publishAction)
		self.addAction(self.rollbackAction)
		self.addAction(self.propertiesAction)

		self.explorerAction.triggered.connect(lambda: self.handleExplorer(True))
		self.exploreReleaseAction.triggered.connect(lambda: self.handleExplorer(False))
		self.publishAction.triggered.connect(self.handlePublish)
		self.rollbackAction.triggered.connect(self.handleRollback)
		self.propertiesAction.triggered.connect(self.parent.handleElementEdit)

	def handleExplorer(self, work):
		path = self.element.getDiskLocation(workDir=work)

		fileutils.openPathInExplorer(path)

	def handlePublish(self):
		env.element = self.element

		try:
			cmds.pub()
			QMessageBox.warning(self, 'Publish', 'Successfully published new version')
		except PublishError, e:
			QMessageBox.warning(self, 'Publish error', str(e))
			return

	def handleRollback(self):
		self.parent.rollbackDialog.show(self.element)

class NewShowDialog(QDialog):
	def __init__(self, parent):
		super(NewShowDialog, self).__init__(parent)

	def makeConnections(self):
		self.BTN_create.clicked.connect(self.accept)
		self.BTN_cancel.clicked.connect(self.reject)
		self.LNE_name.textChanged.connect(self.checkCanCreate)

	def checkCanCreate(self, text):
		self.BTN_create.setEnabled(str(text).strip() != '')

	def accept(self):
		showName, aliases = self.getInputs()
		aliases = [a.strip() for a in aliases.split(',')]

		cmds.mkshow(showName)

		show = self.parent().db.getShow(showName)

		show.set('aliases', aliases)

		self.parent().db.save()
		self.parent().handleDBReload()

		super(NewShowDialog, self).accept()

	def show(self):
		self.LNE_name.setText('')
		self.LNE_aliases.setText('')

		self.checkCanCreate('')
		super(NewShowDialog, self).show()

	def getInputs(self):
		return (str(self.LNE_name.text()).strip(), str(self.LNE_aliases.text()).strip())

class NewSequenceDialog(QDialog):
	def __init__(self, parent):
		super(NewSequenceDialog, self).__init__(parent)

	def makeConnections(self):
		self.BTN_create.clicked.connect(self.accept)
		self.BTN_cancel.clicked.connect(self.reject)
		self.LNE_number.textChanged.connect(self.checkCanCreate)

	def checkCanCreate(self, text):
		try:
			text = int(text)
			self.BTN_create.setEnabled(True)
		except ValueError:
			self.BTN_create.setEnabled(False)

	def accept(self):
		seqNum = int(self.LNE_number.text())

		cmds.pop(self._show.get('name'))

		try:
			cmds.mkseq(seqNum)
			self.parent().handleDBReload()
			super(NewSequenceDialog, self).accept()
		except Exception, e:
			QMessageBox.warning(self, 'Sequence creation error', str(e))
			return

	def show(self, showObj):
		self._show = showObj

		self.LNE_number.setText('')
		self.LBL_show.setText(str(self._show))

		self.checkCanCreate('')
		super(NewSequenceDialog, self).show()

class NewShotDialog(QDialog):
	def __init__(self, parent):
		super(NewShotDialog, self).__init__(parent)

	def makeConnections(self):
		self.BTN_create.clicked.connect(self.accept)
		self.BTN_cancel.clicked.connect(self.reject)
		self.LNE_number.textChanged.connect(self.checkCanCreate)
		self.LNE_start.textChanged.connect(self.checkCanCreate)
		self.LNE_end.textChanged.connect(self.checkCanCreate)

	def checkCanCreate(self):
		try:
			shotNum = int(self.LNE_number.text())
			start = int(self.LNE_start.text())
			end = int(self.LNE_end.text())

			self.BTN_create.setEnabled(True)
		except ValueError:
			self.BTN_create.setEnabled(False)

	def accept(self):
		shotNum, start, end, clipName = self.getInputs()

		cmds.pop(self._show.get('name'))

		try:
			cmds.mkshot(self._seq.get('num'), shotNum, start, end, clipName)
			self.parent().handleDBReload()
			super(NewShotDialog, self).accept()
		except Exception, e:
			QMessageBox.warning(self, 'Shot creation error', str(e))
			return

	def show(self, showObj, seqObj):
		self._show = showObj
		self._seq = seqObj

		self.LNE_number.setText('')
		self.LNE_start.setText('')
		self.LNE_end.setText('')
		self.LNE_clip.setText('')
		self.LBL_show.setText(str(self._show))
		self.LBL_seq.setText(str(self._seq))

		self.checkCanCreate()
		super(NewShotDialog, self).show()

	def getInputs(self):
		shotNum = int(self.LNE_number.text())
		start = int(self.LNE_start.text())
		end = int(self.LNE_end.text())
		clipName = str(self.LNE_clip.text()).strip()

		return (shotNum, start, end, clipName)

class NewElementDialog(QDialog):
	def __init__(self, parent):
		super(NewElementDialog, self).__init__(parent)

	def makeConnections(self):
		self.BTN_create.clicked.connect(self.accept)
		self.BTN_cancel.clicked.connect(self.reject)
		self.LNE_name.textChanged.connect(self.checkCanCreate)
		self.CHK_nameless.stateChanged.connect(self.handleNamelessStateChange)

	def handleNamelessStateChange(self, state):
		self.LNE_name.setEnabled(state == Qt.Unchecked)
		self.checkCanCreate('')

	def checkCanCreate(self, text):
		self.BTN_create.setEnabled(str(text).strip() != '' or self.CHK_nameless.checkState() == Qt.Checked)

	def accept(self):
		name, elType = self.getInputs()

		cmds.pop(self._show.get('name'))

		seq = self._seq.get('num') if self._seq else None
		shot = self._shot.get('num') if self._shot else None

		try:
			cmds.mke(elType, name, sequence=seq, shot=shot)
			self.parent().handleDBReload()
			super(NewElementDialog, self).accept()
		except DatabaseError, e:
			QMessageBox.warning(self, 'Element creation error', str(e))
			return
		except MergeConflictError, e:
			self.parent().handleSaveConflict(e)
		except Exception as e:
			ExceptionDialog(e, msg='Some other detail text', parent=window).exec_()

	def show(self, showObj, seqObj, shotObj):
		self._show = showObj
		self._seq = seqObj
		self._shot = shotObj
		container = self._shot if self._shot else self._seq
		container = container if container else self._show

		self.LNE_name.setEnabled(True)
		self.LNE_name.setText('')
		self.CMB_type.clear()
		self.CMB_type.addItems(Element.ELEMENT_TYPES)
		self.CMB_type.setCurrentIndex(0)
		self.CHK_nameless.setCheckState(Qt.Unchecked)
		self.CHK_nameless.setVisible(self._seq is not None and self._shot is not None)
		self.LBL_container.setText(str(container))

		self.checkCanCreate('')

		super(NewElementDialog, self).show()

	def getInputs(self):
		name = str(self.LNE_name.text()).strip() if self.CHK_nameless.checkState() == Qt.Unchecked else '-'
		elType = str(self.CMB_type.currentText())

		return (name, elType)

class RollbackDialog(QDialog):
	def __init__(self, parent):
		super(RollbackDialog, self).__init__(parent)

	def makeConnections(self):
		self.BTN_rollback.clicked.connect(self.accept)
		self.BTN_cancel.clicked.connect(self.reject)

	def accept(self):
		rollbackVer = int(self.CMB_rollback.currentText())

		try:
			env.element = self._element

			cmds.roll(rollbackVer)
			super(RollbackDialog, self).accept()
		except Exception, e:
			QMessageBox.warning(self, 'Rollback error', str(e))
			return

	def show(self, element):
		self._element = element

		self.LBL_pubVersion.setText(str(element.get('pubVersion', '--')))
		self.CMB_rollback.clear()

		verInfo = element.getPublishedVersions()

		self.CMB_rollback.addItems([str(ver.get('version')) for ver in verInfo])

		super(RollbackDialog, self).show()

class PropertyValueWidgetItem(QTableWidgetItem):
	def __init__(self, text, obj):
		super(PropertyValueWidgetItem, self).__init__(text)

		self._obj = obj

	def __repr__(self):
		return

class PropertyValueModel(QAbstractItemModel):
	def __init__(self, root, parent=None):
		super(PropertyValueModel, self).__init__(parent=parent)

		self.root = root

	def columnCount(self, index):
		return 2

	def rowCount(self, index):
		len([k for k in self.root._data.keys() if k not in ('_DBOType', 'elements', 'sequences', 'shots')])

	def data(self, index, role):
		if not index.isValid():
			return QVariant()

		item = index.internalPointer()

		if node and role == Qt.DisplayRole:
			return str(item)

		return QVariant()

class EditingDialog(QDialog):
	def __init__(self, parent):
		super(EditingDialog, self).__init__(parent)

	def setItem(self, item):
		propBlacklist = ['_DBOType', 'elements', 'sequences', 'shots']
		self.item = item

		self.setWindowTitle('Editing {}'.format(str(self.item)))
		self.TBL_properties.clearContents()
		self.TBL_properties.setRowCount(0)

		row = 0

		for parm, val in item._data.iteritems():
			if str(parm) in propBlacklist:
				continue

			self.TBL_properties.insertRow(row)

			propItem = QTableWidgetItem(parm)

			#if type(val) in (dict, list, tuple, set):
				#if type(val) == dict:
					#valItem = QTableWidget(self.TBL_properties)

					#valItem.setColumnCount(2)
					#valItem.horizontalHeader().hide()
					#valItem.verticalHeader().hide()

					#r = 0

					#for p, v in val.iteritems():
						#if str(p) in propBlacklist:
							#continue

						#valItem.insertRow(r)
						#valItem.setItem(r, 0, QTableWidgetItem(str(p)))
						#valItem.setItem(r, 1, QTableWidgetItem(str(v)))

						#r += 1

					#valItem.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)
				#else:
					#val = list(val)
					#valItem = QListWidget(self.TBL_properties)

					#for r, v in enumerate(val):
						#valItem.insertItem(r, str(v))

				#self.TBL_properties.setCellWidget(row, 1, valItem)
			#else:
				#valItem = QTableWidgetItem(str(val))

				#self.TBL_properties.setItem(row, 1, valItem)

			valItem = QTableWidgetItem(str(val))

			self.TBL_properties.setItem(row, 1, valItem)
			propItem.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
			self.TBL_properties.setItem(row, 0, propItem)

			row += 1

		self.TBL_properties.verticalHeader().setResizeMode(QHeaderView.ResizeToContents)
		self.show()

	def makeConnections(self):
		self.BTN_cancel.clicked.connect(self.reject)
		self.BTN_save.clicked.connect(self.accept)
		self.BTN_new.clicked.connect(self.handleNewParm)

	def handleNewParm(self):
		row = self.TBL_properties.rowCount()

		self.TBL_properties.insertRow(row)

		propItem = QTableWidgetItem('property')

		self.TBL_properties.setItem(row, 0, propItem)
		self.TBL_properties.setItem(row, 1, QTableWidgetItem('value'))

		# Now set it up so that the new property is instantly in edit mode

		self.TBL_properties.setCurrentItem(propItem)

		idx = self.TBL_properties.model().index(row, 0, QModelIndex())

		self.TBL_properties.edit(idx)

	def accept(self):
		super(EditingDialog, self).accept()

class ImportElementDialog(QDialog):
	def __init__(self, parent):
		super(ImportElementDialog, self).__init__(parent)

	def makeConnections(self):
		self.BTN_cancel.clicked.connect(self.reject)
		self.BTN_import.clicked.connect(self.accept)
		self.BTN_file.clicked.connect(self.handleFileImport)
		self.BTN_folder.clicked.connect(self.handleFolderImport)
		self.LNE_folder.textChanged.connect(self.handleFolderChange)
		self.LNE_file.textChanged.connect(self.handleFileChange)
		self.CHK_nameless.clicked.connect(self.handleNamelessToggle)
		self.CMB_show.currentIndexChanged.connect(self.populateSeqAndShot)
		self.CMB_seq.currentIndexChanged.connect(self.populateShots)

	def handleNamelessToggle(self):
		self.LBL_name.setEnabled(not self.CHK_nameless.isChecked())
		self.LNE_name.setEnabled(not self.CHK_nameless.isChecked())

	def populateShots(self):
		self.CMB_shot.clear()

		seq = str(self.CMB_seq.currentText())

		if not seq:
			self.CMB_shot.addItems([])
			return

		seq = env.show.getSequence(seq)
		shots = [str(s.get('num')) for s in seq.getShots()]

		self.CMB_shot.addItems(sorted(shots, key=lambda s: int(s)))
		self.CMB_shot.setCurrentIndex(0)

	def populateSeqAndShot(self):
		self.CMB_seq.clear()
		cmds.pop(str(self.CMB_show.currentText()))

		seqs = [str(s.get('num')) for s in env.show.getSequences()]

		self.CMB_seq.addItems(sorted(seqs))
		self.CMB_seq.setCurrentIndex(0)
		self.populateShots()

	def handleFileImport(self):
		self.LNE_file.setText(QFileDialog.getOpenFileName(self, 'Work File', str(self.LNE_folder.text()).strip()))

		self.handleFileChange()

	def handleFolderChange(self):
		text = str(self.LNE_folder.text()).strip()
		cond = os.path.exists(text) and os.path.isdir(text)

		self.LBL_file.setEnabled(cond)
		self.LNE_file.setEnabled(cond)
		self.BTN_file.setEnabled(cond)
		self.CHK_importAll.setEnabled(cond)

	def handleFileChange(self):
		text = str(self.LNE_file.text()).strip()
		cond = os.path.exists(text)

		self.LBL_name.setEnabled(cond)
		self.LNE_name.setEnabled(cond)
		self.CHK_nameless.setEnabled(cond)

		self.LBL_type.setEnabled(cond)
		self.CMB_type.setEnabled(cond)

		self.LBL_container.setEnabled(cond)
		self.LBL_show.setEnabled(cond)
		self.CMB_show.setEnabled(cond)
		self.LBL_seq.setEnabled(cond)
		self.CMB_seq.setEnabled(cond)
		self.LBL_shot.setEnabled(cond)
		self.CMB_shot.setEnabled(cond)

	def handleFolderImport(self):
		self.LNE_folder.setText(QFileDialog.getExistingDirectory(self, caption='Element Folder'))

		self.handleFolderChange()

	def accept(self):
		super(ImportElementDialog, self).accept()

	def show(self):
		self.LNE_folder.setText('')
		self.CHK_importAll.setEnabled(False)

		self.LBL_file.setEnabled(False)
		self.LNE_file.setEnabled(False)

		self.LBL_name.setEnabled(False)
		self.LNE_name.setEnabled(False)
		self.LNE_name.setText('')
		self.CHK_nameless.setEnabled(False)

		self.LBL_type.setEnabled(False)
		self.CMB_type.setEnabled(False)
		self.CMB_type.clear()
		self.CMB_type.addItems(Element.ELEMENT_TYPES)
		self.CMB_type.setCurrentIndex(0)

		self.LBL_container.setEnabled(False)
		self.LBL_show.setEnabled(False)
		self.CMB_show.setEnabled(False)
		self.CMB_show.addItems([s.get('name') for s in self.parent().db.getShows()])
		self.CMB_show.setCurrentIndex(0)
		self.LBL_seq.setEnabled(False)
		self.CMB_seq.setEnabled(False)
		self.CMB_seq.clear()
		self.LBL_shot.setEnabled(False)
		self.CMB_shot.setEnabled(False)
		self.CMB_shot.clear()

		self.populateSeqAndShot()

		self.LNE_file.setText('')
		self.BTN_import.setEnabled(False)

		super(ImportElementDialog, self).show()

class FindElementItem(QLabel):
	def __init__(self, el, col, parent):
		super(FindElementItem, self).__init__(parent)

		self.element = el
		self.col = col

		self.setText(str(self.data()))

	def data(self):
		if self.col == 0:
			return self.element.get('name')
		elif self.col == 1:
			return self.element.get('type')
		elif self.col == 2:
			container = self.element.getContainer()

			if isinstance(container, tuple):
				return '{} ({})'.format(str(container[1]), str(container[0]))
			else:
				return container

class FindDialog(QDialog):
	def __init__(self, parent):
		super(FindDialog, self).__init__(parent)

	def makeConnections(self):
		self.BTN_cancel.clicked.connect(self.reject)
		self.BTN_find.clicked.connect(self.handleFind)
		self.CMB_show.currentIndexChanged.connect(self.populateSeqAndShot)
		self.CMB_seq.currentIndexChanged.connect(self.populateShots)

	def storeOptions(self):
		self.string = str(self.LNE_string.text()).strip()
		self.strOption = 0 # default to contains

		if self.RDO_starts.isChecked():
			self.strOption = 1
		elif self.RDO_ends.isChecked():
			self.strOption = 2

		self.elType = None if self.CMB_type.currentText() == 'any' else str(self.CMB_type.currentText())
		self.show = str(self.CMB_show.currentText())
		self.seq = None if self.CMB_seq.currentText() == 'any' else str(self.CMB_seq.currentText())
		self.shot = None if self.CMB_shot.currentText() == 'any' else str(self.CMB_shot.currentText())

		cmds.pop(self.show)

	def filterElements(self, element):
		if self.string:
			if self.strOption == 0: # contains
				if self.string not in element.get('name'):
					return False
			elif self.strOption == 1: # starts with
				if not element.get('name').startswith(self.string):
					return False
			elif self.strOption == 2: # ends with
				if not element.get('name').endswith(self.string):
					return False

		if self.elType and self.elType != element.get('type'):
			return False

		elParent = element.get('parent')

		if not elParent and (self.seq or self.shot): # If parent is a show, but the user specified a seq or shot, we bail
			return False

		if not elParent and not self.seq and not self.shot:
			return True

		seq, shot = elParent.split('/')

		if seq and self.seq and seq != self.seq:
			return False

		if shot and self.shot and shot != self.shot:
			return False

		return True

	def populateShots(self):
		self.CMB_shot.clear()

		seq = str(self.CMB_seq.currentText())

		if not seq or seq == 'any':
			self.CMB_shot.addItems([])
			return

		seq = env.show.getSequence(seq)
		shots = [str(s.get('num')) for s in seq.getShots()]

		self.CMB_shot.addItems(['any'] + sorted(shots, key=lambda s: int(s)))

	def populateSeqAndShot(self):
		self.CMB_seq.clear()
		cmds.pop(str(self.CMB_show.currentText()))

		seqs = [str(s.get('num')) for s in env.show.getSequences()]

		self.CMB_seq.addItems(['any'] + sorted(seqs))
		self.populateShots()

	def show(self):
		elTypeItems = ['any']

		elTypeItems.extend(Element.ELEMENT_TYPES)

		self.CMB_type.clear()
		self.CMB_type.addItems(elTypeItems)
		self.CMB_type.setCurrentIndex(0)
		self.CMB_show.addItems([s.get('name') for s in self.parent().db.getShows()])

		self.populateSeqAndShot()

		super(FindDialog, self).show()

	def handleFind(self):
		self.storeOptions()

		show = self.parent().db.getShow(self.show)
		elements = show.getAllElements(self.filterElements)

		self.TBL_found.clearContents()
		self.TBL_found.setRowCount(0)

		row = 0

		for el in elements:
			self.TBL_found.insertRow(row)
			self.TBL_found.setCellWidget(row, 0, FindElementItem(el, 0, self.TBL_found))
			self.TBL_found.setCellWidget(row, 1, FindElementItem(el, 1, self.TBL_found))
			self.TBL_found.setCellWidget(row, 2, FindElementItem(el, 2, self.TBL_found))

			row += 1

class ManagerWindow(QMainWindow):
	def __init__(self, dbPath=None):
		super(ManagerWindow, self).__init__()
		uic.loadUi(os.path.join(helix.root, 'ui', 'visualizer.ui'), self)

		self.elTypeFilter = Element.ELEMENT_TYPES
		self.currentSelectionIndex = None
		self.editDialog = EditingDialog(self)
		self.showCreationDialog = NewShowDialog(self)
		self.seqCreationDialog = NewSequenceDialog(self)
		self.shotCreationDialog = NewShotDialog(self)
		self.elementCreationDialog = NewElementDialog(self)
		self.rollbackDialog = RollbackDialog(self)
		self.importElementDialog = ImportElementDialog(self)
		self.findDialog = FindDialog(self)

		uic.loadUi(os.path.join(helix.root, 'ui', 'editingDialog.ui'), self.editDialog)
		self.editDialog.makeConnections()

		uic.loadUi(os.path.join(helix.root, 'ui', 'showCreation.ui'), self.showCreationDialog)
		self.showCreationDialog.makeConnections()

		uic.loadUi(os.path.join(helix.root, 'ui', 'seqCreation.ui'), self.seqCreationDialog)
		self.seqCreationDialog.makeConnections()

		uic.loadUi(os.path.join(helix.root, 'ui', 'shotCreation.ui'), self.shotCreationDialog)
		self.shotCreationDialog.makeConnections()

		uic.loadUi(os.path.join(helix.root, 'ui', 'elementCreation.ui'), self.elementCreationDialog)
		self.elementCreationDialog.makeConnections()

		uic.loadUi(os.path.join(helix.root, 'ui', 'rollbackDialog.ui'), self.rollbackDialog)
		self.rollbackDialog.makeConnections()

		uic.loadUi(os.path.join(helix.root, 'ui', 'importElementDialog.ui'), self.importElementDialog)
		self.importElementDialog.makeConnections()

		uic.loadUi(os.path.join(helix.root, 'ui', 'find.ui'), self.findDialog)
		self.findDialog.makeConnections()

		self.checkSelection()
		self.makeConnections()
		self.setAcceptDrops(True)

		self.show()

		if dbPath:
			self.handleOpenDB(dbLoc=dbPath)

	def dragEnterEvent(self, event):
		if event.mimeData().hasUrls():
			urls = event.mimeData().urls()

			if urls and len(urls) == 1:
				event.acceptProposedAction()

		super(ManagerWindow, self).dragEnterEvent(event)

	def dropEvent(self, event):
		url = event.mimeData().urls()[0]

		if url.isLocalFile():
			path = str(url.toLocalFile())

			if not os.path.isdir(path):
				_, ext = os.path.splitext(path)

				if ext == '.json':
					self.handleOpenDB(dbLoc=path)
					event.acceptProposedAction()
				else: # Try import element (from single file)
					pass
			else: # Try import element (as directory)
				pass

		super(ManagerWindow, self).dropEvent(event)

	def makeConnections(self):
		self.ACT_openDB.triggered.connect(self.handleOpenDB)
		self.ACT_reload.triggered.connect(self.handleDBReload)
		self.ACT_newShow.triggered.connect(self.handleNewShow)
		self.ACT_newSeq.triggered.connect(self.handleNewSequence)
		self.ACT_newShot.triggered.connect(self.handleNewShot)
		self.ACT_newElement.triggered.connect(self.handleNewElement)
		self.ACT_editProperties.triggered.connect(self.handleElementEdit)
		self.ACT_explorer.triggered.connect(self.handleExplorer)
		self.ACT_importElement.triggered.connect(self.handleImportElement)
		self.TBL_elements.itemDoubleClicked.connect(self.handleElementEdit)
		self.VIEW_cols.doubleClicked.connect(self.handleDataEdit)
		self.ACT_find.triggered.connect(self.findDialog.show)
		self.ACT_prefGeneral.triggered.connect(lambda: self.handleConfigEditor(0))
		self.ACT_prefPerms.triggered.connect(lambda: self.handleConfigEditor(1))
		self.ACT_prefExe.triggered.connect(lambda: self.handleConfigEditor(2))

		self.ACT_slapComp.triggered.connect(self.handleSlapComp)
		self.ACT_slapComp.setEnabled(False)

		self.MENU_elementTypes.clear()
		self.MENU_elementTypes.setWindowTitle('Element Type Filter')

		for elType in Element.ELEMENT_TYPES:
			action = self.MENU_elementTypes.addAction(elType)

			action.setCheckable(True)
			action.setChecked(True)

			action.triggered.connect(self.handleElementFilterUpdate)

		self.MENU_elementTypes.addSeparator()
		self.MENU_elementTypes.addAction('View All').triggered.connect(lambda: self.handleElementTypeFilter(True))
		self.MENU_elementTypes.addAction('Hide All').triggered.connect(lambda: self.handleElementTypeFilter(False))

	def handleConfigEditor(self, tabIndex):
		dialog = ConfigEditorDialog(self)

		dialog.tabs.setCurrentIndex(tabIndex)
		dialog.show()

	def handleSlapComp(self):
		if not self.currentSelectionIndex:
			return

		item = self.currentSelectionIndex.internalPointer().data(0)

		if not isinstance(item, Shot):
			return

		SlapCompDialog(item, self).show()

	def handleImportElement(self):
		self.importElementDialog.show()

	def handleElementFilterUpdate(self):
		self.elTypeFilter = []

		for action in self.MENU_elementTypes.actions():
			if action.isChecked():
				self.elTypeFilter.append(action.text())

		self.handleDataSelection(self.currentSelectionIndex, None)

	def handleElementTypeFilter(self, view=True):
		if view:
			self.elTypeFilter = Element.ELEMENT_TYPES
		else:
			self.elTypeFilter = []

		for action in self.MENU_elementTypes.actions():
			action.setChecked(view)

		self.handleDataSelection(self.currentSelectionIndex, None)

	def handleExplorer(self):
		item = self.TBL_elements.cellWidget(self.TBL_elements.currentRow(), self.TBL_elements.currentColumn())

		# Fall back to selection in the column view and try to show the file location for that
		if not item:
			idx = self.VIEW_cols.selectionModel().currentIndex()

			if not idx.isValid():
				return

			fileutils.openPathInExplorer(idx.internalPointer().data(0).getDiskLocation())
		else:
			item.handleExplorer(True)

	def handleSaveConflict(self, e):
		resp = QMessageBox.warning(self, 'Merge Conflict', str(e) + '\nOverwrite on-disk values? Specifying "No" (or closing the dialog) will discard your local changes made this session.', buttons=QMessageBox.Yes|QMessageBox.No)
		diff = self.db._diffToResolve

		if diff:
			diff.resolve(discard=resp!=QMessageBox.Yes)

	def handleNewShow(self):
		self.showCreationDialog.show()

	def handleNewSequence(self):
		index = self.VIEW_cols.selectionModel().currentIndex()

		if not index.isValid():
			return

		node = index.internalPointer()
		parent = node.parent()
		data = node.data(0)

		while not isinstance(data, Show) and parent:
			data = parent.data(0)
			parent = parent.parent()

		# data is now the Show
		self.seqCreationDialog.show(data)

	def handleNewShot(self):
		index = self.VIEW_cols.selectionModel().currentIndex()

		if not index.isValid():
			return

		node = index.internalPointer()
		parent = node.parent()
		data = node.data(0)
		seq = None

		while not isinstance(data, Show) and parent:
			if isinstance(data, Sequence):
				seq = data

			data = parent.data(0)
			parent = parent.parent()

		# data is now the Show
		self.shotCreationDialog.show(data, seq)

	def handleNewElement(self):
		index = self.VIEW_cols.selectionModel().currentIndex()

		if not index.isValid():
			return

		node = index.internalPointer()
		parent = node.parent()
		data = node.data(0)
		seq = None
		shot = None

		while not isinstance(data, Show) and parent:
			if isinstance(data, Sequence):
				seq = data
			elif isinstance(data, Shot):
				shot = data

			data = parent.data(0)
			parent = parent.parent()

		# data is now the Show
		self.elementCreationDialog.show(data, seq, shot)

	def handleDataEdit(self, index):
		if not index.isValid():
			return

		item = index.internalPointer().data(0)

		self.editDialog.setItem(item)

	def handleElementEdit(self, item=None):
		if not item:
			item = self.TBL_elements.cellWidget(self.TBL_elements.currentRow(), self.TBL_elements.currentColumn())

			# Fall back to selection in the column view and try to show the edit dialog for that
			if not item:
				idx = self.VIEW_cols.selectionModel().currentIndex()

				self.handleDataEdit(idx)
		if not isinstance(item, ElementTableItem):
			return

		self.editDialog.setItem(item.element)

	def checkSelection(self):
		self.ACT_newSeq.setEnabled(False)
		self.ACT_newShot.setEnabled(False)
		self.ACT_newElement.setEnabled(False)
		self.ACT_editProperties.setEnabled(False)

		if not self.currentSelectionIndex:
			return

		self.ACT_editProperties.setEnabled(True)

		item = self.currentSelectionIndex.internalPointer().data(0)

		if isinstance(item, Show):
			self.ACT_newSeq.setEnabled(True)
			self.ACT_newShot.setEnabled(False)
			self.ACT_newElement.setEnabled(True)
			self.ACT_slapComp.setEnabled(False)
		elif isinstance(item, Sequence):
			self.ACT_newSeq.setEnabled(True)
			self.ACT_newShot.setEnabled(True)
			self.ACT_newElement.setEnabled(True)
			self.ACT_slapComp.setEnabled(False)
		elif isinstance(item, Shot):
			self.ACT_newSeq.setEnabled(False)
			self.ACT_newShot.setEnabled(True)
			self.ACT_newElement.setEnabled(True)
			self.ACT_slapComp.setEnabled(True)

	def handleDataSelection(self, currentIndex, oldIndex):
		if not currentIndex or not currentIndex.isValid():
			self.currentSelectionIndex = None
			self.TBL_elements.clearContents()
			self.TBL_elements.setRowCount(0)
			return

		self.currentSelectionIndex = currentIndex

		self.checkSelection()

		self.TBL_elements.clearContents()
		self.TBL_elements.setRowCount(0)

		container = currentIndex.internalPointer().data(0)

		if isinstance(container, Show) and container != env.show:
			cmds.pop(container.get('name'))

		for el in container.getElements():
			if el.get('type') not in self.elTypeFilter:
				continue

			row = self.TBL_elements.rowCount()

			self.TBL_elements.insertRow(row)

			typeItem = ElementTableItem(el, 0, self)
			nameItem = ElementTableItem(el, 1, self)

			self.TBL_elements.setCellWidget(row, 0, typeItem)
			self.TBL_elements.setCellWidget(row, 1, nameItem)

		self.TBL_elements.doubleClicked.connect(self.handleElTableDoubleClick)

	def handleElTableDoubleClick(self, index):
		if not index.isValid():
			return

		self.handleElementEdit()

	def handleOpenDB(self, dbLoc=None):
		self.dbLoc = dbLoc if dbLoc else QFileDialog.getOpenFileName(self, caption='Open Database File', filter='Database Files (*.json)')

		if os.path.exists(self.dbLoc):
			self.db = Database(str(self.dbLoc))
			self.model = ShowModel(self.db.getShows())

			self.VIEW_cols.setModel(self.model)
			self.VIEW_cols.setSelectionModel(QItemSelectionModel(self.model))
			self.VIEW_cols.selectionModel().currentChanged.connect(self.handleDataSelection)
			self.ACT_reload.setEnabled(True)

	def handleDBReload(self):
		del self.db

		self.db = Database(str(self.dbLoc))

		self.model.setShows(self.db.getShows())
		self.handleDataSelection(QModelIndex(), QModelIndex())

if __name__ == '__main__':
	app = QApplication(sys.argv)
	dbPath = None

	app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt())

	if len(sys.argv) >= 2:
		dbPath = sys.argv[1]

	window = ManagerWindow(dbPath=dbPath)

	sys.exit(app.exec_())
