import subprocess
import sys
import os

import helix

class DCCPackage(object):
	def __init__(self, name, version=None):
		self.name = name
		self.version = version

	@property
	def fullName(self):
		return '%s%s' % (self.name, self.version if self.version else '')

	@property
	def executable(self):
		try:
			return helix.hxenv.cfg.config.get('Executables-{}'.format(helix.hxenv.OS), self.fullName)
		except:
			raise ValueError('{} has not been configured for your OS: {}'.format(self.fullName, helix.hxenv.OS))

	def run(self, args=[], env={}):
		for e, val in os.environ.iteritems():
			if e in env:
				env[e] += os.pathsep + val
			else:
				env[e] = val

		# Also add all of our env vars, this will stomp any globals set
		env.update(helix.hxenv.getAllEnv())

		# Anything the DCC package defines/overrides as needed for the process environment
		env.update(self.env())

		# Kick it!
		p = subprocess.Popen([self.executable] + args, env=env)

		return p

	@staticmethod
	def startup():
		pass

	@staticmethod
	def guiStartup():
		pass

	@staticmethod
	def setResolution():
		raise NotImplementedError()

	@staticmethod
	def setFPS():
		raise NotImplementedError()

	@staticmethod
	def setFrameRange():
		raise NotImplementedError()

	def env(self):
		return {}

