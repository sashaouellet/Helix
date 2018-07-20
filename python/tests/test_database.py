import unittest
import os, shutil

from helix.database.sql import Manager
from helix.database.show import Show
from helix.database.person import Person
from helix.database.sequence import Sequence
from helix.database.shot import Shot
import helix.environment.environment as env

'''
	MAJOR TODO:
	1. Install script for first time users
	2. Environment tab in config
'''

class TestDatabase(unittest.TestCase):
	def setUp(self):
		if not os.path.exists(os.environ['HELIX_DB']):
			if not os.path.isdir(os.path.dirname(os.environ['HELIX_DB'])):
				os.makedirs(os.path.dirname(os.environ['HELIX_DB']))

			open(os.environ['HELIX_DB'], 'w').close()

		with Manager() as mgr:
			mgr.initTables()
			show = Show('foobar')
			p1 = Person('spaouellet')

			p1.insert()
			show.insert()

			seq = Sequence(100, 'foobar')
			seq.insert()

			shot = Shot(100, 100, 'foobar')
			shot.insert()

			env.show = 'foobar'

	def testShow(self):
		# TODO: validate table columns are in object attrs
		show = Show('foobar')

		self.assertTrue(show._exists)
		self.assertTrue(show.exists())
		self.assertEqual(show.exists(fetch=True), ('foobar', None, '/tmp/helixTest/work/foobar', '/tmp/helixTest/release/foobar', 'spaouellet', show.creation))
		self.assertEqual(show.alias, 'foobar')
		self.assertEqual(show.name, None)
		self.assertEqual(show.work_path, '/tmp/helixTest/work/foobar')
		self.assertEqual(show.release_path, '/tmp/helixTest/release/foobar')
		self.assertEqual(show.author, 'spaouellet')

		self.assertEqual(show.get('alias'), 'foobar')

		# Nonextant attributes
		self.assertIs(show.get('randomAttr'), None)
		self.assertEqual(show.get('randomAttr', 'default'), 'default')

		self.assertIn(show.table, Manager.TABLE_LIST)
		self.assertTrue(os.path.exists(show.work_path))
		self.assertTrue(os.path.exists(show.release_path))

		# Test dummy show doesn't exist
		nonextant = Show('nonextant')
		self.assertFalse(nonextant._exists)
		self.assertFalse(nonextant.exists())
		self.assertIs(nonextant.exists(fetch=True), None)

		show.set('name', 'Testing')

		del show
		show = Show('foobar') # Remaking, should have saved show.name

		self.assertEqual(show.name, 'Testing')

		# Test setting on a non-db-extant show
		show2 = Show('show2')

		show2.set('name', 'Show2')
		del show2
		show2 = Show('show2')
		self.assertEqual(show2.name, 'Show2')

		# Table columns exist in attrs
		with Manager(willCommit=False) as mgr:
			for c in [c[0] for c in mgr.getColumnNames(show2.table)]:
				self.assertTrue(hasattr(show2, c))

		# Try inserting again, should fail
		self.assertFalse(show.insert())

	def testPerson(self):
		person = Person('spaouellet')

		self.assertTrue(person._exists)
		self.assertTrue(person.exists())
		self.assertEqual(person.full_name, None)
		self.assertEqual(person.department, None)
		self.assertIn(person.table, Manager.TABLE_LIST)
		self.assertTrue(person.exists())

		# Random person
		self.assertFalse(Person('bob').exists())

		person.set('full_name', 'Sasha Ouellet')
		del person
		person = Person('spaouellet')
		self.assertEqual(person.full_name, 'Sasha Ouellet')

		with Manager(willCommit=False) as mgr:
			for c in [c[0] for c in mgr.getColumnNames(person.table)]:
				self.assertTrue(hasattr(person, c))

		# Try inserting again, should fail
		self.assertFalse(person.insert())

	def testSequence(self):
		seq1 = Sequence(200)

		self.assertFalse(seq1._exists)
		self.assertFalse(seq1.exists())
		self.assertTrue(Show(seq1.show).exists())

		with self.assertRaises(ValueError):
			badSeq = Sequence(100, show='nonextant')

		with self.assertRaises(ValueError):
			badSeq = Sequence(None)

		self.assertIn(seq1.table, Manager.TABLE_LIST)
		self.assertTrue(os.path.exists(seq1.work_path))
		self.assertTrue(os.path.exists(seq1.release_path))

		with Manager(willCommit=False) as mgr:
			for c in [c[0] for c in mgr.getColumnNames(seq1.table)]:
				self.assertTrue(hasattr(seq1, c))

		# Try inserting again, should fail
		self.assertFalse(Sequence(100, show='foobar').insert())

	def testShot(self):
		shot = Shot(100, 100)

		self.assertFalse(shot._exists)
		self.assertFalse(shot.exists())
		self.assertTrue(Show(shot.show).exists())
		self.assertTrue(Sequence(shot.sequence).exists())

		self.assertIn(shot.table, Manager.TABLE_LIST)
		self.assertTrue(os.path.exists(shot.work_path))
		self.assertTrue(os.path.exists(shot.release_path))

		with Manager(willCommit=False) as mgr:
			for c in [c[0] for c in mgr.getColumnNames(shot.table)]:
				self.assertTrue(hasattr(shot, c))

		# Try inserting again, should fail
		self.assertFalse(shot.insert())

	def tearDown(self):
		self.cleanDirs()

	def cleanDirs(self):
		if os.path.isdir(os.environ['HELIX_WORK']):
			shutil.rmtree(os.environ['HELIX_WORK'])

		if os.path.isdir(os.environ['HELIX_RELEASE']):
			shutil.rmtree(os.environ['HELIX_RELEASE'])

		if os.path.exists(os.environ['HELIX_DB']):
			os.remove(os.environ['HELIX_DB'])

if __name__ == '__main__':
	os.environ['HELIX_WORK'] = '/tmp/helixTest/work'
	os.environ['HELIX_RELEASE'] = '/tmp/helixTest/release'
	os.environ['HELIX_DB'] = '/tmp/helixTest/test.db'

	unittest.main()