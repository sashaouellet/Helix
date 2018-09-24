from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic

import os, re

import helix
import helix.environment.environment as env
from helix.environment.permissions import PermissionGroup, PermissionNodes
from helix.database.person import Person
from helix import hxdb

class ConfigEditorDialog(QDialog):
	def __init__(self, parent=None):
		super(ConfigEditorDialog, self).__init__(parent)

		self.canEditConfig = parent.permHandler.check(PermissionNodes.nodes['EDIT_CONFIG'], silent=True)
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

		from helix import hxdb
		permGroups = hxdb.getAll(PermissionGroup)

		for pg in permGroups:
			if pg.group_name == 'defaultgroup':
				self.LST_groups.insertItem(0, pg.group_name)
			else:
				self.LST_groups.addItem(pg.group_name)

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
		self.BTN_removePerm.clicked.connect(self.handleRemovePerm)
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

		pg = PermissionGroup.fromPk(groupName)

		if pg is None:
			QMessageBox(QMessageBox.Warning, 'Remove Group Error', '{} doesn\'t exist'.format(groupName), buttons=QMessageBox.Ok, parent=self).exec_()
			return
		else:
			self.LST_groups.takeItem(self.LST_groups.currentRow())
			pg.delete()

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
				pg = PermissionGroup(name)
				if pg.exists():
					QMessageBox(QMessageBox.Warning, 'Create Group Error', 'The group "{}" already exists, please select a different name.'.format(name), buttons=QMessageBox.Ok, parent=self).exec_()
					return

				pg.insert()
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
		completer = QCompleter([p.username for p in hxdb.getUsers()], user)

		cancel.clicked.connect(dialog.reject)
		create.clicked.connect(dialog.accept)
		create.setDefault(True)

		user.setCompleter(completer)
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
				user = Person.fromPk(name)

				if not user:
					raise ValueError('User: {} does not exist'.format(user))

				group = str(self.LST_groups.selectedItems()[0].text())

				user.set('perm_group', group)
				self.LST_users.addItem(name)
				self.LST_users.clearSelection()
				self.LST_users.setCurrentRow(self.LST_users.count() - 1)

	def handleRemoveUser(self):
		for selected in self.LST_users.selectedItems():
			user = Person.fromPk(str(selected.text()))

			if not user:
				continue

			user.set('perm_group', PermissionGroup.DEFAULT)

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
			pg = PermissionGroup.fromPk(group)

			# Should also be impossible..
			if not pg:
				QMessageBox(QMessageBox.Warning, 'Group Error', '{} doesn\'t exist'.format(group), buttons=QMessageBox.Ok, parent=self).exec_()
				return

			if name:
				if pg.permissionList and name in pg.permissionList:
					QMessageBox(QMessageBox.Warning, 'Add Permission Error', 'The permission "{}" already exists for the group "{}".'.format(name, group), buttons=QMessageBox.Ok, parent=self).exec_()
					return

				if name not in possibleNodes:
					QMessageBox(QMessageBox.Warning, 'Add Permission Error', 'Invalid permission node. Nodes begin with the prefix "helix" (or "^helix" for negated nodes), start typing to see all options.'.format(name, group), buttons=QMessageBox.Ok, parent=self).exec_()
					return

				permList = pg.permissionList
				permList.append(name)
				pg.permissionList = permList
				pg.set('perm_nodes', pg.perm_nodes)

				self.LST_perms.addItem(name)
				self.LST_perms.clearSelection()
				self.LST_perms.setCurrentRow(self.LST_perms.count() - 1)

	def handleRemovePerm(self):
		groupName = str(self.LST_groups.selectedItems()[0].text())
		pg = PermissionGroup.fromPk(groupName)

		if pg is None:
			QMessageBox(QMessageBox.Warning, 'Remove Permission Error', '{} doesn\'t exist'.format(groupName), buttons=QMessageBox.Ok, parent=self).exec_()
			return
		elif self.LST_perms.count() > 0:
			permList = pg.permissionList

			if len(permList) == 1:
				# Don't allow people to remove the last perm node the group has
				QMessageBox(QMessageBox.Warning, 'Remove Permission Error', 'Cannot remove a permission if it is the group\'s only one', buttons=QMessageBox.Ok, parent=self).exec_()
			else:
				perm = str(self.LST_perms.takeItem(self.LST_perms.currentRow()).text())
				permList.pop(permList.index(perm))
				pg.permissionList = permList
				pg.set('perm_nodes', pg.perm_nodes)

	def handleGroupChange(self):
		selected = self.LST_groups.selectedItems()

		if len(selected) == 1:
			groupName = str(selected[0].text())
			pg = PermissionGroup.fromPk(groupName)

			if not pg:
				raise KeyError('Permission group {} is not defined'.format(groupName))

			self.LST_users.clear()
			self.LST_perms.clear()
			self.GRP_users.setEnabled(True)
			self.BTN_removeGroup.setEnabled(True)

			for user in hxdb.getUsers():
				if user.perm_group == groupName:
					self.LST_users.addItem(user.username)

				if groupName == 'defaultgroup':
					# self.LST_users.addItem('Users who are not in a group are considered a part of this one')
					self.GRP_users.setEnabled(False)
					self.BTN_removeGroup.setEnabled(False)

			for perm in pg.permissionList:
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