from PyQt4.QtCore import *
from PyQt4.QtGui import *
import helix.api.commands as hxcmds
import sys, re
import cStringIO

class Console(QDockWidget):
	PROMPT_COLOR = 'DimGray'
	CMD_COLOR = 'LightSteelBlue'
	WARNING_COLOR = 'Moccasin'

	def __init__(self, parent):
		super(Console, self).__init__('Console', parent=parent)

		self.historyPos = 0
		self.history = []
		self._hidden = True
		self._prompt = '>>> '
		self.buildUI()
		self.makeConnections()

	def buildUI(self):
		self.widget = QWidget(self)

		self.layout = QVBoxLayout()

		self.output = QTextEdit(self)
		# self.output.setTextBackgroundColor()
		self.output.setReadOnly(True)

		self.input = CommandLineEdit(self)

		self.layout.addWidget(self.output)
		self.layout.addWidget(self.input)
		self.widget.setLayout(self.layout)

		self.setWidget(self.widget)
		self.setMinimumSize(500, 800)

	def makeConnections(self):
		self.input.returnPressed.connect(self.handleInputSent)

	def injectGetElement(self, element):
		elType = element.get('type')
		name = element.get('name')
		parent = element.get('parent').split('/')
		seq, shot = None, None

		if len(parent) > 1:
			seq, shot = parent

		cmd = ['get', elType, name]

		if seq:
			cmd.append('-sq')
			cmd.append(seq)

		if shot:
			cmd.append('-s')
			cmd.append(shot)

		self.inject(cmd)

	def inject(self, cmd):
		self.handleInputSent(' '.join(cmd))

	def handleInputSent(self, text=''):
		if not text:
			text = str(self.input.text())

		cmd = Command(text)
		self.history.append(cmd)
		self.historyPos = len(self.history)
		self.printOutput()

		stdout_ = sys.stdout
		stream = cStringIO.StringIO()
		sys.stdout = stream

		hxcmds.handleInput(str(cmd))

		sys.stdout = stdout_
		stdoutputs = stream.getvalue().split('\n')
		whitespaceRegex = re.compile(r'\s')

		for line in stdoutputs:
			if not line:
				continue

			self.output.insertHtml(self.color(line.replace(' ', '&nbsp;'*2) + '<br>', color=Console.WARNING_COLOR))

		self.output.verticalScrollBar().setValue(self.output.verticalScrollBar().maximum())
		self.input.clear()

	def previousCommand(self):
		if not self.history:
			return ''

		self.historyPos = max(0, self.historyPos - 1)

		return self.history[self.historyPos]

	def nextCommand(self):
		if not self.history:
			return ''

		self.historyPos = min(len(self.history) - 1, self.historyPos + 1)

		return self.history[self.historyPos]

	def formatCommandAtIndex(self, index=-1):
		return self.prompt() + self.color(str(self.history[index])) + '<br>'

	def printOutput(self):
		if not self.history:
			return

		self.output.moveCursor(QTextCursor.End)
		self.output.insertHtml(self.formatCommandAtIndex())

	def prompt(self):
		return self.color(self._prompt, Console.PROMPT_COLOR)

	def color(self, text, color=CMD_COLOR):
		return '<font color="{}">{}</font>'.format(color, text)

class CommandLineEdit(QLineEdit):
	def getConsole(self):
		return self.parent().parent()

	def keyPressEvent(self, event):
		if (event.key() == Qt.Key_Up):
			self.setText(str(self.getConsole().previousCommand()))
		elif (event.key() == Qt.Key_Down):
			self.setText(str(self.getConsole().nextCommand()))
		else:
			super(CommandLineEdit, self).keyPressEvent(event)

class Command(object):
	def __init__(self, line):
		self.cmd = None
		self.args = []

		parts = line.split()

		if parts:
			self.cmd = parts[0]

			if len(parts) > 1:
				self.args = parts[1:]

	def __repr__(self):
		return '{}{}{}'.format(self.cmd, ' ' if self.args else '', ' '.join(self.args))