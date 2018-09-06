import unittest
import helix.utils.utils as utils
from helix.utils.fileclassification import FrameSequence, Frame

class UtilTestCase(unittest.TestCase):
	def testFrameSequence(self):
		pass
	def testIsSanitary(self):
		self.assertEqual(utils.isSanitary('foobar'), (True, []))
		self.assertEqual(utils.isSanitary('fooBar2'), (True, []))
		self.assertEqual(utils.isSanitary('foo2_bar'), (True, []))
		self.assertEqual(utils.isSanitary('foo-bar-bar', maxChars=-1), (True, []))
		self.assertEqual(utils.isSanitary('foo_2_the_bar-bar', maxChars=-1), (True, []))
		self.assertEqual(utils.isSanitary('aa'), (True, []))

		self.assertEqual(utils.isSanitary('a'),
			(
				False,
				['Must be at least 2 character(s) long']
			)
		)

		self.assertEqual(utils.isSanitary('2'),
			(
				False,
				['Must be at least 2 character(s) long',
				 'Cannot start with a dash, underscore, or number']
			),
			'Starts with number'
		)
		self.assertEqual(utils.isSanitary('222aa'),
			(
				False,
				['Cannot start with a dash, underscore, or number']
			),
			'Starts with number (multiple characters)'
		)
		self.assertEqual(utils.isSanitary('--a'),
			(
				False,
				['Cannot start with a dash, underscore, or number']
			),
			'Starts with dash'
		)
		self.assertEqual(utils.isSanitary('___'),
			(
				False,
				['Cannot start with a dash, underscore, or number',
				 'Cannot end with a dash or underscore']
			),
			'Starts with underscores'
		)
		self.assertEqual(utils.isSanitary('foo bar'),
			(
				False,
				['Cannot contain spaces']
			),
			'Has a space'
		)
		self.assertEqual(utils.isSanitary('foo.bar'),
			(
				False,
				['Cannot contain special characters']
			),
			'Has a special character (".")'
		)
		self.assertEqual(utils.isSanitary('.foobar'),
			(
				False,
				['Cannot contain special characters']
			),
			'Starts with a "."'
		)
		self.assertEqual(utils.isSanitary('@foo'),
			(
				False,
				['Cannot contain special characters']
			),
			'Starts with a "@"'
		)
		self.assertEqual(utils.isSanitary('foo_'),
			(
				False,
				['Cannot end with a dash or underscore']
			),
			'Ends with a "_"'
		)
		self.assertEqual(utils.isSanitary('foo-'),
			(
				False,
				['Cannot end with a dash or underscore']
			),
			'Ends with a "-"'
		)
		self.assertEqual(utils.isSanitary(' foo'),
			(
				False,
				['Cannot contain spaces']
			),
			'Starts with a space'
		)
		self.assertEqual(utils.isSanitary('_fo@o  -'),
			(
				False,
				['Cannot start with a dash, underscore, or number',
				 'Cannot end with a dash or underscore',
				 'Cannot contain spaces',
				 'Cannot contain special characters']
			),
			'Lots of issues'
		)