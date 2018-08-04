import os, sys

import helix
from helix.database.fix import Fix
import helix.database.database as db
from helix.database.show import Show
from helix.database.sequence import Sequence
from helix.database.shot import Shot
from helix.database.element import Element
from helix.database.person import Person
from helix.database.database import DatabaseObject
import helix.environment.environment as env
from helix.utils.qtutils import Node
import helix.utils.utils as utils

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic

class FixDialog(QDialog):
	def __init__(self, parent, fix=None):
		super(FixDialog, self).__init__(parent)
		uic.loadUi(os.path.join(helix.root, 'ui', 'fixCreation.ui'), self)

		self.fix = fix
		self.shots = []
		self.elements = []

		self.initUI()
		self.makeConnections()
		self.checkCanCreate()

	def initUI(self):
		self.CMB_status.setDisabled(self.fix is None)
		self.CMB_status.addItems(Fix.STATUS.values())

		self.CMB_priority.addItems(['{}{}'.format(k, ' (' + v + ')' if v else '') for k, v in Fix.PRIORITY.iteritems()])
		self.CMB_priority.setCurrentIndex(3)
		self.CMB_dept.addItems(['general'] + env.cfg.departments)

		completionList = [u.username for u in db.getUsers()]
		self.assignedCompleter = QCompleter(completionList, self.LNE_assignTo)
		self.assignedCompleter.setCaseSensitivity(Qt.CaseInsensitive)
		self.assignedCompleter.setCompletionMode(QCompleter.InlineCompletion)
		self.LNE_assignTo.setCompleter(self.assignedCompleter)
		self.LNE_assignTo.textChanged.connect(self.fixerChanged)

		self.CMB_show.addItems([s.alias for s in db.getShows()])

		today = QDate.currentDate()
		self.DATE_due.setDate(today.addDays(14))
		self.CHK_due.clicked.connect(self.toggleDue)

		self.toggleDue()
		self.populateSeqAndShot()

		if self.fix is not None:
			self.CMB_status.setCurrentIndex(self.CMB_status.findText(self.fix.status))
			self.CMB_priority.setCurrentIndex(self.fix.priority)
			self.CMB_dept.setCurrentIndex(self.CMB_dept.findText(self.fix.for_dept if self.fix.for_dept else 'general'))
			self.LNE_assignTo.setText(self.fix.fixer if self.fix.fixer else '')

			self.CMB_show.setCurrentIndex(self.CMB_show.findText(self.fix.show))
			self.CMB_show.setDisabled(True)

			self.populateSeqAndShot()

			if self.fix.sequence:
				self.CMB_seq.setCurrentIndex(self.CMB_seq.findText(str(self.fix.sequence)))

			self.CMB_seq.setDisabled(True)

			self.populateShots()

			if self.fix.shot:
				shot = Shot.fromPk(self.fix.shotId)

				for i, s in enumerate(self.shots):
					if s == shot:
						self.CMB_shot.setCurrentIndex(i)
						break

			self.CMB_shot.setDisabled(True)

			self.populateElements()

			if self.fix.elementId:
				el = Element.fromPk(self.fix.elementId)

				for i, e in enumerate(self.elements):
					if e == el:
						self.CMB_asset.setCurrentIndex(i)
						break

			self.CMB_asset.setDisabled(True)

			if self.fix.deadline:
				dt = utils.dbTimetoDt(self.fix.deadline)
				self.DATE_due.setDate(QDate(dt.year, dt.month, dt.day))
				self.CHK_due.setCheckState(Qt.Checked)

			self.LNE_title.setText(self.fix.title)
			self.TXT_body.setPlainText(self.fix.body)

			self.LNE_title.setReadOnly(True)
			self.TXT_body.setReadOnly(True)

			self.setWindowTitle('Fix #{} ({})'.format(self.fix.num, self.fix.show))

	def toggleDue(self):
		self.DATE_due.setEnabled(self.CHK_due.isChecked())

	def fixerChanged(self):
		# Updates department combo box to reflect the "assigned user's" department
		username = str(self.LNE_assignTo.text())
		deptIndex = self.CMB_dept.findText('general')
		if username and len(username) <= 10:
			user = Person(username)

			if user.exists():
				deptIndex = self.CMB_dept.findText(user.department)

		if not self.fix: # Only do this convenience switching if we are making a new fix, otherwise it's really annoying
			self.CMB_dept.setCurrentIndex(deptIndex)

	def populateElements(self):
		self.CMB_asset.clear()

		show = str(self.CMB_show.currentText())
		seq = int(str(self.CMB_seq.currentText())) if str(self.CMB_seq.currentText()) and str(self.CMB_seq.currentText()) != '--' else None
		shotIndex = self.CMB_shot.currentIndex() if str(self.CMB_shot.currentText()) and str(self.CMB_shot.currentText()) != '--' else None
		shot = self.shots[shotIndex] if shotIndex and self.shots else None
		container = Show(show)

		if shot:
			container = shot
		elif seq:
			container = Sequence(seq, show=show)

		self.elements = sorted(container.getElements(exclusive=True), key=lambda e: str(e))

		self.CMB_asset.addItems(['--'] + [str(e) for e in self.elements])
		self.elements = ['--'] + self.elements

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

		self.populateElements()

	def populateSeqAndShot(self):
		self.CMB_seq.clear()
		self._show = Show(str(self.CMB_show.currentText()))
		seqs = [str(s.num) for s in self._show.getSequences()]

		self.CMB_seq.addItems(['--'] + sorted(seqs, key=lambda s: int(s)))
		self.populateShots()

	def makeConnections(self):
		self.BTN_submit.clicked.connect(self.accept)
		self.BTN_cancel.clicked.connect(self.reject)
		self.LNE_title.textChanged.connect(self.checkCanCreate)
		self.TXT_body.textChanged.connect(self.checkCanCreate)
		self.CMB_show.currentIndexChanged.connect(self.populateSeqAndShot)
		self.CMB_seq.currentIndexChanged.connect(self.populateShots)
		self.CMB_shot.currentIndexChanged.connect(self.populateElements)

	def checkCanCreate(self):
		if not self.LNE_title.text() or not self.TXT_body.toPlainText():
			self.BTN_submit.setEnabled(False)
		else:
			self.BTN_submit.setEnabled(True)

	def accept(self):
		show = str(self.CMB_show.currentText())
		seq = int(str(self.CMB_seq.currentText())) if str(self.CMB_seq.currentText()) and str(self.CMB_seq.currentText()) != '--' else None
		shotIndex = self.CMB_shot.currentIndex() if str(self.CMB_shot.currentText()) and str(self.CMB_shot.currentText()) != '--' else None
		shot = self.shots[shotIndex] if shotIndex and self.shots else None
		elementIndex = self.CMB_asset.currentIndex() if str(self.CMB_asset.currentText()) and str(self.CMB_asset.currentText()) != '--' else None
		element = self.elements[elementIndex] if elementIndex and self.elements else None
		username = str(self.LNE_assignTo.text())
		fixer = None
		status = str(self.CMB_status.currentText())
		priority = int(self.CMB_priority.currentIndex())
		dept = str(self.CMB_dept.currentText())

		if username and len(username) <= 10:
			fixer = Person(username)

		deadline = self.DATE_due.date().toPyDate() if self.CHK_due.isChecked() else None

		if self.fix:
			# Just update instead of making a new fix
			if dept != self.fix.for_dept:
				self.fix.set('for_dept', dept)

			if status != self.fix.status:
				self.fix.set('status', status)

				if status == 'done':
					self.fix.set('fix_date', env.getCreationInfo(format=False)[1])
				else:
					self.fix.set('fix_date', None)

			fixUser = fixer.username if fixer is not None else None

			if fixUser != self.fix.fixer:
				self.fix.set('fixer', fixUser)

				if fixer is not None:
					self.fix.set('assign_date', env.getCreationInfo(format=False)[1])
					self.fix.set('status', 'assigned')
				else:
					self.fix.set('assign_date', None)
					self.fix.set('status', 'new')

			if priority != self.fix.priority:
				self.fix.set('priority', priority)

			if deadline != self.fix.deadline:
				self.fix.set('deadline', deadline)

			QMessageBox.information(self, 'Fix #{}'.format(self.fix.num), 'Changes submitted')

		else:
			# There's no command-line api for this because of how cumbersome it would be to type all these parameters from that interface
			fix = Fix(
				str(self.LNE_title.text()),
				str(self.TXT_body.toPlainText()),
				dept,
				show=show,
				sequence=seq,
				shot=shot.num if shot else None,
				clipName=shot.clipName if shot else None,
				elementName=element.name if element and not element.name.startswith('_') else None,
				elementType=element.type if element else None,
				status=status,
				priority=priority
			)

			if fixer is not None and fixer.exists():
				fix.fixer = fixer.username
				fix.assign_date = fix.creation
				fix.status = 'assigned'

			if deadline:
				fix.deadline = deadline

			if fix.insert():
				QMessageBox.information(self, 'Submitted fix #{}'.format(fix.num), 'Successfully submitted fix!')

		super(FixDialog, self).accept()

class FixView(QWidget):
	def __init__(self, parent):
		super(FixView, self).__init__(parent)
		uic.loadUi(os.path.join(helix.root, 'ui', 'fixViewer.ui'), self)

		fixes = db.getAll(Fix)

		self.proxyModel = FixSortFilterProxyModel()
		self.model = FixViewerModel(fixes)

		self.proxyModel.setSourceModel(self.model)
		self.TBL_fixes.setModel(self.proxyModel)
		self.TBL_fixes.setSelectionModel(QItemSelectionModel(self.proxyModel))

		self.sidebarModel = FixesSidebarTreeModel(fixes)
		self.TREE_sideNav.setModel(self.sidebarModel)
		self.TREE_sideNav.setAnimated(True)

		self.initUI()
		self.makeConnections()

	def asDockable(self):
		qdock = QDockWidget('Fixes', self.parent())
		qdock.setWidget(self)

		return qdock

	def initUI(self):
		depts = ['general'] + env.cfg.departments
		self.deptChecks = []

		for d in depts:
			deptCheck = QCheckBox(d)
			deptCheck.clicked.connect(self.handleDeptChange)
			self.deptChecks.append(deptCheck)
			self.SCRL_widget.layout().addWidget(deptCheck)

		completionList = [u.username for u in db.getUsers()]
		self.assignedCompleter = QCompleter(completionList, self.LNE_user)
		self.assignedCompleter.setCaseSensitivity(Qt.CaseInsensitive)
		self.assignedCompleter.setCompletionMode(QCompleter.InlineCompletion)
		self.LNE_user.setCompleter(self.assignedCompleter)

		self.CMB_priority.addItems(['{}{}'.format(k, ' (' + v + ')' if v else '') for k, v in Fix.PRIORITY.iteritems()])
		self.CMB_status.addItems(['--'] + Fix.STATUS.values())

	def makeConnections(self):
		self.CMB_due.currentIndexChanged.connect(self.handleDueDateChange)
		self.CMB_priority.currentIndexChanged.connect(self.handlePriorityChange)
		self.CMB_status.currentIndexChanged.connect(self.handleStatusChange)
		self.LNE_user.textChanged.connect(self.handleUserChange)
		self.BTN_reset.clicked.connect(self.resetFilter)
		self.TBL_fixes.doubleClicked.connect(self.openFix)
		self.TREE_sideNav.selectionModel().currentChanged.connect(self.handleSidebarNav)

	def setFixes(self, fixes):
		self.model.setFixes(fixes)

	def openFix(self, index):
		sourceIndex = self.proxyModel.mapToSource(index)
		if not sourceIndex.isValid():
			return

		fixDialog = FixDialog(self, fix=sourceIndex.internalPointer()._fix)
		ret = fixDialog.exec_()

		if ret == QDialog.Accepted:
			self.setFixes(db.getAll(Fix))

	def resetFilter(self):
		for deptCheck in self.deptChecks:
			deptCheck.setCheckState(Qt.Unchecked)

		self.CMB_priority.setCurrentIndex(0)
		self.CMB_status.setCurrentIndex(0)
		self.LNE_user.setText('')
		self.CMB_due.setCurrentIndex(0)

		self.proxyModel.updateDue()
		self.proxyModel.updateDepartments()
		self.proxyModel.updateFixer()
		self.proxyModel.updatePriority()
		self.proxyModel.updateStatus()

	def handleDueDateChange(self):
		if self.CMB_due.currentIndex() == 1:
			self.proxyModel.updateDue(30)
		elif self.CMB_due.currentIndex() == 2:
			self.proxyModel.updateDue(7)
		else:
			self.proxyModel.updateDue()

	def setDepartment(self, dept):
		for d in self.deptChecks:
			if dept == str(d.text()):
				d.setCheckState(Qt.Checked)
				break

		self.handleDeptChange()

	def handleDeptChange(self):
		depts = []

		for d in self.deptChecks:
			if d.isChecked():
				depts.append(str(d.text()))

		self.proxyModel.updateDepartments(depts)

	def setUserField(self, user):
		self.LNE_user.setText(user)
		self.handleUserChange()

	def handleUserChange(self):
		self.proxyModel.updateFixer(str(self.LNE_user.text()).strip())

	def handlePriorityChange(self):
		self.proxyModel.updatePriority(self.CMB_priority.currentIndex())

	def handleStatusChange(self):
		status = str(self.CMB_status.currentText())

		if status != '--':
			self.proxyModel.updateStatus(status)
		else:
			self.proxyModel.updateStatus()

	def handleSidebarNav(self, current, prev):
		if not current.isValid():
			return

		data = current.internalPointer()._data[0]

		if isinstance(data, DatabaseObject):
			self.proxyModel.updateTarget(target=data)
		else:
			self.proxyModel.updateTarget()

class FixSortFilterProxyModel(QSortFilterProxyModel):
	def __init__(self, parent=None):
		super (FixSortFilterProxyModel, self).__init__(parent)

		self.departments = ['general'] + env.cfg.departments
		self.fixer = None
		self.due = -1
		self.priority = 0
		self.status = None
		self.target = None

	def filterAcceptsRow(self, sourceRow, sourceParent):
		deptIndex = self.sourceModel().index(sourceRow, FixNode.MAPPING.index('for_dept'), sourceParent)
		fixerIndex = self.sourceModel().index(sourceRow, FixNode.MAPPING.index('fixer'), sourceParent)
		daysIndex = self.sourceModel().index(sourceRow, FixNode.MAPPING.index('days'), sourceParent)
		priorityIndex = self.sourceModel().index(sourceRow, FixNode.MAPPING.index('priority'), sourceParent)
		statusIndex = self.sourceModel().index(sourceRow, FixNode.MAPPING.index('status'), sourceParent)
		targetIndex = self.sourceModel().index(sourceRow, FixNode.MAPPING.index('target'), sourceParent)

		dept = self.sourceModel().data(deptIndex)
		fixer = self.sourceModel().data(fixerIndex)
		days = self.sourceModel().data(daysIndex)
		priority = self.sourceModel().data(priorityIndex)
		status = self.sourceModel().data(statusIndex)
		target = None

		if targetIndex.isValid():
			target = targetIndex.internalPointer()._fix.target

		if dept not in self.departments:
			return False

		if self.fixer is not None and self.fixer != fixer:
			return False

		if self.due != -1 and int(days) > self.due:
			return False

		if int(priority) < self.priority:
			return False

		if self.status is not None and self.status != status:
			return False

		if self.target is not None and target is not None:
			parents = [target] + [target.parent if not isinstance(target, Show) else target]

			while not isinstance(parents[-1], Show):
				parents.append(parents[-1].parent)

			if self.target not in parents:
				return False

		return True

	def updateTarget(self, target=None):
		self.target = target
		self.invalidateFilter()

	def updateDepartments(self, depts=[]):
		if not depts:
			self.departments = ['general'] + env.cfg.departments
		else:
			self.departments = depts

		self.invalidateFilter()

	def updateFixer(self, fixer=''):
		if fixer:
			self.fixer = fixer
		else:
			self.fixer = None
		self.invalidateFilter()

	def updateDue(self, days=-1):
		# If days == -1, it means the filter doesn't apply. Otherwise, we should filter <= to days
		self.due = days
		self.invalidateFilter()

	def updatePriority(self, priority=0):
		self.priority = priority
		self.invalidateFilter()

	def updateStatus(self, status=None):
		self.status = status
		self.invalidateFilter()

class FixViewerModel(QAbstractItemModel):
	HEADERS = ['Number', 'Priority', 'Show', 'Requested', 'From', 'Assigned To', 'Assigned', 'Department', 'Target', 'Status', 'Due', 'Days Left', 'Bid', 'Subject']

	def __init__(self, fixes, parent=None):
		super(FixViewerModel, self).__init__(parent)

		self.setFixes(fixes)

	def setFixes(self, fixes):
		self.beginResetModel()

		self._root = Node()

		for fix in fixes:
			self._root.addChild(FixNode(fix))

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
			if section >= 0 and section < len(FixViewerModel.HEADERS):
				return FixViewerModel.HEADERS[section]
		elif orientation == Qt.Vertical:
			return QVariant()

		return super(FixViewerModel, self).headerData(section, orientation, role=role)

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

class FixesSidebarTreeModel(QAbstractItemModel):
	def __init__(self, fixes, parent=None):
		super(FixesSidebarTreeModel, self).__init__(parent)

		self.setFixes(fixes)

	def setFixes(self, fixes):
		self.beginResetModel()

		self._root = Node()
		self.all = SidebarNode('All Fixes')
		self.all.num = len(fixes)

		self._root.addChild(self.all)

		nodes = {}

		for f in fixes:
			self.addFixTargetToTree(f.target, nodes)

		self.endResetModel()

	def addFixTargetToTree(self, target, nodes, childToAdd=None):
		if isinstance(target, Show):
			node = nodes.get(target.id)
			if node is None:
				existed = False
				node = SidebarNode(target)
				nodes[target.id] = node
				self.all.addChild(node)

			node.incrementNum()

			if childToAdd is not None:
				node.addChild(childToAdd)

			return
		else:
			parent = target.parent
			node = nodes.get(target.id)
			existed = True
			if node is None:
				existed = False
				node = SidebarNode(target)
				nodes[target.id] = node

			node.incrementNum()

			if childToAdd is not None:
				node.addChild(childToAdd)

			self.addFixTargetToTree(parent, nodes, childToAdd=node if not existed else None)

	def columnCount(self, index):
		if index.isValid():
			return index.internalPointer().columnCount()

		return self._root.columnCount()

	def rowCount(self, index):
		if index.isValid():
			return index.internalPointer().childCount()

		return self._root.childCount()

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

class SidebarNode(Node):
	def __init__(self, data=None):
		super(SidebarNode, self).__init__(data=data)
		self.num = 0

	def incrementNum(self):
		self.num += 1

	def data(self, col):
		ret = super(SidebarNode, self).data(col)

		return str(ret) + ' ({})'.format(self.num)

class FixNode(Node):
	MAPPING = ['num', 'priority', 'show', 'creation', 'author', 'fixer', 'assign_date', 'for_dept', 'target', 'status', 'deadline', 'days', 'bid', 'title']

	def __init__(self, fix):
		self._fix = fix
		self._colCount = len(FixNode.MAPPING)
		self._children = []
		self._parent = None
		self._row = 0

	def data(self, col):
		if col >=0 and col < len(FixNode.MAPPING):
			attr = FixNode.MAPPING[col]
			val = getattr(self._fix, attr)

			if val is None:
				return 'N/A'

			if attr in ('creation', 'deadline', 'assign_date'):
				return utils.prettyDate(val)
			elif attr == 'bid':
				return '{} days'.format(val)

			return val
