from PySide2.QtWidgets import QApplication, QDialog

from helix.manager.element import ElementPickerDialog
import helix.api.nuke.utils as nkutils
from helix.utils.fileclassification import FrameSequence

def importAsset():
	dialog = ElementPickerDialog(parent=QApplication.instance().activeWindow(), forcePublished=True, okButtonLabel='Import')
	ret = dialog.exec_()

	if ret == QDialog.Accepted and dialog.selected:
		el = dialog.selected[0]
		latest = el.getLatestPublishedFile()

		if latest and latest.versionless_path:
			fs = FrameSequence(latest.versionless_path)

			if fs.isValid():
				read = nkutils.read('{} {}-{}'.format(latest.versionless_path, fs.first(), fs.last()))
			else:
				read = nkutils.read(latest.versionless_path)

			read.setName(str(el))
			read.knob('label').setValue('Publish version: {}'.format(latest.version))
