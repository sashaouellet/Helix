import os

from helix.api.dcc import DCCPackage

SCRIPT_DIR = os.path.join(os.path.dirname(__file__), 'scripts')

class Nuke(DCCPackage):
	def __init__(self, version=None):
		super(Nuke, self).__init__('nuke', version=version)

	def runCommandLineScript(self, script, args=[]):
		return super(Nuke, self).run(args=['-t', script.rstrip('cd')] + args)