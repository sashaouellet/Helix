import os, sys

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
stylesheetPath = os.path.join(root, 'python', 'QDarkStyleSheet')

if stylesheetPath not in sys.path:
	sys.path.insert(0, stylesheetPath)