import os, sys

import helix.database.database as hxdb
import helix.environment.environment as hxenv
from helix.database.database import DatabaseObject
from helix.database.show import Show
from helix.database.sequence import Sequence
from helix.database.shot import Shot
from helix.database.element import Element
from helix.database.elementContainer import ElementContainer
from helix.database.person import Person
from helix.database.fix import Fix
from helix.database.publishedFile import PublishedFile
from helix.database.take import Take
from helix.database.checkpoint import Checkpoint
from helix.database.sql import Manager

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
stylesheetPath = os.path.join(root, 'python', 'QDarkStyleSheet')

if stylesheetPath not in sys.path:
	sys.path.insert(0, stylesheetPath)