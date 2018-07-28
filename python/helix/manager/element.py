from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic

from helix.utils.qtutils import Node
import helix.utils.utils as utils
import helix

import os

class ElementNode(Node):
	MAPPING = ['name', 'type', 'version', 'parent', 'author', 'creation', 'pubVersion']

	def __init__(self, element):
		self._element = element
		self._colCount = len(ElementNode.MAPPING)
		self._children = []
		self._parent = None
		self._row = 0

	def data(self, col):
		if col >= 0 and col < len(ElementNode.MAPPING):
			return getattr(self._element, ElementNode.MAPPING[col])

class ElementSortFilterProxyModel(QSortFilterProxyModel):
	def __init__(self, parent=None):
		super(ElementSortFilterProxyModel, self).__init__(parent)

		self.elFilters = helix.database.element.Element.ELEMENT_TYPES
		self.onlyPublished = False
		self.userFilter = '*'

	def filterAcceptsRow(self, sourceRow, sourceParent):
		typeIndex = self.sourceModel().index(sourceRow, ElementNode.MAPPING.index('type'), sourceParent)
		publishedIndex = self.sourceModel().index(sourceRow, ElementNode.MAPPING.index('pubVersion'), sourceParent)
		authorIndex = self.sourceModel().index(sourceRow, ElementNode.MAPPING.index('author'), sourceParent)
		publishCond = (self.onlyPublished and int(self.sourceModel().data(publishedIndex)) != 0) or not self.onlyPublished

		return self.sourceModel().data(typeIndex) in self.elFilters and publishCond and (self.sourceModel().data(authorIndex) == self.userFilter or self.userFilter == '*')

	def updateUserFilter(self, user=None):
		if user:
			self.userFilter = user
		else:
			self.userFilter = '*'

		self.invalidateFilter()

	def updatePublishFilter(self, onlyPublished=False):
		self.onlyPublished = onlyPublished
		self.invalidateFilter()

	def updateElFilter(self, newEls):
		self.elFilters = newEls
		self.invalidateFilter()

class ElementPickerModel(QAbstractItemModel):
	HEADERS = ['Name', 'Type', 'Version', 'Container', 'Author', 'Created', 'Published Version']

	def __init__(self, elements, parent=None):
		super(ElementPickerModel, self).__init__(parent)

		self.setElements(elements)

	def setElements(self, elements):
		self.beginResetModel()

		self._root = Node()

		for el in elements:
			self._root.addChild(ElementNode(el))

		self.endResetModel()

	def columnCount(self, index):
		if index.isValid():
			return index.internalPointer().columnCount()

		return self._root.columnCount()

	def rowCount(self, index):
		if index.isValid():
			return index.internalPointer().childCount()

		return self._root.childCount()

	def headerData(self, section, orientation, role=Qt.DisplayRole):
		if orientation == Qt.Horizontal and role == Qt.DisplayRole:
			if section >= 0 and section < len(ElementPickerModel.HEADERS):
				return ElementPickerModel.HEADERS[section]
		elif orientation == Qt.Vertical:
			return QVariant()

		return super(ElementPickerModel, self).headerData(section, orientation, role=role)

	def data(self, index, role=Qt.DisplayRole):
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

class PickMode():
	SINGLE = 0
	MULTI = 1

class ElementViewWidget(QWidget):
	def __init__(self, elements=[], mode=PickMode.SINGLE, parent=None):
		super(QWidget, self).__init__(parent)

		self.mode = mode
		self.elements = elements

		self.buildUI()

	def asDockable(self):
		qdock = QDockWidget('Global Asset Viewer', self.parent())
		qdock.setWidget(self)

		return qdock

	def setElements(self, elements):
		self.model.setElements(elements)

	def buildUI(self):
		self.proxyModel = ElementSortFilterProxyModel()
		self.model = ElementPickerModel(self.elements)
		self.elementsView = QTableView(self)
		self.search = QLineEdit(self)
		self.mainLayout = QVBoxLayout()
		self.filterLayout = QGridLayout()
		self.filterGroup = QGroupBox('Filters', self)

		# Setup table view with model for the given elements
		self.proxyModel.setSourceModel(self.model)
		self.elementsView.setModel(self.proxyModel)
		self.elementsView.setSelectionModel(QItemSelectionModel(self.proxyModel))

		# Set pick mode based on init
		if self.mode == PickMode.SINGLE:
			self.elementsView.setSelectionMode(QAbstractItemView.SingleSelection)
		elif self.mode == PickMode.MULTI:
			self.elementsView.setSelectionMode(QAbstractItemView.ExtendedSelection)

		self.elementsView.setSelectionBehavior(QAbstractItemView.SelectRows)
		self.elementsView.setSortingEnabled(True)

		# Header stuff...
		hHeader = QHeaderView(Qt.Horizontal)

		hHeader.setClickable(True)
		hHeader.setResizeMode(QHeaderView.Stretch)
		hHeader.setSortIndicatorShown(True)
		self.elementsView.setHorizontalHeader(hHeader)

		# Search bar
		self.search.setPlaceholderText('Find asset...')
		self.setupSearchCompleter()

		# Filters
		self.elFilters = []

		for i, elType in enumerate(helix.database.element.Element.ELEMENT_TYPES):
			chk = QCheckBox(utils.capitalize(elType), self)
			chk.setCheckState(Qt.Checked)
			chk.stateChanged.connect(self.handleFilterUpdate)
			self.elFilters.append(chk)
			self.filterLayout.addWidget(chk, 0, i)

		self.userFilter = QCheckBox('Mine')
		self.userFilter.stateChanged.connect(self.handleUserFilter)
		self.filterLayout.addWidget(self.userFilter, 1, 0)

		self.publishedOnlyFilter = QCheckBox('Published Only')
		self.publishedOnlyFilter.stateChanged.connect(self.handlePublishFilter)
		self.filterLayout.addWidget(self.publishedOnlyFilter, 1, 1)

		self.filterGroup.setAlignment(Qt.AlignLeft)
		self.filterGroup.setLayout(self.filterLayout)

		# Add stuff to layouts
		self.mainLayout.addWidget(self.search)
		self.mainLayout.addWidget(self.filterGroup)
		self.mainLayout.addWidget(self.elementsView)

		self.setLayout(self.mainLayout)

	# Slots
	def handleUserFilter(self, state):
		if state == Qt.Checked:
			import getpass
			self.proxyModel.updateUserFilter(user=getpass.getuser())
		else:
			self.proxyModel.updateUserFilter()

	def handlePublishFilter(self, state):
		self.proxyModel.updatePublishFilter(onlyPublished=state==Qt.Checked)

	def handleFilterUpdate(self):
		keepEls = []
		for filter in self.elFilters:
			if filter.checkState() == Qt.Checked:
				keepEls.append(str(filter.text()).lower())

		self.proxyModel.updateElFilter(keepEls)

	def handleCompleterHighlight(self, text):
		selection = None

		for i in range(self.proxyModel.rowCount()):
			idx = self.proxyModel.index(i, 0)

			if idx.isValid():
				name = self.proxyModel.mapToSource(idx).internalPointer()._element.name

				if name.lower() == str(text).lower():
					selection = idx
					break

		if selection:
			selectMode = QItemSelectionModel.SelectCurrent

			if self.mode == PickMode.MULTI:
				selectMode = QItemSelectionModel.Select

			self.elementsView.selectionModel().select(idx, selectMode | QItemSelectionModel.Rows)

	def setupSearchCompleter(self):
		elList = []

		for i in range(self.proxyModel.rowCount()):
			idx = self.proxyModel.index(i, 0)

			if idx.isValid():
				elList.append(self.proxyModel.mapToSource(idx).internalPointer()._element.name)

		self.completer = QCompleter(elList, self.search)

		self.completer.highlighted.connect(self.handleCompleterHighlight)
		self.completer.setCaseSensitivity(Qt.CaseInsensitive)
		self.search.setCompleter(self.completer)

	def keyPressEvent(self, event):
		if event.key() == Qt.Key_Escape:
			self.elementsView.selectionModel().clearSelection()
			return

		super(ElementViewWidget, self).keyPressEvent(event)

class ElementPickerDialog(QDialog):
	def __init__(self, elements, mode=PickMode.SINGLE, parent=None):
		super(ElementPickerDialog, self).__init__(parent)

		self.selected = []

		self.mainLayout = QVBoxLayout()
		self.buttonLayout = QHBoxLayout()
		self.okButton = QPushButton('OK')
		self.cancelButton = QPushButton('Cancel')

		self.buttonLayout.insertStretch(0)
		self.buttonLayout.addWidget(self.cancelButton)
		self.buttonLayout.addWidget(self.okButton)

		self.elementViewerWidget = ElementViewWidget(elements, mode=mode, parent=self)

		self.mainLayout.addWidget(self.elementViewerWidget)
		self.mainLayout.addLayout(self.buttonLayout)

		self.setLayout(self.mainLayout)
		self.makeConnections()
		self.resize(800, 600)

	def getSelectedElements(self):
		if not self.elementViewerWidget.elementsView.selectionModel().hasSelection():
			return []

		selection = self.elementViewerWidget.elementsView.selectionModel().selectedRows()

		return [self.elementViewerWidget.proxyModel.mapToSource(idx).internalPointer()._element for idx in selection]

	def accept(self):
		self.selected = self.getSelectedElements()

		if not self.selected:
			return

		super(ElementPickerDialog, self).accept()

	def makeConnections(self):
		self.okButton.clicked.connect(self.accept)
		self.cancelButton.clicked.connect(self.reject)