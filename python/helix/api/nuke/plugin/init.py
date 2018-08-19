from helix.api.nuke import Nuke
from helix import hxenv

Nuke.startup()

def filenameFix(filename):
	try:
		return hxenv.convertPath(filename)
	except ValueError:
		# Not within the Helix system, so I guess we just ignore
		return filename