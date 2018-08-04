import os, sys
import collections

import helix
import helix.database.database as db
import helix.environment.environment as env
from helix.database.checkpoint import Checkpoint
from helix.database.person import Person
import helix.utils.utils as utils
from helix.utils.qtutils import Node

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic

class UpdateCheckpointDialog(QDialog):
	def __init__(self, parent, shot):
		super(UpdateCheckpointDialog, self).__init__(parent)
		uic.loadUi(os.path.join(helix.root, 'ui', 'updateCheckpoints.ui'), self)

		self.shot = shot

		self.initUI()
		self.makeConnections()

	def initUI(self):
		stages = [utils.capitalize(s) for s in Checkpoint.STAGES]
		self.CMB_stages.addItems(stages)
		self.CMB_status.addItems(Checkpoint.STATUS.values())
		self.LBL_notIn = QLabel('<font color=red>Not included in this shot</font>')
		self.currStatusWidget = self.CMB_status

		completionList = [u.username for u in db.getUsers()]
		self.assignedCompleter = QCompleter(completionList, self.LNE_assignee)
		self.assignedCompleter.setCaseSensitivity(Qt.CaseInsensitive)
		self.assignedCompleter.setCompletionMode(QCompleter.InlineCompletion)
		self.LNE_assignee.setCompleter(self.assignedCompleter)

		self.setWindowTitle('Checkpoints for {} in {} ({})'.format(self.shot, self.shot.parent, self.shot.show))
		self.handleStageChanged()

	def makeConnections(self):
		self.BTN_add.clicked.connect(self.handleAddStage)
		self.BTN_remove.clicked.connect(self.handleRemoveStage)
		self.BTN_reset.clicked.connect(self.handleResetStage)
		self.BTN_cancel.clicked.connect(self.reject)
		self.BTN_ok.clicked.connect(self.accept)
		self.CMB_stages.currentIndexChanged.connect(self.handleStageChanged)

	def handleAddStage(self):
		stage = str(self.CMB_stages.currentText()).lower()
		cp = Checkpoint(self.shot.id, stage, show=self.shot.show)

		if cp.insert():
			self.handleStageChanged()
		else:
			raise ValueError('Something went wrong trying to add this stage')

	def handleRemoveStage(self):
		ret = QMessageBox.warning(
			self,
			'Remove Checkpoint Stage',
			'Removing this stage will reset the status, assignee, and start/end dates set. The stage will also be removed from consideration for the shot. Are you sure you want to continue?',
			QMessageBox.No | QMessageBox.Yes,
			QMessageBox.No
			)

		if ret == QMessageBox.Yes:
			stage = str(self.CMB_stages.currentText()).lower()
			cp = Checkpoint(self.shot.id, stage, show=self.shot.show)

			if cp.exists():
				cp.delete()
			else:
				raise ValueError('Checkpoint does not exist, can\'t remove')

			self.handleStageChanged()

	def handleResetStage(self):
		ret = QMessageBox.warning(
			self,
			'Reset Checkpoint Stage',
			'Resetting this stage will reset the status, assignee, and start/end dates set. Are you sure you want to continue?',
			QMessageBox.No | QMessageBox.Yes,
			QMessageBox.No
			)

		if ret == QMessageBox.Yes:
			stage = str(self.CMB_stages.currentText()).lower()
			cp = Checkpoint(self.shot.id, stage, show=self.shot.show)

			if cp.exists():
				cp.set('status', Checkpoint.STATUS[0])
				cp.set('begin_date', None)
				cp.set('completion_date', None)
			else:
				raise ValueError('Checkpoint does not exist, can\'t remove')

			self.handleStageChanged()

	def handleStageChanged(self):
		stage = str(self.CMB_stages.currentText()).lower()
		cp = Checkpoint(self.shot.id, stage, show=self.shot.show)

		self.LAY_form.removeWidget(self.currStatusWidget)
		self.currStatusWidget.hide()

		if cp.exists():
			self.BTN_add.setEnabled(False)
			self.BTN_remove.setEnabled(True)
			self.LNE_assignee.setEnabled(True)
			self.LAY_form.setWidget(0, QFormLayout.FieldRole, self.CMB_status)
			self.currStatusWidget = self.CMB_status
			self.CMB_status.setCurrentIndex(self.CMB_status.findText(cp.status))
		else:
			self.BTN_add.setEnabled(True)
			self.BTN_remove.setEnabled(False)
			self.LNE_assignee.setEnabled(False)
			self.LAY_form.setWidget(0, QFormLayout.FieldRole, self.LBL_notIn)
			self.currStatusWidget = self.LBL_notIn

		if cp.begin_date:
			self.LBL_startDate.setText(utils.prettyDate(cp.begin_date))
		else:
			self.LBL_startDate.setText('--')

		if cp.completion_date:
			self.LBL_endDate.setText(utils.prettyDate(cp.begin_date))
		else:
			self.LBL_endDate.setText('--')

		if cp.assigned_to:
			self.LNE_assignee.setText(cp.assigned_to)
		else:
			self.LNE_assignee.setText('')

		self.currStatusWidget.show()

	def accept(self):
		stage = str(self.CMB_stages.currentText()).lower()
		status = str(self.CMB_status.currentText())
		assignee = str(self.LNE_assignee.text())
		user = None

		if assignee:
			user = Person(assignee)
			assignee = user.username
		else:
			assignee = None

		if user and not user.exists():
			QMessageBox.warning(self, 'Checkpoints', 'Specified assignee does not exist')
			return

		cp = Checkpoint(self.shot.id, stage, show=self.shot.show)

		if status != cp.status:
			if status == Checkpoint.STATUS[0]: # N/A
				cp.set('status', status)
				cp.set('begin_date', None)
				cp.set('completion_date', None)
			elif status == Checkpoint.STATUS[1]: # pre-prod
				cp.set('status', status)
				cp.set('completion_date', None)
				if cp.status == Checkpoint.STATUS[0]: # If was N/A, set begin date
					cp.set('begin_date', env.getCreationInfo(format=False)[1])
			elif status == Checkpoint.STATUS[2]: # assigned
				cp.set('status', status)
				cp.set('completion_date', None)
				if cp.status == Checkpoint.STATUS[0]: # If was N/A, set begin date
					cp.set('begin_date', env.getCreationInfo(format=False)[1])
			elif status == Checkpoint.STATUS[3]: # ip
				cp.set('status', status)
				cp.set('completion_date', None)
				if cp.status == Checkpoint.STATUS[0]: # If was N/A, set begin date
					cp.set('begin_date', env.getCreationInfo(format=False)[1])
			elif status == Checkpoint.STATUS[4]: # review
				cp.set('status', status)
				cp.set('completion_date', None)
				if cp.status == Checkpoint.STATUS[0]: # If was N/A, set begin date
					cp.set('begin_date', env.getCreationInfo(format=False)[1])
			elif status == Checkpoint.STATUS[5]: # done
				cp.set('status', status)
				if cp.status == Checkpoint.STATUS[0]: # If was N/A, set begin date
					cp.set('begin_date', env.getCreationInfo(format=False)[1])
				cp.set('completion_date', env.getCreationInfo(format=False)[1])

		if assignee != cp.assigned_to:
			cp.set('assigned_to', assignee)

		QMessageBox.information(self, 'Checkpoints', 'Successfully updated checkpoint stage "{}"'.format(stage))

		super(UpdateCheckpointDialog, self).accept()

class CheckpointStatusDialog(QDialog):
	def __init__(self, parent, sequence):
		super(CheckpointStatusDialog, self).__init__(parent)
		uic.loadUi(os.path.join(helix.root, 'ui', 'checkpointStatus.ui'), self)

		self.sequence = sequence

		self.initUI()
		self.makeConnections()

	def initUI(self):
		stageCounter = collections.defaultdict(int)
		shotsStarted = 0
		shotsDone = 0
		seqShots = self.sequence.getShots()

		for shot in seqShots:
			started = False
			done = True
			for cp in shot.getCheckpoints():
				stageCounter[cp.stage] += 1

				# If we find any checkpoint in the shot that isn't "N/A" or "done", mark the whole shot as IP
				if cp.status not in (Checkpoint.STATUS[0], Checkpoint.STATUS[5]):
					started = True

				# If we find any checkpoint in the shot that isn't "done", mark the whole shot as not done
				if cp.status != Checkpoint.STATUS[5]:
					done = False

			if started:
				shotsStarted += 1

			if done:
				shotsDone += 1

		if seqShots:
			self.WIDG_stats.layout().setWidget(0, QFormLayout.LabelRole, QLabel('Shots IP'))
			shotPortionString = '%d / %d' % (shotsStarted, len(seqShots))
			self.WIDG_stats.layout().setWidget(0, QFormLayout.FieldRole, QLabel('%-9s (%.1f%%)' % (shotPortionString, 100 * float(shotsStarted) / len(seqShots))))

			self.WIDG_stats.layout().setWidget(1, QFormLayout.LabelRole, QLabel('Shots Done'))
			shotPortionString = '%d / %d' % (shotsDone, len(seqShots))
			self.WIDG_stats.layout().setWidget(1, QFormLayout.FieldRole, QLabel('%-9s (%.1f%%)' % (shotPortionString, 100 * float(shotsDone) / len(seqShots))))

			row = 2
			for stage in Checkpoint.STAGES:
				if stage != Checkpoint.DELIVERED:
					count = stageCounter[stage]
					self.WIDG_stats.layout().setWidget(row, QFormLayout.LabelRole, QLabel('Shots with {}:'.format(utils.capitalize(stage))))

					shotPortionString = '%d / %d' % (count, len(seqShots))
					self.WIDG_stats.layout().setWidget(row, QFormLayout.FieldRole, QLabel('%-9s (%.1f%%)' % (shotPortionString, 100 * float(count) / len(seqShots))))
					row += 1

		self.model = CheckpointStatusModel(seqShots, self)
		self.TREE_checkpoints.setModel(self.model)

	def makeConnections(self):
		pass

class CheckpointStatusModel(QAbstractItemModel):
	HEADERS = ['', 'Status', 'Assignee', 'Started', 'Completed']

	def __init__(self, shots, parent=None):
		super(CheckpointStatusModel, self).__init__(parent)

		self.setShots(shots)

	def setShots(self, shots):
		self.beginResetModel()

		self._root = Node()

		for shot in shots:
			shotNode = Node(str(shot), defaultVal='')
			self._root.addChild(shotNode)

			checkpoints = sorted(shot.getCheckpoints(), key=lambda c: Checkpoint.STAGES.index(c.stage))

			for cp in checkpoints:
				shotNode.addChild(CheckpointNode(cp))

		self.endResetModel()

	def headerData(self, section, orientation, role=Qt.DisplayRole):
		if orientation == Qt.Horizontal and role == Qt.DisplayRole:
			if section >= 0 and section < len(CheckpointStatusModel.HEADERS):
				return CheckpointStatusModel.HEADERS[section]
		elif orientation == Qt.Vertical:
			return QVariant()

		return super(CheckpointStatusModel, self).headerData(section, orientation, role=role)

	def columnCount(self, index):
		if index.isValid():
			return index.internalPointer().columnCount()

		return len(CheckpointNode.MAPPING)

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

class CheckpointNode(Node):
	MAPPING = ['stage', 'status', 'assigned_to', 'begin_date', 'completion_date']

	def __init__(self, checkpoint):
		self._checkpoint = checkpoint
		self._colCount = len(CheckpointNode.MAPPING)
		self._children = []
		self._parent = None
		self._row = 0

	def data(self, col):
		if col >= 0 and col < len(CheckpointNode.MAPPING):
			attr = CheckpointNode.MAPPING[col]
			val = getattr(self._checkpoint, attr)

			if val is None:
				return 'N/A'

			if attr in ('begin_date', 'completion_date'):
				return utils.prettyDate(val)
			elif attr == 'stage':
				return utils.capitalize(val)

			return val
