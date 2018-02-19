import os
import environment as env

cfg = env.getConfig()

PADDING = cfg.config.getint('Formatting', 'sequenceshotpadding')
SEQUENCE_FORMAT = 'sq{}'
SHOT_FORMAT = 's{}'

def formatShotDir(seqNum, shotNum):
	return os.path.join(SEQUENCE_FORMAT.format(str(seqNum).zfill(PADDING)), SHOT_FORMAT.format(str(shotNum).zfill(PADDING)))