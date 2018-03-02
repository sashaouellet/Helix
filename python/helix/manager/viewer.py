from helix.database.database import *
import helix.environment.environment as env

if __name__ == '__main__':
	dbLoc = env.getEnvironment('db')

	if not dbLoc:
		raise KeyError('Database location not set in your environment')

	db = Database(dbLoc)