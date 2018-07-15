from PyQt4.QtCore import *
from PyQt4.QtGui import *
from helix.utils.fileclassification import FrameSequence

class ThumbnailViewer(QLabel):
	def __init__(self, seq=None):
		super(ThumbnailViewer, self).__init__()
		self.seq = seq
		self.setMinimumSize(320, 180)
		self.setMouseTracking(True)

		if self.seq:
			self.setSequence(self.seq)

	def getImageFromSequence(self, frame):
		if self.seq:
			return QPixmap(self.seq.getFrame(frame).getPath())

	def setSequence(self, seq):
		self.seq = seq
		self.image = self.getImageFromSequence(self.seq.first())
		self.setMinimumSize(1, 1)
		self.setMaximumSize(self.image.size())
		self.setPixmap(self.image.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
		self.setScaledContents(False)
		self.adjustSize()

	def mouseMoveEvent(self, event):
		if self.seq:
			perc = float(event.x()) / float(self.width())
			numFrames = self.seq.getRange()[1] - self.seq.getRange()[0]
			num = min(int(perc * numFrames) + self.seq.getRange()[0], self.seq.getRange()[1])
			self.image = self.getImageFromSequence(num)

			self.setPixmap(self.image.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

		super(ThumbnailViewer, self).mouseMoveEvent(event)

	def resizeEvent(self, event):
		self.setPixmap(self.image.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
		super(ThumbnailViewer, self).resizeEvent(event)