try:
	from PySide2.QtWidgets import *
	from PySide2.QtCore import *
	from helix.utils.pysideUtils import UiLoader
	pyqtSignal = Signal
except ImportError:
	from PyQt4.QtCore import *
	from PyQt4.QtGui import *
	from PyQt4 import uic

from helix.utils.qtutils import Node
from helix.utils.fileclassification import FrameSequence
import helix.utils.utils as utils
import helix.environment.environment as env
import helix
from helix import Show, Element

import os
import collections

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
			val = getattr(self._element, ElementNode.MAPPING[col])

			if ElementNode.MAPPING[col] == 'creation':
				return utils.prettyDate(val)
			else:
				return val

	@property
	def element(self):
		return self._element

class ElementSortFilterProxyModel(QSortFilterProxyModel):
	def __init__(self, parent=None):
		super(ElementSortFilterProxyModel, self).__init__(parent)

		self.elFilters = helix.database.element.Element.ELEMENT_TYPES
		self.onlyPublished = False
		self.userFilter = '*'
		self.name = None

	def filterAcceptsRow(self, sourceRow, sourceParent):
		typeIndex = self.sourceModel().index(sourceRow, ElementNode.MAPPING.index('type'), sourceParent)
		publishedIndex = self.sourceModel().index(sourceRow, ElementNode.MAPPING.index('pubVersion'), sourceParent)
		authorIndex = self.sourceModel().index(sourceRow, ElementNode.MAPPING.index('author'), sourceParent)
		nameIndex = self.sourceModel().index(sourceRow, ElementNode.MAPPING.index('name'), sourceParent)

		elType = self.sourceModel().data(typeIndex)
		if elType not in self.elFilters:
			return False

		if self.onlyPublished and int(self.sourceModel().data(publishedIndex)) == 0:
			return False

		author = self.sourceModel().data(authorIndex)
		if self.userFilter != '*' and author != self.userFilter:
			return False

		name = self.sourceModel().data(nameIndex)
		if self.name is not None and self.name.lower() not in name.lower():
			return False

		return True

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

	def updateNameFilter(self, name=None):
		self.name = name
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

	def rowCount(self, index=QModelIndex()):
		if index.isValid():
			return index.internalPointer().childCount()

		return self._root.childCount()

	def headerData(self, section, orientation, role=Qt.DisplayRole):
		if orientation == Qt.Horizontal and role == Qt.DisplayRole:
			if section >= 0 and section < len(ElementPickerModel.HEADERS):
				return ElementPickerModel.HEADERS[section]
		elif orientation == Qt.Vertical:
			return None

		return super(ElementPickerModel, self).headerData(section, orientation, role=role)

	def data(self, index, role=Qt.DisplayRole):
		if not index.isValid():
			return None

		node = index.internalPointer()

		if node and role == Qt.DisplayRole:
			return str(node.data(index.column()))

		return None

	def supportedDropActions(self):
	    return Qt.CopyAction

	def mimeData(self, indexes):
		if len(indexes) == 0:
			return None

		data = QMimeData()
		for idx in indexes:
			el = idx.internalPointer()._element
			lastPub = el.getLatestPublishedFile()

			if lastPub and lastPub.versionless_path:
				fs = FrameSequence(lastPub.versionless_path)

				if fs.isValid():
					data.setText('{} {}-{}'.format(lastPub.versionless_path, fs.first(), fs.last()))
				else:
					data.setText(lastPub.versionless_path)

		return data

	def flags(self, index):
		default = super(ElementPickerModel, self).flags(index)
		return Qt.ItemIsDragEnabled | default

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
	elementDoubleClicked = pyqtSignal(Element)

	def __init__(self, elements=[], mode=PickMode.SINGLE, parent=None, forcePublished=False):
		super(ElementViewWidget, self).__init__(parent)

		self.mode = mode
		self.elements = elements

		self.buildUI(forcePublished)

	def asDockable(self):
		qdock = QDockWidget('Global Asset Viewer', self.parent())
		qdock.setWidget(self)

		return qdock

	def setElements(self, elements):
		self.model.setElements(elements)
		self.setupSearchCompleter()

	def buildUI(self, forcePublished):
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
		self.elementsView.setDragEnabled(True)
		self.elementsView.setAcceptDrops(True)
		self.elementsView.setDropIndicatorShown(True)
		self.elementsView.setDragDropMode(QAbstractItemView.DragOnly)

		# Header stuff...
		hHeader = QHeaderView(Qt.Horizontal)

		# Check out this hack way of supporting PySide2 and PyQt4
		if hasattr(hHeader, 'setClickable'):
			hHeader.setClickable(True)
		elif hasattr(hHeader, 'setSectionsClickable'):
			hHeader.setSectionsClickable(True)

		if hasattr(hHeader, 'setResizeMode'):
			hHeader.setResizeMode(QHeaderView.Stretch)
		elif hasattr(hHeader, 'setSectionResizeMode'):
			hHeader.setSectionResizeMode(QHeaderView.Stretch)

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

		if forcePublished:
			self.publishedOnlyFilter.setChecked(True)
			self.publishedOnlyFilter.setDisabled(True)

		self.filterLayout.addWidget(self.publishedOnlyFilter, 1, 1)

		self.elementsView.doubleClicked.connect(self.handleDoubleClick)

		self.filterGroup.setAlignment(Qt.AlignLeft)
		self.filterGroup.setLayout(self.filterLayout)

		# Add stuff to layouts
		self.mainLayout.addWidget(self.search)
		self.mainLayout.addWidget(self.filterGroup)
		self.mainLayout.addWidget(self.elementsView)

		self.setLayout(self.mainLayout)

	# Slots
	def handleDoubleClick(self, index):
		if not index or not index.isValid():
			return

		# We only want to provide double click functionality for asset selection in single picker mode
		if self.mode != PickMode.SINGLE:
			return

		el = self.proxyModel.mapToSource(index).internalPointer().element

		self.elementDoubleClicked.emit(el)

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
	def __init__(self, elements=None, mode=PickMode.SINGLE, parent=None, forcePublished=False, okButtonLabel='OK'):
		super(ElementPickerDialog, self).__init__(parent)

		self.selected = []

		self.mainLayout = QVBoxLayout()
		self.buttonLayout = QHBoxLayout()
		self.okButton = QPushButton(okButtonLabel)
		self.cancelButton = QPushButton('Cancel')

		self.buttonLayout.insertStretch(0)
		self.buttonLayout.addWidget(self.cancelButton)
		self.buttonLayout.addWidget(self.okButton)

		if not elements:
			elements = Show.fromPk(env.getEnvironment('show')).getElements()

		self.elementViewerWidget = ElementViewWidget(elements, mode=mode, parent=self, forcePublished=forcePublished)

		self.mainLayout.addWidget(self.elementViewerWidget)
		self.mainLayout.addLayout(self.buttonLayout)
		self.setMouseTracking(True)

		self.setWindowTitle('Asset Browser')
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

	def reject(self):
		self.elementViewerWidget.elementsView.selectionModel().clearSelection()
		self.selected = []

		super(ElementPickerDialog, self).reject()

	def makeConnections(self):
		self.okButton.clicked.connect(self.accept)
		self.cancelButton.clicked.connect(self.reject)
		self.elementViewerWidget.elementDoubleClicked.connect(self.accept)

class PublishedAssetBrowser(QDialog):
	def __init__(self, container, parent=None):
		super(PublishedAssetBrowser, self).__init__(parent)

		# TODO: probably want to move into qtUtils..
		if 'uic' in globals():
			uic.loadUi(os.path.join(helix.root, 'ui', 'publishBrowser.ui'), self)
		else:
			loader = UiLoader(self)
			loader.load(QFile(os.path.join(helix.root, 'ui', 'publishBrowser.ui')))

		self.container = container
		self.pfMapping = collections.OrderedDict()
		self.selectedPf = None

		from helix import ElementContainer
		if not isinstance(container, ElementContainer):
			raise ValueError('Container must be of type ElementContainer. Got: {}'.format(container.__class__.__name__))

		self.model = ElementPickerModel([e for e in self.container.getElements() if e.pubVersion != 0], self)
		self.proxyModel = ElementSortFilterProxyModel(parent=self)

		self.initUI()
		self.makeConnections()

	def initUI(self):
		self.CHK_limitScope.setText('Limit to assets in {}'.format(str(self.container)))
		self.populatePfTypes()

		self.proxyModel.setSourceModel(self.model)
		self.TREE_assets.setModel(self.proxyModel)
		self.TREE_assets.setSelectionModel(QItemSelectionModel(self.proxyModel))
		# self.proxyModel.updatePublishFilter(onlyPublished=True)

	def makeConnections(self):
		self.BTN_import.clicked.connect(self.accept)
		self.BTN_cancel.clicked.connect(self.reject)
		self.CHK_limitScope.clicked.connect(self.handleLimitAssetScope)
		self.CMB_pfFileType.currentIndexChanged.connect(self.handlePfTypeChosen)
		self.CMB_versions.currentIndexChanged.connect(self.handlePfChosen)
		self.LNE_search.textEdited.connect(self.handleFilter)
		self.TREE_assets.selectionModel().currentChanged.connect(self.handleAssetSelected)

		self.setupSearchCompleter()

	def populatePfTypes(self):
		self.CMB_pfFileType.clear()
		self.CMB_pfFileType.addItems(['--'] + self.getPublishedFileTypes())

	def getPublishedFileTypes(self):
		return []

	def handleFilter(self):
		self.proxyModel.updateNameFilter(str(self.LNE_search.text()))

	def handleAssetSelected(self, current, previous):
		self.CMB_versions.clear()
		self.pfMapping = collections.OrderedDict()

		if not current or not current.isValid():
			self.BTN_import.setEnabled(False)
			return

		el = self.proxyModel.mapToSource(current).internalPointer()._element
		versions = sorted(el.getPublishedFiles(), reverse=True, key=lambda pf: pf.version)

		for pf in versions:
			self.pfMapping['Version {} ({})'.format(pf.version, utils.prettyDate(pf.creation))] = pf

		self.CMB_versions.addItems(self.pfMapping.keys())
		self.BTN_import.setEnabled(True)

	def handlePfChosen(self):
		self.selectedPf = self.pfMapping.get(str(self.CMB_versions.currentText()))

	def handleLimitAssetScope(self):
		if self.CHK_limitScope.isChecked():
			# Just this scope's elements (the container)
			self.model.setElements([e for e in self.container.getElements() if e.pubVersion != 0])
		else:
			# Set to show wide elements
			self.model.setElements([e for e in Show.fromPk(self.container.show).getElements() if e.pubVersion != 0])

		self.populatePfTypes()
		self.setupSearchCompleter()
		self.handleAssetSelected(QModelIndex(), QModelIndex())

	def reject(self):
		self.selectedPf = None
		super(PublishedAssetBrowser, self).reject()

	def handlePfTypeChosen(self):
		pass

	def setupSearchCompleter(self):
		elList = []

		for i in range(self.model.rowCount()):
			idx = self.model.index(i, 0)

			if idx.isValid():
				elList.append(idx.internalPointer()._element.name)

		self.completer = QCompleter(elList, self.LNE_search)

		self.completer.setCaseSensitivity(Qt.CaseInsensitive)
		self.LNE_search.setCompleter(self.completer)
