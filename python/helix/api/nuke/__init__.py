import os

import helix
from helix.api.dcc import DCCPackage

PLUGIN = os.path.join(os.path.dirname(__file__), 'plugin')

class Nuke(DCCPackage):
	def __init__(self, version=None):
		super(Nuke, self).__init__('nuke', version=version)

	def runCommandLineScript(self, script, args=[]):
		return super(Nuke, self).run(args=['-t', script.rstrip('cd')] + args)

	@staticmethod
	def startup():
		print 'Initializing Helix Nuke startup...'
		Nuke.setResolution()
		Nuke.setFPS()
		Nuke.setFrameRange()
		print 'Done'

	@staticmethod
	def guiStartup():
		print 'Initializing Helix Nuke GUI...'
		from helix import Element, Show, Sequence, Shot, hxenv
		from helix.api.exceptions import EnvironmentError
		import helix.api.nuke.plugin as plugin
		import nuke
		helixRoot = nuke.menu('Nuke').addMenu('Helix')

		helixRoot.addCommand('Asset/Import...', plugin.importAsset)

		# File browser quick links
		try:
			element = Element.fromPk(hxenv.getEnvironment('element'))

			if element:
				nuke.addFavoriteDir(
					name='ASSET',
					directory=element.work_path
				)

				os.chdir(element.work_path)

				container = element.parent

				while not isinstance(container, Show):
					nuke.addFavoriteDir(
						name=container.__class__.__name__.upper(),
						directory=container.work_path
					)

					container = container.parent

				nuke.addFavoriteDir(
					name='SHOW',
					directory=container.work_path
				)

			print 'Done'
		except EnvironmentError:
			print 'Could not initialize Nuke for Helix without an asset'

		projDir = nuke.Root().knob('project_directory').value()

		if projDir:
			os.chdir(projDir)

	def env(self):
		return {
			'NUKE_PATH': PLUGIN
		}

	@staticmethod
	def setResolution():
		import helix.api.nuke.utils as nkutils
		import nuke
		show = helix.hxenv.getShow()

		if show:
			print 'Setting resolution...',
			formatName = '{} Format'.format(show.alias)
			width = show.resolution_x
			height = show.resolution_y
			overscanX = 0 # TODO: implement this as an option
			overscanY = 0
			x = overscanX
			y = overscanY
			r = width - overscanX
			t = height - overscanY

			format = None

			for f in nuke.formats():
				if f.name() == formatName:
					format = f
					break

			if format is not None:
				format.setWidth(width)
				format.setHeight(height)
				format.setX(x)
				format.setY(y)
				format.setR(r)
				format.setT(t)
			else:
				format = nuke.addFormat('%d %d %d %d %d %d 1.0 %s' % (width, height, x, y, r, t, formatName))

			nkutils.setRootKnobValue('format', format.name())
			print 'Done'

	@staticmethod
	def setFPS():
		import helix.api.nuke.utils as nkutils
		import nuke
		show = helix.hxenv.getShow()

		if show:
			print 'Setting FPS...',
			nkutils.setRootKnobValue('fps', show.fps)
			print 'Done'

	@staticmethod
	def setFrameRange():
		import helix.api.nuke.utils as nkutils
		import nuke
		shot = helix.hxenv.getShot()

		if shot:
			print 'Setting frame range...',
			nkutils.setRootKnobValue('first_frame', shot.start)
			nkutils.setRootKnobValue('last_frame', shot.end)
			print 'Done'

