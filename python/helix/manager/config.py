from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic

import os, re

import helix
import helix.environment.environment as env
from helix.environment.permissions import PermissionGroup, PermissionNodes

class ConfigEditorDialog(QDialog):
	def __init__(self, parent=None):
		super(ConfigEditorDialog, self).__init__(parent)

		self.canEditConfig = parent.permHandler.check(PermissionNodes.nodes['EDIT_CONFIG'], silent=True)
		print 'EDIT CONFIG', self.canEditConfig
		self.configHandler = env.getConfig()

		uic.loadUi(os.path.join(helix.root, 'ui', 'configEditor.ui'), self)
		self.makeConnections()
		self.populateConfigFields()

		if not self.canEditConfig:
			for child in self.TAB_general.children():
				if not isinstance(child, QLayout):
					child.setEnabled(False)

			for child in self.TAB_users.children():
				if not isinstance(child, QLayout):
					child.setEnabled(False)

			for child in self.TAB_exe.children():
				if not isinstance(child, QLayout):
					child.setEnabled(False)

	def populateConfigFields(self):
		if self.configHandler.dateFormat:
			self.LNE_dateFormat.setText(self.configHandler.dateFormat)

		if self.configHandler.versionPadding:
			self.SPN_versionPadding.setValue(self.configHandler.versionPadding)

		if self.configHandler.framePadding:
			self.SPN_framePadding.setValue(self.configHandler.framePadding)

		if self.configHandler.seqShotPadding:
			self.SPN_seqShotPadding.setValue(self.configHandler.seqShotPadding)

		for name, pg in self.configHandler.permGroups.iteritems():
			if name == 'defaultgroup':
				self.LST_groups.insertItem(0, name)
			else:
				self.LST_groups.addItem(name)

			self.LST_groups.setCurrentRow(0)
			self.handleGroupChange()

		if self.configHandler.mayaLinux or self.configHandler.houdiniLinux or self.configHandler.nukeLinux:
			self.GRP_linux.setChecked(True)
			if self.configHandler.mayaLinux:
				self.LNE_mayaLinux.setText(self.configHandler.mayaLinux)
			if self.configHandler.houdiniLinux:
				self.LNE_houdiniLinux.setText(self.configHandler.houdiniLinux)
			if self.configHandler.nukeLinux:
				self.LNE_nukeLinux.setText(self.configHandler.nukeLinux)
		else:
			self.GRP_linux.setChecked(False)

		if self.configHandler.mayaWin or self.configHandler.houdiniWin or self.configHandler.nukeWin:
			self.GRP_windows.setChecked(True)
			if self.configHandler.mayaWin:
				self.LNE_mayaWin.setText(self.configHandler.mayaWin)
			if self.configHandler.houdiniWin:
				self.LNE_houdiniWin.setText(self.configHandler.houdiniWin)
			if self.configHandler.nukeWin:
				self.LNE_nukeWin.setText(self.configHandler.nukeWin)
		else:
			self.GRP_windows.setChecked(False)

		if self.configHandler.mayaMac or self.configHandler.houdiniMac or self.configHandler.nukeMac:
			self.GRP_mac.setChecked(True)
			if self.configHandler.mayaMac:
				self.LNE_mayaMac.setText(self.configHandler.mayaMac)
			if self.configHandler.houdiniMac:
				self.LNE_houdiniMac.setText(self.configHandler.houdiniMac)
			if self.configHandler.nukeMac:
				self.LNE_nukeMac.setText(self.configHandler.nukeMac)
		else:
			self.GRP_mac.setChecked(False)

	def dumpSettings(self):
		self.configHandler.dateFormat = str(self.LNE_dateFormat.text())
		self.configHandler.versionPadding = int(self.SPN_versionPadding.value())
		self.configHandler.framePadding = int(self.SPN_framePadding.value())
		self.configHandler.seqShotPadding = int(self.SPN_seqShotPadding.value())

		if self.GRP_linux.isChecked():
			self.configHandler.mayaLinux = str(self.LNE_mayaLinux.text())
			self.configHandler.houdiniLinux = str(self.LNE_houdiniLinux.text())
			self.configHandler.nukeLinux = str(self.LNE_nukeLinux.text())
		else:
			self.configHandler.mayaLinux = None
			self.configHandler.houdiniLinux = None
			self.configHandler.nukeLinux = None

		if self.GRP_windows.isChecked():
			self.configHandler.mayaWin = str(self.LNE_mayaWin.text())
			self.configHandler.houdiniWin = str(self.LNE_houdiniWin.text())
			self.configHandler.nukeWin = str(self.LNE_nukeWin.text())
		else:
			self.configHandler.mayaWin = None
			self.configHandler.houdiniWin = None
			self.configHandler.nukeWin = None

		if self.GRP_mac.isChecked():
			self.configHandler.mayaMac = str(self.LNE_mayaMac.text())
			self.configHandler.houdiniMac = str(self.LNE_houdiniMac.text())
			self.configHandler.nukeMac = str(self.LNE_nukeMac.text())
		else:
			self.configHandler.mayaMac = None
			self.configHandler.houdiniMac = None
			self.configHandler.nukeMac = None

		self.configHandler.store()
		self.configHandler.write()

	def makeConnections(self):
		self.BTN_cancel.clicked.connect(self.reject)
		self.BTN_save.clicked.connect(self.accept)
		self.LST_groups.itemSelectionChanged.connect(self.handleGroupChange)
		self.BTN_addGroup.clicked.connect(self.handleAddGroup)
		self.BTN_addUser.clicked.connect(self.handleAddUser)
		self.BTN_addPerm.clicked.connect(self.handleAddPerm)
		self.BTN_removeGroup.clicked.connect(self.handleRemoveGroup)
		self.BTN_removeUser.clicked.connect(self.handleRemoveUser)
		self.BTN_mayaLinux.clicked.connect(lambda: self.handleChooseExe(self.LNE_mayaLinux))
		self.BTN_houdiniLinux.clicked.connect(lambda: self.handleChooseExe(self.LNE_houdiniLinux))
		self.BTN_nukeLinux.clicked.connect(lambda: self.handleChooseExe(self.LNE_nukeLinux))
		self.BTN_mayaWin.clicked.connect(lambda: self.handleChooseExe(self.LNE_mayaWin))
		self.BTN_houdiniWin.clicked.connect(lambda: self.handleChooseExe(self.LNE_houdiniWin))
		self.BTN_nukeWin.clicked.connect(lambda: self.handleChooseExe(self.LNE_nukeWin))
		self.BTN_mayaMac.clicked.connect(lambda: self.handleChooseExe(self.LNE_mayaMac))
		self.BTN_houdiniMac.clicked.connect(lambda: self.handleChooseExe(self.LNE_houdiniMac))
		self.BTN_nukeMac.clicked.connect(lambda: self.handleChooseExe(self.LNE_nukeMac))

	def handleChooseExe(self, field):
		curr = str(field.text())
		start = os.path.dirname(curr) if os.path.exists(os.path.dirname(curr)) else os.path.expanduser('~')
		selection = QFileDialog.getOpenFileName(self, caption='Choose Executable Location', directory=start)

		if selection:
			field.setText(selection)

	def handleRemoveGroup(self):
		selected = self.LST_groups.selectedItems()
		groupName = str(selected[0].text())

		if groupName == 'defaultgroup':
			# Should be impossible, but just in case you know...
			QMessageBox(QMessageBox.Warning, 'Remove Group Error', 'Can\'t delete defaultgroup, it must always be defined!', buttons=QMessageBox.Ok, parent=self).exec_()
			return

		self.LST_groups.takeItem(self.LST_groups.currentRow())
		self.configHandler.permGroups.pop(groupName)

	def handleAddGroup(self):
		dialog = QDialog(self)
		layout = QVBoxLayout()
		groupName = QLineEdit(dialog)
		buttonLayout = QHBoxLayout()
		cancel = QPushButton('Cancel')
		create = QPushButton('Create')

		cancel.clicked.connect(dialog.reject)
		create.clicked.connect(dialog.accept)
		create.setDefault(True)

		layout.addWidget(groupName)
		buttonLayout.addWidget(cancel)
		buttonLayout.addWidget(create)
		buttonLayout.insertStretch(0)
		layout.addLayout(buttonLayout)
		dialog.setWindowTitle('Create Group')
		dialog.setLayout(layout)

		if dialog.exec_() == QDialog.Accepted:
			name = str(groupName.text()).strip()

			if name:
				if name in self.configHandler.permGroups:
					QMessageBox(QMessageBox.Warning, 'Create Group Error', 'The group "{}" already exists, please select a different name.'.format(name), buttons=QMessageBox.Ok, parent=self).exec_()
					return

				self.configHandler.permGroups[name] = PermissionGroup(name, users=[], permissions=[])
				self.LST_groups.addItem(name)
				self.LST_groups.setCurrentRow(self.LST_groups.count() - 1)
				self.handleGroupChange()

	def handleAddUser(self):
		dialog = QDialog(self)
		layout = QVBoxLayout()
		user = QLineEdit(dialog)
		buttonLayout = QHBoxLayout()
		cancel = QPushButton('Cancel')
		create = QPushButton('Add')

		cancel.clicked.connect(dialog.reject)
		create.clicked.connect(dialog.accept)
		create.setDefault(True)

		layout.addWidget(user)
		buttonLayout.addWidget(cancel)
		buttonLayout.addWidget(create)
		buttonLayout.insertStretch(0)
		layout.addLayout(buttonLayout)
		dialog.setWindowTitle('Add User')
		dialog.setLayout(layout)

		if dialog.exec_() == QDialog.Accepted:
			name = str(user.text()).strip()

			if name:
				for pg in self.configHandler.permGroups.values():
					if pg.users and name in pg.users:
						QMessageBox(QMessageBox.Warning, 'Add User Error', 'The user "{}" already exists in group "{}", please remove them from that group before trying again.'.format(name, pg.name), buttons=QMessageBox.Ok, parent=self).exec_()
						return

				group = str(self.LST_groups.selectedItems()[0].text())

				self.configHandler.permGroups[group].users.append(name)
				self.LST_users.addItem(name)
				self.LST_users.clearSelection()
				self.LST_users.setCurrentRow(self.LST_users.count() - 1)

	def handleRemoveUser(self):
		for selected in self.LST_users.selectedItems():
			user = str(selected.text())
			group = str(self.LST_groups.selectedItems()[0].text())

			listItem = self.LST_users.findItems(user, Qt.MatchFixedString)[0]
			self.LST_users.takeItem(self.LST_users.row(listItem))
			users = self.configHandler.permGroups[group].users

			users.pop(users.index(user))

	def handleAddPerm(self):
		dialog = QDialog(self)
		layout = QVBoxLayout()
		perm = QLineEdit(dialog)
		buttonLayout = QHBoxLayout()
		cancel = QPushButton('Cancel')
		create = QPushButton('Add')
		possibleNodes = PermissionNodes.expandedNodeList()
		completer = QCompleter(possibleNodes, perm)

		perm.setToolTip('Permission nodes start with the "helix" prefix, begin typing to see available options.')
		perm.setCompleter(completer)
		cancel.clicked.connect(dialog.reject)
		create.clicked.connect(dialog.accept)
		create.setDefault(True)

		layout.addWidget(perm)
		buttonLayout.addWidget(cancel)
		buttonLayout.addWidget(create)
		buttonLayout.insertStretch(0)
		layout.addLayout(buttonLayout)
		dialog.setWindowTitle('Add Permission Node')
		dialog.setLayout(layout)

		if dialog.exec_() == QDialog.Accepted:
			name = str(perm.text()).strip()
			group = str(self.LST_groups.selectedItems()[0].text())
			pg = self.configHandler.permGroups[group]

			if name:
				if pg.permissions and name in pg.permissions:
					QMessageBox(QMessageBox.Warning, 'Add Permission Error', 'The permission "{}" already exists for the group "{}".'.format(name, group), buttons=QMessageBox.Ok, parent=self).exec_()
					return

				if name not in possibleNodes:
					QMessageBox(QMessageBox.Warning, 'Add Permission Error', 'Invalid permission node. Nodes begin with the prefix "helix" (or "^helix" for negated nodes), start typing to see all options.'.format(name, group), buttons=QMessageBox.Ok, parent=self).exec_()
					return

				group = str(self.LST_groups.selectedItems()[0].text())

				self.configHandler.permGroups[group].permissions.append(name)
				self.LST_perms.addItem(name)
				self.LST_perms.clearSelection()
				self.LST_perms.setCurrentRow(self.LST_perms.count() - 1)

	def handleGroupChange(self):
		selected = self.LST_groups.selectedItems()

		if len(selected) == 1:
			groupName = str(selected[0].text())
			pg = self.configHandler.permGroups.get(groupName)

			if not pg:
				raise KeyError('Permission group {} is not defined'.format(groupName))

			self.LST_users.clear()
			self.LST_perms.clear()
			self.GRP_users.setEnabled(True)
			self.BTN_removeGroup.setEnabled(True)

			if groupName == 'defaultgroup':
				self.LST_users.addItem('Users who are not in a group are considered a part of this one')
				self.GRP_users.setEnabled(False)
				self.BTN_removeGroup.setEnabled(False)
			else:
				for user in pg.users:
					self.LST_users.addItem(user)

			for perm in pg.permissions:
				self.LST_perms.addItem(perm)
		else:
			# Clear the users in group and permissions lists
			self.LST_users.clear()
			self.LST_perms.clear()
			self.BTN_removeGroup.setEnabled(False)

	def accept(self):
		# Save file...
		lockFile = self.CHK_lockFile.checkState() == Qt.Checked

		self.dumpSettings()

		super(ConfigEditorDialog, self).accept()