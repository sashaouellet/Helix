from PySide2.QtWidgets import QApplication, QDialog

from helix.manager.element import PublishedAssetBrowser
from helix import Show, Element, hxenv
import helix.api.nuke.utils as nkutils
from helix.utils.fileclassification import FrameSequence

import nuke

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

			el = Element.fromPk(dialog.selectedPf.elementId)
			read.setName('{}_{}'.format(el.name, el.type.upper()))
			read.knob('label').setValue('Publish version: {}'.format(dialog.selectedPf.version))

			if dialog.selectedPf.version != el.pubVersion:
				read.knob('note_font_color').setValue(3036676351) # Red
			else:
				read.knob('note_font_color').setValue(4980991) # Green

			# Add element id for future reference
			elementIdKnob = nkutils.addCustomKnobWithValue(read, nuke.String_Knob, 'elementId', el.id)
			elementIdKnob.setFlag(nuke.READ_ONLY)