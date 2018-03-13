import helix
from helix.database.database import *
import helix.environment.environment as env

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic

import os
from collections import OrderedDict
from datetime import datetime

class VisualizerWindow(QMainWindow):
	HEADER_MAPPINGS = OrderedDict([
		('Name', 'name'),
		('Author', 'author'),
		('Creation', 'creation'),
		('Version', 'version'),
		('Published Version', 'pubVersion'),
		('Extension', 'ext'),
		('Sequence', 'seq')
	])

	def __init__(self):
		super(VisualizerWindow, self).__init__()
		uic.loadUi(os.path.join(helix.root, 'ui', 'visualizer.ui'), self)

		self.model = QStandardItemModel()
		self.model.setHorizontalHeaderLabels(list(VisualizerWindow.HEADER_MAPPINGS.keys()))
		self.VIEW_tree.setModel(self.model)

		self.makeConnections()
		self.show()

	def makeConnections(self):
		self.ACT_openDB.triggered.connect(self.handleOpenDB)
		self.ACT_reload.triggered.connect(self.handleDBReload)

	def handleOpenDB(self):
		test = '/home/souell20/mount/collaborative/560testing/.db/db.json'
		self.dbLoc = QFileDialog.getOpenFileName(self, caption='Open Database File', directory=test, filter='Database Files (*.json)')

		if os.path.exists(self.dbLoc):
			self.db = Database(str(self.dbLoc))

			self.populate()

	def handleDBReload(self):
		del self.db
		self.model.clear()
		self.model.setHorizontalHeaderLabels(list(VisualizerWindow.HEADER_MAPPINGS.keys()))

		self.db = Database(str(self.dbLoc))

		self.populate()

	def populate(self):
		self.ACT_reload.setEnabled(False)

		for show in self.db.getShows():
			self.addShow(show)

		self.ACT_reload.setEnabled(True)

		for col in range(self.VIEW_tree.header().count()):
			self.VIEW_tree.resizeColumnToContents(col)

	def addShow(self, show):
		showItem = QStandardItem(show.get('name', 'undefined'))

		for sequence in show.getSequences():
			showItem.appendRow(self.getSequence(sequence))

		self.addElements(showItem, show.getElements())
		self.model.appendRow(showItem)

	def getSequence(self, sequence):
		sequenceItem = QStandardItem('Sequence {}'.format(sequence.get('num', -1)))

		for shot in sequence.getShots():
			sequenceItem.appendRow(self.getShot(shot))

		self.addElements(sequenceItem, sequence.getElements())

		return sequenceItem

	def getShot(self, shot):
		shotItem = QStandardItem('Shot {}'.format(shot.get('num', -1)))

		self.addElements(shotItem, shot.getElements())

		return shotItem

	def addElements(self, parent, elements):
		els = {}

		for element in elements:
			elItem = self.getElement(element)
			elType = element.get('_DBOType', 'Element')
			elTypeItem = els.get(elType, QStandardItem(elType))

			elTypeItem.appendRow(elItem)

			els[elType] = elTypeItem

		for elTypeItem in els.itervalues():
			parent.appendRow(elTypeItem)

	def getElement(self, element):
		ret = []

		for val in VisualizerWindow.HEADER_MAPPINGS.itervalues():
			data = str(element.get(val, 'undefined'))

			if val == 'creation':
				date = datetime.strptime(data, env.DATE_FORMAT)
				data = date.strftime('%b %d %Y %I:%M%p')

			ret.append(QStandardItem(data))

		return ret

if __name__ == '__main__':
	app = QApplication(sys.argv)
	window = VisualizerWindow()

	sys.exit(app.exec_())