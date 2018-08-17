import os, sys
import collections

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic

import helix
import helix.utils.utils as utils

Comment = collections.namedtuple('Collections', ('user', 'time', 'text'))

class CommentWidget(QFrame):
	def __init__(self, parent, commentTuple):
		super(CommentWidget, self).__init__(parent)
		uic.loadUi(os.path.join(helix.root, 'ui', 'commentWidget.ui'), self)

		self.comment = Comment(*commentTuple)

		self.initUI()

	def initUI(self):
		self.LBL_user.setText('<b>{}</b>'.format(self.comment.user))
		self.LBL_date.setText(utils.relativeDate(self.comment.time))
		self.LBL_comment.setText(self.comment.text)

		# OK, this is a super hack way of getting the nice textedit background color from the stylesheet. Sorry.
		textEdit = QTextEdit()
		textEdit.ensurePolished()
		darkGray = textEdit.palette().color(textEdit.backgroundRole())
		outline = textEdit.palette().mid().color()

		self.setStyleSheet(
			'QFrame {{ \
				background-color: rgb({}, {}, {});\
			}}'
			'QFrame#{} {{ \
				border: 1px solid rgb({}, {}, {}); \
				border-radius: 13px; \
			}}'.format(darkGray.red(), darkGray.green(), darkGray.blue(), self.objectName(), outline.red(), outline.green(), outline.blue())
		)