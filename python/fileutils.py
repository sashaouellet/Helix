import os

PADDING = 4 # TODO pull from config file
SEQUENCE_FORMAT = 's{}'
SHOT_FORMAT = '{}'

def formatShotDir(seqNum, shotNum):
	return os.path.join(SEQUENCE_FORMAT.format(str(seqNum).zfill(PADDING)), SHOT_FORMAT.format(str(shotNum).zfill(PADDING)))