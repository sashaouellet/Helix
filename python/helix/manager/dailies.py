from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic

import os

import helix
import helix.api.commands as cmds
import helix.environment.environment as env
from helix.utils.qtutils import FilePathCompleter

class SlapCompLayer(object):
	MERGE_METHODS = ['atop', 'average', 'color-burn', 'color-dodge', 'conjoint-over', 'copy', 'difference', 'disjoint-over', 'divide', 'exclusion', 'from', 'geometric', 'hard-light', 'hypot', 'in', 'mask', 'matte', 'max', 'min', 'minus', 'multiply', 'out', 'over', 'overlay', 'plus', 'screen', 'soft-light', 'stencil', 'under', 'xor']

	def __init__(self, element):
		self.element = element

		if not self.element.get('versionInfo') or not self.element.get('pubVersion'):
			raise ValueError('Can only use elements that have been published at least once')

		self.version = int(self.element.get('pubVersion'))
		self.mergeMethod = SlapCompLayer.MERGE_METHODS.index('over')

		uic.loadUi(os.path.join(helix.root, 'ui', 'dailyBuilderDialog.ui'), self)
		self.makeConnections()

	def toWidgets(self):
		verCMB = QComboBox()
		mergeCMB = QComboBox()
		allVersions = [str(pf.version()) for pf in self.element.get('versionInfo').values()]

		verCMB.addItems(allVersions)
		mergeCMB.addItems(SlapCompLayer.MERGE_METHODS)

		verCMB.setCurrentIndex(allVersions.index(str(self.version)))
		mergeCMB.setCurrentIndex(self.mergeMethod)

		return (QLabel(self.element.get('name')), verCMB, mergeCMB)

	@staticmethod
	def fromWidgets(element, widgets):
		scl = SlapCompLayer(element)

		for w in widgets:
			scl.version = int(widgets[1].currentText())
			scl.mergeMethod = widgets[2].currentIndex()

		return scl

class SlapCompDialog(QDialog):
	def __init__(self, shot, parent=None):
		super(SlapCompDialog, self).__init__(parent)

		uic.loadUi(os.path.join(helix.root, 'ui', 'dailyBuilderDialog.ui'), self)
		self.makeConnections()

		self.shot = shot
		self.layerElements = []

	def makeConnections(self):
		self.BTN_cancel.clicked.connect(self.reject)
		self.BTN_comp.clicked.connect(self.accept)
		self.BTN_add.clicked.connect(self.handleAddElement)
		self.BTN_remove.clicked.connect(self.handleRemoveElement)
		self.BTN_up.clicked.connect(lambda: self.handleMoveElement(True))
		self.BTN_down.clicked.connect(lambda: self.handleMoveElement(False))
		self.BTN_output.clicked.connect(self.handleChooseFolder)

		self.TBL_layers.verticalHeader().setMovable(True)
		self.TBL_layers.setAcceptDrops(True)

		self.CHK_verInfo.stateChanged.connect(lambda c: self.LNE_verInfo.setEnabled(c == Qt.Checked))
		self.CHK_shotInfo.stateChanged.connect(lambda c: self.LNE_shotInfo.setEnabled(c == Qt.Checked))
		self.CHK_global.stateChanged.connect(lambda c: self.LNE_global.setEnabled(c == Qt.Checked))

	def handleChooseFolder(self):
		chosenDir = self.LNE_output.text()
		startDir = chosenDir if os.path.exists(chosenDir) and os.path.isdir(chosenDir) else os.path.expanduser('~')
		selected = QFileDialog.getExistingDirectory(self, caption='Output Folder', directory=startDir)

		if selected:
			self.LNE_output.setText(selected)

	def handleMoveElement(self, up):
		# TODO: I think I have to account for re-arranged row numbering with visualIndex...
		if not self.TBL_layers.selectionModel().hasSelection():
			return

		row = self.TBL_layers.selectionModel().selectedRows()[0].row()
		otherRow = row - 1 if up else row + 1

		if otherRow < 0 or otherRow >= self.TBL_layers.rowCount():
			return # Can't move up past index 0 or down past last index

		self.swapRows(row, otherRow)
		self.TBL_layers.setCurrentCell(otherRow, 0)

		temp = self.layerElements[row]
		self.layerElements[row] = self.layerElements[otherRow]
		self.layerElements[otherRow] = temp
	def handleRemoveElement(self):
		if not self.TBL_layers.selectionModel().hasSelection():
			return

		row = self.TBL_layers.selectionModel().selectedRows()[0].row()

		self.layerElements.pop(self.TBL_layers.verticalHeader().visualIndex(row))
		self.TBL_layers.removeRow(row)

	def swapRows(self, row1, row2):
		widgets1 = list(SlapCompLayer.fromWidgets(self.layerElements[row1], [self.TBL_layers.cellWidget(row1, c) for c in range(3)]).toWidgets())
		widgets2 = list(SlapCompLayer.fromWidgets(self.layerElements[row2], [self.TBL_layers.cellWidget(row2, c) for c in range(3)]).toWidgets())

		for i in range(3): # Run over columns, set both rows in tandem
			self.TBL_layers.setCellWidget(row1, i, widgets2[i])
			self.TBL_layers.setCellWidget(row2, i, widgets1[i])

	def handleAddElement(self):
		from helix.manager.element import ElementPickerDialog, PickMode

		els = env.show.getAllElements(elFilter=lambda e: e.get('pubVersion') is not None and e.get('versionInfo') is not None)
		d = ElementPickerDialog(els, mode=PickMode.SINGLE, parent=self)

		d.exec_()

		if len(d.selected) > 0:
			element = d.selected[0]

			try:
				widgets = SlapCompLayer(element).toWidgets()
				row = self.TBL_layers.rowCount()

				self.TBL_layers.insertRow(row)

				for i, widg in enumerate(widgets):
					self.TBL_layers.setCellWidget(row, i, widg)

				self.layerElements.append(element)
			except:
				raise

	def accept(self):
		for i in range(self.TBL_layers.rowCount()):
			print self.TBL_layers.cellWidget(self.TBL_layers.verticalHeader().visualIndex(i), 2).currentText(), self.layerElements[self.TBL_layers.verticalHeader().visualIndex(i)]

		# super(SlapCompDialog, self).accept()

	def show(self):
		self.LNE_shotInfo.setText(str(self.shot))
		self.LNE_output.setText(self.shot.getDiskLocation())

		self.outputCompleter = FilePathCompleter(self.LNE_output, startDir=self.LNE_output.text())
		self.LNE_output.setCompleter(self.outputCompleter)

		super(SlapCompDialog, self).show()