import os

VAR_PREFIX = 'HELIX_'

def setEnvironment(var, value):
	os.environ[VAR_PREFIX + var.upper()] = value
	
def getEnvironment(var):
	return os.environ.get(VAR_PREFIX + var.upper())
	
def getAllEnv():
	ret = {}
	
	for key, val in os.environ.iteritems():
		if key.startswith(VAR_PREFIX):
			ret[key] = val
			
	return ret
