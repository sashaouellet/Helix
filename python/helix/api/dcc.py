import subprocess
import sys

import helix.environment.environment as hxenv

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
			return hxenv.cfg.config.get('Executables-{}'.format(hxenv.OS), self.fullName)
		except:
			raise ValueError('{} has not been configured for your OS: {}'.format(self.fullName, hxenv.OS))

	def run(self, args=[], env={}):
		# Inject our python path for the process
		hxPython = hxenv.getEnvironment('python')
		pythonPath = env.get('PYTHONPATH', '')

		if hxPython not in pythonPath:
			pythonPath += ';%s' % hxPython
			pythonPath = pythonPath.lstrip(';')

		env['PYTHONPATH'] = pythonPath

		# Also add all of our env vars
		env.update(hxenv.getAllEnv())

		# Kick it!
		p = subprocess.Popen([self.executable] + args, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

		return p