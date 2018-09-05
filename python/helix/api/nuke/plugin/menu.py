import nuke

from helix.api.nuke import Nuke
import helix.api.nuke.plugin as nkplugin

Nuke.guiStartup()

nuke.addUpdateUI(nkplugin.knobChanged)