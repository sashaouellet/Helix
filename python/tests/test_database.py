import unittest
import os, shutil

from helix.database.sql import Manager
from helix.database.show import Show
from helix.database.person import Person
from helix.database.sequence import Sequence
from helix.database.shot import Shot
from helix.database.element import Element
from helix.database.fix import Fix
from helix.database.take import Take
from helix.database.publishedFile import PublishedFile
import helix.environment.environment as env

class DatabaseTestCase(unittest.TestCase):
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

		self.assertEqual(Sequence(100, 'foobar').id, show.getSequences([100])[0].id)
		self.assertEqual(len(show.getSequences(200)), 0)

		self.assertEqual(Shot(200, 900, 'foobar').id, show.getShots(900, 200)[0].id)
		self.assertEqual(Shot(200, 900, 'foobar').id, show.getShots(900, [100, 200])[0].id)
		self.assertEqual(len(show.getShots()), 3)

		self.assertEqual(len(show.getElements()), 3)
		self.assertEqual(Element('test', 'prop', 'foobar').id, show.getElements('test', 'prop')[0].id)
		self.assertEqual(len(show.getElements(status='ip')), 0)
		self.assertEqual(len(show.getElements(authors='bob')), 0)
		self.assertEqual(len(show.getElements(authors='spaouellet')), 3)
		self.assertEqual(len(show.getElements(assignedTo='foo')), 1)
		self.assertEqual(len(show.getElements(assignedTo='foo', authors='bob')), 0)

		with self.assertRaises(ValueError):
			# Non-sanitary alias
			Show('foo bar')

		with self.assertRaises(ValueError):
			# Long alias
			Show('thisaliasiswaytoolong')

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

		show2.set('name', 'Show2') # We set without inserting
		del show2
		show2 = Show('show2')
		self.assertIs(show2.name, None)
		# Now set while inserting
		show2.set('name', 'Show2', insertIfMissing=True)
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

		seq = Sequence(100, show='foobar')

		self.assertEqual(Shot(100, 100, 'foobar').id, seq.getShots([100])[0].id)
		self.assertEqual(len(seq.getShots(300)), 0)

		with self.assertRaises(ValueError):
			badSeq = Sequence(100, show='nonextant')

		with self.assertRaises(ValueError):
			badSeq = Sequence(None)

		# Bad number
		with self.assertRaises(ValueError):
			badSeq = Sequence('foo')

		# Should convert
		self.assertEqual(Sequence('100', show='foobar').num, 100)

		self.assertIn(seq1.table, Manager.TABLE_LIST)
		self.assertFalse(os.path.exists(seq1.work_path))
		self.assertFalse(os.path.exists(seq1.release_path))

		with Manager(willCommit=False) as mgr:
			for c in [c[0] for c in mgr.getColumnNames(seq1.table)]:
				self.assertTrue(hasattr(seq1, c))

		# Try inserting again, should fail
		self.assertFalse(Sequence(100, show='foobar').insert())

	def testShot(self):
		shot = Shot(100, 100)

		self.assertTrue(shot._exists)
		self.assertTrue(shot.exists())
		self.assertTrue(Show(shot.show).exists())
		self.assertTrue(Sequence(shot.sequence).exists())

		self.assertIn(shot.table, Manager.TABLE_LIST)
		self.assertTrue(os.path.exists(shot.work_path))
		self.assertTrue(os.path.exists(shot.release_path))

		with self.assertRaises(ValueError):
			badShot = Shot(100, None, show='nonextant')

		with self.assertRaises(ValueError):
			badShot = Shot(None, None, 'foobar')

		# Bad shot number
		with self.assertRaises(ValueError):
			badShot = Shot('foo', 100, 'foobar')

		# Bad seq number
		with self.assertRaises(ValueError):
			badShot = Shot(100, 'foo', 'foobar')

		# Should convert
		self.assertEqual(Shot('100', '100', 'foobar').num, 100)
		self.assertEqual(Shot('100', '100', 'foobar').sequence, 100)

		# Non-extant sequence
		with self.assertRaises(ValueError):
			badShot = Shot(100, 200, 'foobar')

		with Manager(willCommit=False) as mgr:
			for c in [c[0] for c in mgr.getColumnNames(shot.table)]:
				self.assertTrue(hasattr(shot, c))

		# Try inserting again, should fail
		self.assertFalse(shot.insert())

	def testElement(self):
		el = Element('test', 'prop', 'foobar', 100, 100)

		self.assertFalse(el._exists)
		self.assertFalse(el.exists())
		self.assertTrue(Show(el.show).exists())
		self.assertTrue(Sequence(el.sequence, el.show).exists())
		self.assertTrue(Shot(el.shot, el.sequence, el.show).exists())

		self.assertTrue(Element('test', 'prop', 'foobar').exists())

		el.insert()
		pf = PublishedFile('test', 'prop', '', shot=100, sequence=100, show='foobar')
		pf.insert()
		self.assertEqual(el.getPublishedFiles()[0].id, pf.id)

		self.assertIn(el.table, Manager.TABLE_LIST)
		self.assertFalse(os.path.exists(el.work_path))
		self.assertFalse(os.path.exists(el.release_path))

		# No element type
		with self.assertRaises(ValueError):
			badEl = Element('foo', None, 'foobar')

		# Can be nameless, but only if we give shot and seq
		with self.assertRaises(ValueError):
			badEl = Element(None, 'prop', 'foobar')

		# Should be procedurally generated
		self.assertIsNotNone(Element(None, 'prop', 'foobar', 100, 100).name)

		# Improper element type
		with self.assertRaises(ValueError):
			badEl = Element('foo', 'bar', 'foobar')

		with Manager(willCommit=False) as mgr:
			for c in [c[0] for c in mgr.getColumnNames(el.table)]:
				self.assertTrue(hasattr(el, c))

		# Try inserting again, should fail
		self.assertFalse(Element('test', 'prop', 'foobar').insert())

	def testFix(self):
		fix1 = Fix('Test fix', 'This is the body', show='foobar')

		self.assertTrue(fix1._exists)
		self.assertTrue(fix1.exists())
		self.assertTrue(Show(fix1.show).exists())
		self.assertIs(fix1.sequence, None)
		self.assertIs(fix1.sequenceId, None)

		self.assertFalse(Fix('Test fix2', 'This is the body', show='foobar').exists())
		self.assertFalse(Fix('Test fix', 'This is the body', show='foobar', sequence=100).exists())

		# Nonextant sequence
		with self.assertRaises(ValueError):
			f = Fix('Test fix', 'This is the body', show='foobar', sequence=200)

		# Nonextant user
		with self.assertRaises(ValueError):
			f = Fix('Another fix', 'This is the body', show='foobar', author='Bob')

		with Manager(willCommit=False) as mgr:
			for c in [c[0] for c in mgr.getColumnNames(fix1.table)]:
				self.assertTrue(hasattr(fix1, c))

		# Try inserting again, should fail
		self.assertFalse(fix1.insert())

	def testPF(self):
		el = Element('test', 'prop', 'foobar')
		pf = PublishedFile(el.name, el.type, '', show=el.show)

		self.assertFalse(pf.exists())
		self.assertIsNotNone(pf.elementId)
		self.assertEqual(pf.version, 1)
		self.assertTrue(pf.insert())

		# Nonextant element
		with self.assertRaises(ValueError):
			p = PublishedFile('nonextant', 'prop', '', show=el.show)

		# Nonextant fix
		with self.assertRaises(ValueError):
			e = Element('test2', 'prop', 'foobar')
			e.insert()
			p = PublishedFile(e.name, e.type, '', show=e.show, fix=2)

		self.assertEqual(PublishedFile(el.name, el.type, '', show=el.show).version, 2)

		with Manager(willCommit=False) as mgr:
			for c in [c[0] for c in mgr.getColumnNames(pf.table)]:
				self.assertTrue(hasattr(pf, c))

		# Insert again..
		self.assertFalse(pf.insert())

	def testTake(self):
		take = Take('', 100, 100, 'foobar')

		self.assertFalse(take.exists())
		self.assertEqual(take.num, 1)

		with self.assertRaises(ValueError):
			t = Take(None, 100, 100)

		take.insert()

		take2 = Take('', 100, 100, 'foobar')
		self.assertEqual(take2.num, 2)

		take2.insert()

	@classmethod
	def setUpClass(cls):
		if not os.path.exists(os.environ['HELIX_DB']):
			if not os.path.isdir(os.path.dirname(os.environ['HELIX_DB'])):
				os.makedirs(os.path.dirname(os.environ['HELIX_DB']))

			open(os.environ['HELIX_DB'], 'w').close()

		with Manager() as mgr:
			mgr.initTables()

			Person('spaouellet').insert()
			Person('foo').insert()
			Show('foobar', makeDirs=True).insert()
			Sequence(100, 'foobar', makeDirs=True).insert()
			Sequence(900, 'foobar', makeDirs=True).insert()
			Shot(100, 100, 'foobar', makeDirs=True).insert()
			Shot(200, 100, 'foobar', makeDirs=True).insert()
			Shot(200, 900, 'foobar', makeDirs=True).insert()
			Element('test', 'prop', 'foobar', makeDirs=True).insert()
			e = Element('camera', 'camera', 'foobar', sequence=100, makeDirs=True)
			e.set('assigned_to', 'foo', insertIfMissing=True)
			Element('render', 'plate', 'foobar', shot=100, sequence=100, makeDirs=True).insert()
			Fix('Test fix', 'This is the body', show='foobar').insert()

			env.show = 'foobar'

	@classmethod
	def tearDownClass(cls):
		# return
		if os.path.isdir(os.environ['HELIX_WORK']):
			shutil.rmtree(os.environ['HELIX_WORK'])

		if os.path.isdir(os.environ['HELIX_RELEASE']):
			shutil.rmtree(os.environ['HELIX_RELEASE'])

		if os.path.exists(os.environ['HELIX_DB']):
			os.remove(os.environ['HELIX_DB'])