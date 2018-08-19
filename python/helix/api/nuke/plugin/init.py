from helix.api.nuke import Nuke
from helix import hxenv

Nuke.startup()

def filenameFix(filename):
	return hxenv.convertPath(filename)