from PySide2.QtWidgets import QApplication, QDialog

from helix.manager.element import PublishedAssetBrowser
from helix import Show, Element, PublishedFile, hxenv
import helix.api.nuke.utils as nkutils
from helix.utils.fileclassification import FrameSequence

import nuke
import os

def importAsset():
	element = Element.fromPk(hxenv.getEnvironment('element'))

	if not element:
		container = Show.fromPk(hxenv.getEnvironment('show'))
	else:
		container = element.parent

	dialog = PublishedAssetBrowser(container, parent=QApplication.instance().activeWindow())
	ret = dialog.exec_()

	if ret == QDialog.Accepted and dialog.selectedPf:
		if dialog.selectedPf.file_path:
			fs = FrameSequence(dialog.selectedPf.file_path)

			if fs.isValid():
				read = nkutils.read('{} {}-{}'.format(dialog.selectedPf.file_path, fs.first(), fs.last()))
			else:
				read = nkutils.read(dialog.selectedPf.file_path)

			nkutils.updateReadWithElementInfo(read, Element.fromPk(dialog.selectedPf.elementId), dialog.selectedPf)

def knobChanged():
	if nuke.thisNode().Class() == 'Read':
		knob = nuke.thisNode().knob('file')
		pf = PublishedFile.fromPath(knob.value())

		if pf:
			nkutils.updateReadWithElementInfo(nuke.thisNode(), Element.fromPk(pf.elementId), pf)


