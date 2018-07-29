import os, sys
from datetime import datetime

import helix
from helix.database.show import Show
from helix.database.sequence import Sequence
from helix.database.shot import Shot
from helix.database.element import Element
import helix.database.database as db
import helix.api.commands as hxcmds
import helix.environment.environment as env
import helix.environment.permissions as perms
import helix.utils.fileutils as fileutils
from helix.manager.dailies import SlapCompDialog
from helix.manager.config import ConfigEditorDialog
from helix.manager.console import Console
from helix.manager.element import ElementViewWidget, ElementPickerDialog, PickMode
from helix.utils.qtutils import Node, ExceptionDialog, FileChooserLayout, ElementListWidgetItem, Operation
import helix.utils.utils as utils

import qdarkstyle

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic

class ShowModel(QAbstractItemModel):
	def __init__(self, shows, parent=None):
		super(ShowModel, self).__init__(parent)

		self.setShows(shows)

	def getShowIndexes(self):
		indexes = []

		for i in range(self._root.childCount()):
			indexes.append(self.index(i, 0))

		return indexes

	def setShows(self, shows):
		self.beginResetModel()

		self._root = Node()

		shows.sort(key=lambda s: getattr(s, s.pk))

		for show in shows:
			env.setEnvironment('show', show.alias)
			showNode = self._root.addChild(Node(show))
			seqs = show.getSequences()

			seqs.sort(key=lambda s: s.num)

			for seq in seqs:
				seqNode = showNode.addChild(Node(seq))
				shots = seq.getShots()

				shots.sort(key=lambda s: s.num)

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
	def __init__(self, elementId, data, parent):
		super(ElementTableItem, self).__init__('')

		self.parent = parent
		self.elementId = elementId
		self.setText(str(data))

		self.explorerAction = QAction('Open work directory', self)
		self.exploreReleaseAction = QAction('Open release directory', self)
		self.publishAction = QAction('Publish...', self)
		self.rollbackAction = QAction('Rollback...', self)
		self.propertiesAction = QAction('Properties...', self)

		# No rollback option if we have no publishes for the element
		if not self.element.pubVersion:
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
		path = self.element.work_path

		if not work:
			path = self.element.release_path

		fileutils.openPathInExplorer(path)

	def handlePublish(self):
		env.setEnvironment('element', self.elementId)
		PublishDialog(self.parent, self.element).exec_()

	def handleRollback(self):
		env.setEnvironment('element', self.elementId)
		RollbackDialog(self.parent.parent, self.element).show()

	@property
	def element(self):
		return Element.fromPk(self.elementId)

class PublishDialog(QDialog):
	def __init__(self, parent, element):
		super(PublishDialog, self).__init__(parent)
		self.setWindowTitle('Publish {}'.format(str(element)))

		self.element = element

		self.layout = QVBoxLayout()

		self.layout.addWidget(QLabel('Select a file or folder to publish. For sequences, you can pick any 1 file from the sequence'))

		self.fileChooser = FileChooserLayout(self, defaultText=element.work_path, selectionMode=FileChooserLayout.ANY)
		self.layout.addLayout(self.fileChooser)

		self.publishLabel = QLabel('Publishing as: -')
		self.layout.addWidget(self.publishLabel)

		# Sequence options
		self.seqGroupBox = QGroupBox('Sequence Options')

		grpLayout = QVBoxLayout()
		self.ignoreChk = QCheckBox('Ignore missing frames')
		self.ignoreChk.setToolTip('When checked, you will not be warned about frames missing - the operation will just continue and the published output will also be missing these frames.')
		grpLayout.addWidget(self.ignoreChk)

		rangeLayout = QHBoxLayout()
		self.rangeChk = QCheckBox('Specific range')
		self.rangeChk.setToolTip('When checked, the numbers specified determine the subset of the found frame range that will be published. When unchecked, the whole sequence is published.')
		self.rangeChk.clicked.connect(self.handleRangeCheck)
		rangeLayout.addWidget(self.rangeChk)
		self.range1 = QSpinBox()
		self.range2 = QSpinBox()
		self.range1.setEnabled(False)
		self.range2.setEnabled(False)
		rangeLayout.addWidget(self.range1)
		rangeLayout.addWidget(self.range2)

		grpLayout.addLayout(rangeLayout)
		self.layout.addWidget(self.seqGroupBox)
		self.seqGroupBox.setLayout(grpLayout)
		self.seqGroupBox.setEnabled(False)

		# Dialog buttons
		buttonLayout = QHBoxLayout()
		self.pubButton = QPushButton('Publish')
		self.cancelButton = QPushButton('Cancel')
		buttonLayout.addWidget(self.cancelButton)
		buttonLayout.addWidget(self.pubButton)
		buttonLayout.insertStretch(0)
		self.layout.addLayout(buttonLayout)

		self.setLayout(self.layout)

		self.makeConnections()
		self.updatePublishLabel(self.fileChooser.getFile())

	def makeConnections(self):
		self.pubButton.clicked.connect(self.accept)
		self.cancelButton.clicked.connect(self.reject)
		self.fileChooser.fileChosen.connect(self.handleFileChosen)

	def handleRangeCheck(self):
		self.range1.setEnabled(self.rangeChk.isChecked())
		self.range2.setEnabled(self.rangeChk.isChecked())

	def handleFileChosen(self, file):
		self.updatePublishLabel(str(file))

	def updatePublishLabel(self, file):
		sequence = helix.utils.fileclassification.FrameSequence(file)
		publishAs = '-'

		self.seqGroupBox.setEnabled(False)

		if os.path.isdir(file):
			publishAs = 'Folder'
		elif os.path.isfile(file) and sequence.getRange() != ():
			publishAs = 'Sequence'
			self.seqGroupBox.setEnabled(True)
			range = sequence.getRange()
			self.range1.setValue(range[0])
			self.range1.setMinimum(range[0])
			self.range1.setMaximum(range[1])
			self.range2.setValue(range[1])
			self.range2.setMinimum(range[0])
			self.range2.setMaximum(range[1])
		elif os.path.isfile(file):
			publishAs = 'Single File'

		self.publishLabel.setText('Publishing as: {}'.format(publishAs))

	def accept(self):
		try:
			file = self.fileChooser.getFile()
			rng = () if not self.seqGroupBox.isEnabled() or not self.rangeChk.isChecked() else (int(self.range1.value()), int(self.range2.value()))
			force = False if not self.seqGroupBox.isEnabled() else self.ignoreChk.isChecked()
			cmd = ['pub', '"{}"'.format(file)]

			if rng != ():
				cmd.append('--range')
				cmd.append(str(rng[0]))
				cmd.append(str(rng[1]))

			if force:
				cmd.append('--force')

			self.parent().console.injectGetElement(self.element)
			self.parent().console.inject(cmd)
		except Exception as e:
			ExceptionDialog(e, parent=self).exec_()

		super(PublishDialog, self).accept()

class NewShowDialog(QDialog):
	def __init__(self, parent):
		super(NewShowDialog, self).__init__(parent)
		uic.loadUi(os.path.join(helix.root, 'ui', 'showCreation.ui'), self)

		self.makeConnections()
		self.checkCanCreate()

	def makeConnections(self):
		self.BTN_create.clicked.connect(self.accept)
		self.BTN_cancel.clicked.connect(self.reject)
		self.LNE_alias.textChanged.connect(self.checkCanCreate)

	def checkCanCreate(self):
		text = str(self.LNE_alias.text())
		self.LBL_issues.setText('')

		if not text:
			self.BTN_create.setEnabled(False)
			self.LBL_issues.setText('<font color="red">Alias is required</font>')
		else:
			sanitary, reasons = utils.isSanitary(text)

			self.BTN_create.setEnabled(sanitary)
			self.LBL_issues.setText(
				'<br>'.join(['<font color="red">{}</font>'.format(r) for r in reasons])
			)

	def accept(self):
		alias, name = self.getInputs()

		cmd = ['mkshow', alias]

		if name:
			cmd.extend(['--name', '"{}"'.format(name)])

		result = self.parent().console.inject(cmd)

		if result:
			self.parent().handleDBReload()
			super(NewShowDialog, self).accept()

	def getInputs(self):
		return (str(self.LNE_alias.text()).strip(), str(self.LNE_name.text()).strip())

class NewSequenceDialog(QDialog):
	def __init__(self, parent, show):
		super(NewSequenceDialog, self).__init__(parent)
		uic.loadUi(os.path.join(helix.root, 'ui', 'seqCreation.ui'), self)
		self.makeConnections()

		self._show = show

		from helix.database.sql import Manager
		with Manager(willCommit=False) as mgr:
			row = mgr.connection().execute(
				"SELECT MAX(num) FROM {} WHERE show='{}'".format(
					Sequence.TABLE,
					self._show
				)
			).fetchone()

		self.SPN_num.setValue(row[0] + 100 if row and row[0] is not None else 100)
		self.LBL_show.setText(str(self._show))

	def makeConnections(self):
		self.BTN_create.clicked.connect(self.accept)
		self.BTN_cancel.clicked.connect(self.reject)

	def accept(self):
		seqNum = int(self.SPN_num.value())

		self.parent().console.inject(['pop', self._show])

		result = self.parent().console.inject(['mkseq', str(seqNum)])

		if result:
			self.parent().handleDBReload()
			super(NewSequenceDialog, self).accept()

class NewShotDialog(QDialog):
	def __init__(self, parent, show, seq):
		super(NewShotDialog, self).__init__(parent)
		uic.loadUi(os.path.join(helix.root, 'ui', 'shotCreation.ui'), self)
		self.makeConnections()

		self._show = show
		self._seq = seq

		from helix.database.sql import Manager
		with Manager(willCommit=False) as mgr:
			row = mgr.connection().execute(
				"SELECT MAX(num) FROM {} WHERE show='{}' and sequence='{}'".format(
					Shot.TABLE,
					self._show,
					self._seq
				)
			).fetchone()

		self.SPN_num.setValue(row[0] + 100 if row and row[0] is not None else 100)
		self.LBL_show.setText(str(self._show))
		self.LBL_seq.setText(str(self._seq))

		self.checkCanCreate()

	def makeConnections(self):
		self.BTN_create.clicked.connect(self.accept)
		self.BTN_cancel.clicked.connect(self.reject)
		self.LNE_clip.textChanged.connect(self.checkCanCreate)

	def checkCanCreate(self):
		text = str(self.LNE_clip.text())
		self.LBL_issues.setText('')

		if not text:
			self.BTN_create.setEnabled(True)
		else:
			sanitary, reasons = utils.isSanitary(text, minChars=0)

			self.BTN_create.setEnabled(sanitary)
			self.LBL_issues.setText(
				'<br>'.join(['<font color="red">{}</font>'.format(r) for r in reasons])
			)

	def accept(self):
		shotNum, start, end, clipName = self.getInputs()
		cmd = [
			'mkshot',
			str(self._seq),
			str(shotNum),
			'--start', str(start),
			'--end', str(end),
		]

		if clipName:
			cmd.extend(['-c', clipName])

		self.parent().console.inject(['pop', self._show])

		result = self.parent().console.inject(cmd)

		if result:
			self.parent().handleDBReload()
			super(NewShotDialog, self).accept()

	def getInputs(self):
		shotNum = self.SPN_num.value()
		start = self.SPN_start.value()
		end = self.SPN_end.value()
		clipName = str(self.LNE_clip.text()).strip()

		return (shotNum, start, end, clipName)

class NewElementDialog(QDialog):
	def __init__(self, parent, show, seq, shot):
		super(NewElementDialog, self).__init__(parent)
		uic.loadUi(os.path.join(helix.root, 'ui', 'elementCreation.ui'), self)
		self.makeConnections()

		self._show = show
		self._seq = seq
		self._shot = shot
		container = self._shot if self._shot else self._seq
		container = container if container else self._show

		self.CMB_type.addItems(Element.ELEMENT_TYPES)
		self.CHK_nameless.setVisible(self._seq is not None and self._shot is not None)
		self.LBL_container.setText(str(container))

		self.checkCanCreate()

	def makeConnections(self):
		self.BTN_create.clicked.connect(self.accept)
		self.BTN_cancel.clicked.connect(self.reject)
		self.LNE_name.textChanged.connect(self.checkCanCreate)
		self.CHK_nameless.stateChanged.connect(self.handleNamelessStateChange)

	def handleNamelessStateChange(self, state):
		self.LNE_name.setEnabled(state == Qt.Unchecked)
		self.checkCanCreate()

	def checkCanCreate(self):
		text = str(self.LNE_name.text())
		self.LBL_issues.setText('')

		if self.CHK_nameless.isChecked():
			self.BTN_create.setEnabled(True)
		else:
			sanitary, reasons = utils.isSanitary(text, minChars=1, maxChars=40)

			if len(text) > 40:
				reasons.append('More than 40 characters? Really?')

			self.BTN_create.setEnabled(sanitary)
			self.LBL_issues.setText(
				'<br>'.join(['<font color="red">{}</font>'.format(r) for r in reasons])
			)

	def accept(self):
		name, elType = self.getInputs()

		seq = self._seq.num if self._seq else None
		shot = self._shot.num if self._shot else None
		clip = self._shot.clipName if self._shot else None

		cmd = [
			'mke',
			elType,
			name,
		]

		if seq:
			cmd.extend(['-sq', str(seq)])

		if shot:
			cmd.extend(['-s', str(shot)])

		if clip:
			cmd.extend(['-c', clip])

		self.parent().console.inject(['pop', self._show.alias])

		result = self.parent().console.inject(cmd)

		if result:
			self.parent().handleDBReload()
			super(NewElementDialog, self).accept()

	def getInputs(self):
		name = str(self.LNE_name.text()).strip() if self.CHK_nameless.checkState() == Qt.Unchecked else '-'
		elType = str(self.CMB_type.currentText())

		return (name, elType)

class RollbackDialog(QDialog):
	def __init__(self, parent, element):
		super(RollbackDialog, self).__init__(parent)
		uic.loadUi(os.path.join(helix.root, 'ui', 'rollbackDialog.ui'), self)

		self._element = element

		self.LBL_pubVersion.setText(str(element.pubVersion if element.pubVersion else '--'))

		versions = element.getPublishedVersions()

		# Add all but the current published version, we don't allow for them to rollback
		# to the current version anyway
		self.CMB_rollback.addItems([str(ver) for ver in versions if ver != element.pubVersion])

		self.makeConnections()

	def makeConnections(self):
		self.BTN_rollback.clicked.connect(self.accept)
		self.BTN_cancel.clicked.connect(self.reject)

	def accept(self):
		rollbackVer = self.CMB_rollback.currentText()

		try:
			cmd = ['roll', '-v', str(rollbackVer)]

			self.parent().console.injectGetElement(self._element)
			self.parent().console.inject(cmd)

			super(RollbackDialog, self).accept()
		except Exception, e:
			QMessageBox.warning(self, 'Rollback error', str(e))
			return

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
		return 0

	def data(self, index, role):
		if not index.isValid():
			return QVariant()

		item = index.internalPointer()

		if node and role == Qt.DisplayRole:
			return str(item)

		return QVariant()

class EditingDialog(QDialog):
	def __init__(self, parent, item):
		super(EditingDialog, self).__init__(parent)
		uic.loadUi(os.path.join(helix.root, 'ui', 'editingDialog.ui'), self)

		self.BTN_refresh.setIcon(QApplication.instance().style().standardIcon(QStyle.SP_BrowserReload))
		self.TBL_properties.clearContents()
		self.TBL_properties.setRowCount(0)

		self.makeConnections()
		self.setItem(item)

	def setItem(self, item):
		QCoreApplication.instance().setOverrideCursor(QCursor(Qt.WaitCursor))
		self.item = item

		self.setWindowTitle('{} properties'.format(str(self.item)))

		row = 0

		from helix.database.sql import Manager
		with Manager(willCommit=False) as mgr:
			for c, _ in mgr.getColumnNames(item.table):
				self.TBL_properties.insertRow(row)

				# TODO add refresh to this dialog
				propItem = QTableWidgetItem(c)
				valItem = QTableWidgetItem(str(item.get(c))) # Actually pull off disk

				propItem.setFlags(propItem.flags() & ~Qt.ItemIsEditable)
				valItem.setFlags(valItem.flags() & ~Qt.ItemIsEditable)

				self.TBL_properties.setItem(row, 1, valItem)
				self.TBL_properties.setItem(row, 0, propItem)

				row += 1

		self.TBL_properties.verticalHeader().setResizeMode(QHeaderView.ResizeToContents)
		QCoreApplication.instance().restoreOverrideCursor()

	def makeConnections(self):
		self.BTN_refresh.clicked.connect(lambda: self.setItem(self.item))

	def accept(self):
		super(EditingDialog, self).accept()

class ImportElementDialog(QDialog):
	def __init__(self, parent):
		super(ImportElementDialog, self).__init__(parent)

		uic.loadUi(os.path.join(helix.root, 'ui', 'importElementDialog.ui'), self)

		self.CMB_type.addItems(Element.ELEMENT_TYPES)
		self.CMB_show.addItems([s.alias for s in db.getShows()])
		self.folderLayout = FileChooserLayout(self, browseCaption='Select folder with asset contents', selectionMode=FileChooserLayout.FOLDER)
		self.LAY_folderSelect.addLayout(self.folderLayout)

		self.makeConnections()

	def makeConnections(self):
		self.BTN_cancel.clicked.connect(self.reject)
		self.BTN_import.clicked.connect(self.accept)
		self.BTN_assetBrowse.clicked.connect(self.handleElementBrowse)
		self.CHK_nameless.clicked.connect(self.handleNamelessToggle)
		self.CMB_show.currentIndexChanged.connect(self.populateSeqAndShot)
		self.CMB_seq.currentIndexChanged.connect(self.populateShots)
		self.folderLayout.fileChosen.connect(self.handleFileChosen)

	def handleElementBrowse(self):
		dialog = ElementPickerDialog(db.getElements(), parent=self)

		dialog.exec_()

		selected = dialog.getSelectedElements()

		if not selected:
			return

		if not selected[0].name.startswith('_'):
			self.LNE_name.setText(selected[0].name)
			self.LNE_name.setEnabled(True)
			self.CHK_nameless.setChecked(False)
		else:
			self.LNE_name.setText('')
			self.LNE_name.setEnabled(False)
			self.CHK_nameless.setChecked(True)

		typeIndex = self.CMB_type.findText(selected[0].type)

		if typeIndex != -1:
			self.CMB_type.setCurrentIndex(typeIndex)

		showIndex = self.CMB_show.findText(selected[0].show)

		if showIndex != -1:
			self.CMB_show.setCurrentIndex(showIndex)

		if selected[0].sequence is not None:
			seqIndex = self.CMB_seq.findText(str(selected[0].sequence))

			if seqIndex != -1:
				self.CMB_seq.setCurrentIndex(seqIndex)

		if selected[0].shot is not None:
			clipName = selected[0].shot_clipName if selected[0].shot_clipName is not None else ''
			shotIndex = self.CMB_shot.findText(str(selected[0].shot) + clipName)

			if shotIndex != -1:
				self.CMB_shot.setCurrentIndex(shotIndex)

	def handleFileChosen(self):
		self.BTN_import.setEnabled(os.path.exists(self.folderLayout.getFile()))

	def handleNamelessToggle(self):
		self.LBL_name.setEnabled(not self.CHK_nameless.isChecked())
		self.LNE_name.setEnabled(not self.CHK_nameless.isChecked())

	def populateShots(self):
		self.CMB_shot.clear()

		seq = str(self.CMB_seq.currentText())

		if not seq or seq == '--':
			self.CMB_shot.addItems(['--'])
			return

		# Have to keep shots this way since we need to track the clipname as well
		self.shots = sorted([s for s in self._show.getShots(seqs=[int(seq)])], key=lambda s: int(s.num))

		self.CMB_shot.addItems(['--'] + [str(s.num) + (s.clipName if s.clipName else '') for s in self.shots])
		self.shots = ['--'] + self.shots

	def populateSeqAndShot(self):
		self.CMB_seq.clear()
		self._show = Show(str(self.CMB_show.currentText()))
		seqs = [str(s.num) for s in self._show.getSequences()]

		self.CMB_seq.addItems(['--'] + sorted(seqs, key=lambda s: int(s)))
		self.populateShots()

	def accept(self):
		show = str(self.CMB_show.currentText())
		seq = int(self.CMB_seq.currentText()) if self.CMB_seq.count() > 0 and self.CMB_seq.currentText() != '--' else None
		shot = self.shots[self.CMB_shot.currentIndex()] if self.CMB_shot.count() > 0 and self.CMB_shot.currentText() != '--' else None
		shotNum = shot.num if shot else None
		clipName = shot.clipName if shot else None
		assetDir = self.folderLayout.getFile()
		assetName = str(self.LNE_name.text()) if not self.CHK_nameless.isChecked() else None
		assetType = str(self.CMB_type.currentText())
		overwriteOption = 0

		if self.RDO_versionUp.isChecked():
			overwriteOption = 1
		elif self.RDO_skip.isChecked():
			overwriteOption = 2

		self.parent().console.inject(['pop', show])

		cmd = [
			'import',
			'-o', str(overwriteOption)
		]

		if assetName is not None:
			cmd.extend(['-n', assetName])

		if seq is not None:
			cmd.extend(['-sq', str(seq)])

		if shot is not None:
			cmd.extend(['-s', str(shotNum)])

		if clipName is not None:
			cmd.extend(['-c', str(clipName)])

		cmd.extend([assetDir, assetType])

		self.parent().console.inject(cmd)

		super(ImportElementDialog, self).accept()

	def show(self):
		self.populateSeqAndShot()

		super(ImportElementDialog, self).show()

class ExportDialog(QDialog):
	def __init__(self, parent):
		super(ExportDialog, self).__init__(parent)

		uic.loadUi(os.path.join(helix.root, 'ui', 'exportDialog.ui'), self)

		self.folderLayout = FileChooserLayout(self, browseCaption='Select folder to export to', label='Export destination', selectionMode=FileChooserLayout.FOLDER)
		self.LAY_folderSelect.addLayout(self.folderLayout)

		self.makeConnections()

	def makeConnections(self):
		self.BTN_elementBrowse.clicked.connect(self.handleElementBrowse)
		self.BTN_remove.clicked.connect(self.removeSelected)
		self.BTN_cancel.clicked.connect(self.reject)
		self.BTN_export.clicked.connect(self.accept)
		self.CHK_work.clicked.connect(self.determineExportButtonStatus)
		self.CHK_release.clicked.connect(self.determineExportButtonStatus)
		self.folderLayout.fileChosen.connect(self.handleFileChosen)

	def determineExportButtonStatus(self):
		if self.CHK_work.isChecked() or self.CHK_release.isChecked():
			self.handleFileChosen()
		else:
			self.BTN_export.setEnabled(False)

	def removeSelected(self):
		for item in self.LST_elements.selectedItems():
			self.LST_elements.takeItem(self.LST_elements.row(item))

	def handleFileChosen(self):
		self.BTN_export.setEnabled(os.path.exists(self.folderLayout.getFile()))

	def handleElementBrowse(self):
		dialog = ElementPickerDialog(db.getElements(), parent=self, mode=PickMode.MULTI)

		dialog.exec_()

		selected = dialog.getSelectedElements()

		if not selected:
			return

		self.LST_elements.clear()

		for row, el in enumerate(selected):
			self.LST_elements.insertItem(row, ElementListWidgetItem(el, parent=self.LST_elements))

	def accept(self):
		with Operation(numOps=self.LST_elements.count(), parent=self) as op:
			for row in range(self.LST_elements.count()):
				el = self.LST_elements.item(row).element
				cmd = ['export']

				op.updateLabel('Exporting {}...'.format(str(el)))

				if el.name is not None and not el.name.startswith('_'):
					cmd.extend(['-n', el.name])

				if el.sequence is not None:
					cmd.extend(['-sq', str(el.sequence)])

				if el.shot is not None:
					cmd.extend(['-s', str(el.shot)])

				if el.shot_clipName is not None:
					cmd.extend(['-c', str(el.shot_clipName)])

				if self.CHK_work.isChecked:
					cmd.append('--work')

				if self.CHK_release.isChecked:
					cmd.append('--release')

				cmd.extend([self.folderLayout.getFile(), el.show, el.type])

				self.parent().console.inject(cmd)
				op.tick()

		super(ExportDialog, self).accept()

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
		self._show = Show(str(self.CMB_show.currentText()))
		self.seq = None if self.CMB_seq.currentText() == 'any' else str(self.CMB_seq.currentText())
		self.shot = None if self.CMB_shot.currentText() == 'any' else str(self.CMB_shot.currentText())

	def filterElements(self, element):
		if self.string:
			if self.strOption == 0: # contains
				if self.string not in element.name:
					return False
			elif self.strOption == 1: # starts with
				if not element.name.startswith(self.string):
					return False
			elif self.strOption == 2: # ends with
				if not element.name.endswith(self.string):
					return False

		if self.elType and self.elType != element.type:
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
			return

		shots = [str(s.num) for s in self._show.getShots(seqs=[int(seq)])]

		self.CMB_shot.addItems(['any'] + sorted(shots, key=lambda s: int(s)))

	def populateSeqAndShot(self):
		self.CMB_seq.clear()
		self._show = Show(str(self.CMB_show.currentText()))

		seqs = [str(s.num) for s in self._show.getSequences()]

		self.CMB_seq.addItems(['any'] + sorted(seqs, key=lambda s: int(s)))
		self.populateShots()

	def show(self):
		elTypeItems = ['any']

		elTypeItems.extend(Element.ELEMENT_TYPES)

		self.CMB_type.clear()
		self.CMB_type.addItems(elTypeItems)
		self.CMB_type.setCurrentIndex(0)
		self.CMB_show.addItems([s.alias for s in db.getShows()])

		self.populateSeqAndShot()

		super(FindDialog, self).show()

	def handleFind(self):
		start = datetime.now()
		QCoreApplication.instance().setOverrideCursor(QCursor(Qt.WaitCursor))
		self.storeOptions()

		likeNamePattern = self.string

		if self.strOption == 0:
			likeNamePattern = '%' + likeNamePattern + '%'
		elif self.strOption == 1:
			likeNamePattern = likeNamePattern + '%'
		elif self.strOption == 2:
			likeNamePattern = '%' + likeNamePattern

		query = """SELECT * FROM {} WHERE show='{}' AND name LIKE '{}'""".format(Element.TABLE, self._show.alias, likeNamePattern)

		if self.elType:
			query += "AND type='{}'".format(self.elType)

		if self.seq:
			query += "AND sequence='{}'".format(self.seq)

		if self.shot:
			query += "AND shot='{}'".format(self.shot)

		elements = []

		from helix.database.sql import Manager
		with Manager(willCommit=False) as mgr:
			for row in mgr.connection().execute(query).fetchall():
					elements.append(Element.dummy().unmap(row))

		self.TBL_found.clearContents()
		self.TBL_found.setRowCount(0)

		row = 0

		for el in elements:
			self.TBL_found.insertRow(row)
			self.TBL_found.setItem(row, 0, QTableWidgetItem(el.name))
			self.TBL_found.setItem(row, 1, QTableWidgetItem(el.type))
			self.TBL_found.setItem(row, 2, QTableWidgetItem(str(el.parent)))

			row += 1

		time = datetime.now() - start
		matchText = ' match in ' if len(elements) == 1 else ' matches in '
		matchText = str(len(elements)) + matchText
		matchText += '{0:.3f} seconds'.format(time.total_seconds())

		self.LBL_status.setText(matchText)
		QApplication.instance().restoreOverrideCursor()

class ManagerWindow(QMainWindow):
	def __init__(self, dbPath=None):
		super(ManagerWindow, self).__init__()
		uic.loadUi(os.path.join(helix.root, 'ui', 'visualizer.ui'), self)

		self.permHandler = perms.PermissionHandler()
		self.elTypeFilter = Element.ELEMENT_TYPES
		self.currentSelectionIndex = None

		# == START dock widgets ==
		self.console = Console(self)
		self.console.setObjectName('Console')
		self.addDockWidget(Qt.RightDockWidgetArea, self.console)

		self.globalElViewer = ElementViewWidget(parent=self).asDockable()
		self.globalElViewer.setObjectName('GlobalElements')

		self.elementList = BasicElementView(parent=self)
		self.elListDock = self.elementList.asDockable()
		self.elListDock.setObjectName('ElementList')
		self.addDockWidget(Qt.BottomDockWidgetArea, self.elListDock)

		self.mainDock = QDockWidget('Hierarchy', self)
		self.mainDock.setWidget(self.WIDG_main)
		self.mainDock.setObjectName('Hierarchy')
		self.addDockWidget(Qt.TopDockWidgetArea, self.mainDock)
		# == END dock widgets ==

		# Find dialog is created like this as an easy way to preserve user's session settings for the search fields
		self.findDialog = FindDialog(self)
		uic.loadUi(os.path.join(helix.root, 'ui', 'find.ui'), self.findDialog)
		self.findDialog.makeConnections()

		self.checkSelection()
		self.makeConnections()
		self.setAcceptDrops(True)

		if dbPath:
			self.handleOpenDB(dbLoc=dbPath)

		self.configureUiForPerms()

	def restoreSettings(self, version=0):
		settings = QSettings()

		self.restoreGeometry(settings.value('geometry/{}'.format(version)).toByteArray())
		self.restoreState(settings.value('windowState/{}'.format(version)).toByteArray())

		hierarchy = settings.value('hierarchy/toggled/{}'.format(version), True).toBool()
		elementList = settings.value('elementList/toggled/{}'.format(version), True).toBool()
		globalElViewer = settings.value('globalElViewer/toggled/{}'.format(version), True).toBool()
		console = settings.value('console/toggled/{}'.format(version), True).toBool()

		self.ACT_hierarchy.setChecked(hierarchy)
		self.ACT_elList.setChecked(elementList)
		self.ACT_globalElView.setChecked(globalElViewer)
		self.ACT_console.setChecked(console)

		self.toggleElList()
		self.toggleElementViewer()
		self.toggleConsole()
		self.toggleHierarchy()

		# TODO: Save/Restore current data selection
		# TODO: Update Window > menu option when dock is closed

	def restoreFactorySettings(self):
		self.mainDock.show()
		self.elListDock.show()
		self.console.hide()
		self.globalElViewer.hide()

		self.addDockWidget(Qt.TopDockWidgetArea, self.mainDock)
		self.addDockWidget(Qt.BottomDockWidgetArea, self.elListDock)

		self.setGeometry(0, 0, 1050, 720)


	def saveSettings(self, version=0):
		settings = QSettings()

		settings.setValue('geometry/{}'.format(version), self.saveGeometry())
		settings.setValue('windowState/{}'.format(version), self.saveState())
		settings.setValue('hierarchy/toggled/{}'.format(version), self.ACT_hierarchy.isChecked())
		settings.setValue('elementList/toggled/{}'.format(version), self.ACT_elList.isChecked())
		settings.setValue('globalElViewer/toggled/{}'.format(version), self.ACT_globalElView.isChecked())
		settings.setValue('console/toggled/{}'.format(version), self.ACT_console.isChecked())

	def closeEvent(self, event):
		self.saveSettings()

		super(ManagerWindow, self).closeEvent(event)

	def configureUiForPerms(self):
		self.checkAction('helix.create.show', self.ACT_newShow)
		self.checkAction('helix.create.sequence', self.ACT_newSeq)
		self.checkAction('helix.create.shot', self.ACT_newShot)
		self.checkAction('helix.create.element', self.ACT_newElement)
		self.checkAction('helix.config.view', self.ACT_prefGeneral)
		self.checkAction('helix.config.view', self.ACT_prefPerms)
		self.checkAction('helix.config.view', self.ACT_prefExe)

	def checkAction(self, permNode, action):
		if not self.permHandler.check(permNode, silent=True):
			action.setDisabled(True)

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
		self.ACT_editProperties.triggered.connect(self.handleGetProperties)
		self.ACT_explorer.triggered.connect(self.handleExplorer)
		self.ACT_importElement.triggered.connect(self.handleImportElement)
		self.ACT_export.triggered.connect(self.handleExport)
		self.VIEW_cols.doubleClicked.connect(self.handleDataEdit)
		self.ACT_find.triggered.connect(self.findDialog.show)
		self.ACT_prefGeneral.triggered.connect(lambda: self.handleConfigEditor(0))
		self.ACT_prefPerms.triggered.connect(lambda: self.handleConfigEditor(1))
		self.ACT_prefExe.triggered.connect(lambda: self.handleConfigEditor(2))

		self.ACT_hierarchy.triggered.connect(self.toggleHierarchy)
		self.ACT_elList.triggered.connect(self.toggleElList)
		self.ACT_globalElView.triggered.connect(self.toggleElementViewer)
		self.ACT_console.triggered.connect(self.toggleConsole)
		self.ACT_wsReset.triggered.connect(lambda: self.restoreSettings(0))
		self.ACT_wsFullReset.triggered.connect(self.restoreFactorySettings)
		self.ACT_load1.triggered.connect(lambda: self.restoreSettings(1))
		self.ACT_load2.triggered.connect(lambda: self.restoreSettings(2))
		self.ACT_load3.triggered.connect(lambda: self.restoreSettings(3))
		self.ACT_save1.triggered.connect(lambda: self.saveSettings(1))
		self.ACT_save2.triggered.connect(lambda: self.saveSettings(2))
		self.ACT_save3.triggered.connect(lambda: self.saveSettings(3))
		self.ACT_loadOldSchool.triggered.connect(self.loadOldSchool)

		self.ACT_about.triggered.connect(self.handleAbout)
		self.ACT_manual.triggered.connect(lambda: QDesktopServices.openUrl(QUrl('http://helix.readthedocs.io/en/dev')))

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

	def loadOldSchool(self):
		self.mainDock.hide()
		self.elListDock.hide()
		self.globalElViewer.hide()
		self.console.setWindowState(Qt.WindowMaximized)
		self.console.show()

	def toggleHierarchy(self):
		if self.ACT_hierarchy.isChecked():
			self.mainDock.show()
		else:
			self.mainDock.hide()

	def toggleElList(self):
		if self.ACT_elList.isChecked():
			self.elListDock.show()
		else:
			self.elListDock.hide()

	def toggleElementViewer(self):
		if self.ACT_globalElView.isChecked():
			self.globalElViewer.show()
		else:
			self.globalElViewer.hide()

	def toggleConsole(self):
		if self.ACT_console.isChecked():
			self.console.show()
		else:
			self.console.hide()

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
		ImportElementDialog(self).show()

	def handleExport(self):
		ExportDialog(self).show()

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
		item = self.elementList.cellWidget(self.elementList.currentRow(), self.elementList.currentColumn())

		# Fall back to selection in the column view and try to show the file location for that
		if not item:
			idx = self.VIEW_cols.selectionModel().currentIndex()

			if not idx.isValid():
				return

			fileutils.openPathInExplorer(idx.internalPointer().data(0).work_path)
		else:
			item.handleExplorer(True)

	def handleSaveConflict(self, e):
		resp = QMessageBox.warning(self, 'Merge Conflict', str(e) + '\nOverwrite on-disk values? Specifying "No" (or closing the dialog) will discard your local changes made this session.', buttons=QMessageBox.Yes|QMessageBox.No)
		diff = self.db._diffToResolve

		if diff:
			diff.resolve(discard=resp!=QMessageBox.Yes)

	def handleNewShow(self):
		NewShowDialog(self).show()

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
		NewSequenceDialog(self, data.alias).show()

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
		NewShotDialog(self, data.alias, seq.num).show()

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
		NewElementDialog(self, data, seq, shot).show()

	def handleDataEdit(self, index):
		if not index.isValid():
			return

		item = index.internalPointer().data(0)

		EditingDialog(self, item).show()

	def handleGetProperties(self):
		item = self.elementList.currentItem()

		if item:
			self.elementList.handleElementEdit()
		else:
			# Fallback to show/seq/shot
			self.handleDataEdit(self.VIEW_cols.currentIndex())

	def buildContextMenu(self, obj):
		self.MENU_contextMenu.clear()

		if obj == Show:
			self.MENU_contextMenu.setTitle('Show')
		elif obj == Sequence:
			self.MENU_contextMenu.setTitle('Sequence')
		elif obj == Shot:
			self.MENU_contextMenu.setTitle('Shot')

			# Top level actions
			self.ACT_slapComp = QAction('Auto Slap Comp...', self.MENU_contextMenu)
			self.ACT_slapComp.triggered.connect(self.handleSlapComp)

			# Sub menus
			self.MENU_takes = QMenu('Takes', parent=self.MENU_contextMenu)
			self.ACT_newTake = QAction('New take...', self.MENU_takes)

			self.MENU_takes.addAction(self.ACT_newTake)

			self.MENU_contextMenu.addAction(self.ACT_slapComp)
			self.MENU_contextMenu.addSeparator()
			self.MENU_contextMenu.addMenu(self.MENU_takes)

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
			self.buildContextMenu(Show)
			self.ACT_newSeq.setEnabled(True)
			self.ACT_newShot.setEnabled(False)
			self.ACT_newElement.setEnabled(True)
		elif isinstance(item, Sequence):
			self.buildContextMenu(Sequence)
			self.ACT_newSeq.setEnabled(True)
			self.ACT_newShot.setEnabled(True)
			self.ACT_newElement.setEnabled(True)
		elif isinstance(item, Shot):
			self.buildContextMenu(Shot)
			self.ACT_newSeq.setEnabled(False)
			self.ACT_newShot.setEnabled(True)
			self.ACT_newElement.setEnabled(True)

		self.configureUiForPerms()

	def handleDataSelection(self, currentIndex, oldIndex):
		if not currentIndex or not currentIndex.isValid():
			self.currentSelectionIndex = None
			self.elementList.clearContents()
			self.elementList.setRowCount(0)
			return

		self.currentSelectionIndex = currentIndex

		QApplication.instance().setOverrideCursor(QCursor(Qt.WaitCursor))
		self.checkSelection()

		self.elementList.clearContents()
		self.elementList.setRowCount(0)

		container = currentIndex.internalPointer().data(0)
		els = []

		if isinstance(container, Show) and container.alias != env.getEnvironment('show'):
			self.console.inject(['pop', '"{}"'.format(container.alias)])
			els = container.getElements(
				types=self.elTypeFilter if self.elTypeFilter else [''],
				exclusive=True,
				debug=True
			)
			if self.globalElViewer:
				self.globalElViewer.widget().setElements(container.getElements())
		else:
			els = container.getElements(
				types=self.elTypeFilter if self.elTypeFilter else [''],
				exclusive=True,
				debug=True
			)

		self.elementList.setContainer(container)
		QApplication.instance().restoreOverrideCursor()

	def handleOpenDB(self, dbLoc=None):
		self.dbLoc = dbLoc if dbLoc else QFileDialog.getOpenFileName(self, caption='Open Database File', filter='Database Files (*.json)')

		if os.path.exists(self.dbLoc):
			env.setEnvironment('DB', self.dbLoc)

			from helix.database.sql import Manager
			with Manager() as mgr:
				mgr.initTables()

			self.model = ShowModel(db.getShows())

			self.VIEW_cols.setModel(self.model)
			self.VIEW_cols.setSelectionModel(QItemSelectionModel(self.model))
			self.VIEW_cols.selectionModel().currentChanged.connect(self.handleDataSelection)
			self.ACT_reload.setEnabled(True)

			indexes = self.model.getShowIndexes()

			if indexes:
				self.VIEW_cols.setCurrentIndex(indexes[0])
				self.handleDataSelection(indexes[0], None)

	def handleDBReload(self):
		QCoreApplication.instance().setOverrideCursor(QCursor(Qt.WaitCursor))
		self.model.setShows(db.getShows())
		self.handleDataSelection(QModelIndex(), QModelIndex())
		self.permHandler = perms.PermissionHandler()
		QCoreApplication.instance().restoreOverrideCursor()

	def handleAbout(self):
		dialog = QDialog(self)

		dialog.setWindowTitle('About Helix')
		dialog.resize(340, 120)

		layout = QVBoxLayout()
		label1 = QLabel('<p style="line-height:125">Helix is a project and asset management system developed and maintained by <a href="http://www.sashaouellet.com">Sasha Ouellet</a></p>')
		label1.setWordWrap(True)
		label1.setOpenExternalLinks(True)
		label1.setTextFormat(Qt.RichText);
		label1.setTextInteractionFlags(Qt.TextBrowserInteraction)
		layout.addWidget(label1)

		label2 = QLabel('<p style="line-height:125">Find this project on <a href="http://www.github.com/sashaouellet/Helix">Github</a></p>')
		label2.setWordWrap(True)
		label2.setOpenExternalLinks(True)
		label2.setTextFormat(Qt.RichText);
		label2.setTextInteractionFlags(Qt.TextBrowserInteraction)
		layout.addWidget(label2)

		dialog.setLayout(layout)

		dialog.exec_()

class BasicElementView(QTableWidget):
	COLUMNS = ['Name', 'Type', 'Author', 'Creation', 'Version']

	def __init__(self, container=None, parent=None):
		super(BasicElementView, self).__init__(parent=parent)
		self.parent = parent
		self.container = container

		self.makeConnections()

		self.setColumnCount(len(BasicElementView.COLUMNS))
		self.setHorizontalHeaderLabels(BasicElementView.COLUMNS)
		self.setMinimumSize(300, 100)
		self.verticalHeader().setVisible(False)

		self.setContainer(self.container)

	def makeConnections(self):
		self.cellDoubleClicked.connect(self.handleElementEdit)

	def setContainer(self, container):
		self.clearContents()
		self.setRowCount(0)

		els = []

		if container:
			els = container.getElements(exclusive=True)

		self.setRowCount(len(els))

		for row, el in enumerate(els):
			for col, attr in enumerate(BasicElementView.COLUMNS):
				self.setCellWidget(row, col, ElementTableItem(el.id, str(getattr(el, attr.lower())), self))

		self.resizeHeader()

	def resizeEvent(self, event):
		self.resizeHeader()
		super(BasicElementView, self).resizeEvent(event)

	def resizeHeader(self):
		header = self.horizontalHeader()

		for i in range(len(BasicElementView.COLUMNS)):
			header.setResizeMode(QHeaderView.ResizeToContents)

		header.setResizeMode(QHeaderView.Fixed)

		if header.size().width() <= self.size().width():
			for i in range(len(BasicElementView.COLUMNS)):
				self.setColumnWidth(
					i,
					self.size().width() / (1.0 * len(BasicElementView.COLUMNS))
				)

	def asDockable(self):
		qdock = QDockWidget('Asset List', self.parent)
		qdock.setWidget(self)

		return qdock

	def handleElementEdit(self, row=None, col=None):
		if row is None:
			row = self.currentRow()
		if col is None:
			col = self.currentColumn()

		item = self.cellWidget(row, col)

		if not isinstance(item, ElementTableItem):
			return

		EditingDialog(self.parent, item.element).show()

if __name__ == '__main__':
	app = QApplication(sys.argv)
	dbPath = None
	env.HAS_UI = True

	app.setOrganizationName('Helix')
	app.setApplicationName('Manager')
	app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt())
	app.setOverrideCursor(QCursor(Qt.WaitCursor))

	settings = QSettings()
	showSplash = settings.value('ui/showSplash', False).toBool()

	if len(sys.argv) >= 2:
		dbPath = sys.argv[1]

	if showSplash:
		pixmap = QPixmap(os.path.join(helix.root, 'ui', 'splash.jpg'))
		splash = QSplashScreen(pixmap,  Qt.WindowStaysOnTopHint)
		possibleMessages = ['Reticulating splines...', 'Constructing additional pylons...', 'Mining cryptocurrency...']
		import random
		splash.show()
		splash.raise_()
		splash.showMessage(random.choice(possibleMessages), alignment=Qt.AlignBottom | Qt.AlignLeft, color=Qt.white)
		app.processEvents()

	window = ManagerWindow(dbPath=dbPath)

	if showSplash:
		# The "I want to see my splash screen damn it" cheat
		QThread.sleep(4)
		splash.finish(window)

	window.setWindowIcon(QIcon(os.path.join(helix.root, 'ui', 'helix.icns')))
	window.show()
	window.setWindowState(window.windowState() & Qt.WindowMinimized | Qt.WindowActive)
	window.raise_()
	window.activateWindow()
	window.setTabPosition(Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea | Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea, QTabWidget.North)
	app.restoreOverrideCursor()

	# Restore geo/state settings
	window.restoreSettings()

	sys.exit(app.exec_())
