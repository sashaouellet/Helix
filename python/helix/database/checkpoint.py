from helix.database.database import DatabaseObject
from helix.database.shot import Shot
from helix.database.show import Show
import helix.environment.environment as env

class Checkpoint(DatabaseObject):
	TABLE = 'checkpoints'
	PK = 'id'

	# Stages "enum"
	LAYOUT = 'layout'
	CAMERA_POLISH = 'camera polish'
	EDITORIAL = 'editorial'
	LOCK_FOR_ANIM = 'lock for animation'
	ANIM_ROUGH = 'animation rough'
	ANIM_FINAL = 'animation final'
	SET_DECORATION = 'set decoration'
	SHADING = 'shading'
	MASTER_LIGHTING = 'master lighting'
	SHOT_LIGHTING = 'shot lighting'
	FX = 'fx'
	CFX = 'cfx'
	COMP = 'compositing'
	DIRECTOR_REVIEW = 'director review'
	DELIVERED = 'delivered'

	STAGES = [LAYOUT, CAMERA_POLISH, EDITORIAL, LOCK_FOR_ANIM, ANIM_ROUGH,
	ANIM_FINAL, SET_DECORATION, SHADING, MASTER_LIGHTING, SHOT_LIGHTING,
	FX, CFX, COMP, DIRECTOR_REVIEW, DELIVERED]

	STATUS = {
		0: 'N/A',
		1: 'pre-prod',
		2: 'assigned',
		3: 'ip',
		4: 'review',
		5: 'done'
	}

	def __init__(self, shotId, stage, show=None, dummy=False):
		self.table = Checkpoint.TABLE
		self.shotId = shotId
		self.stage = stage
		self._exists = False

		if dummy:
			return

		shot = Shot.fromPk(self.shotId)

		if shot is None or not shot.exists():
			raise ValueError('Shot does not exist')

		if stage not in Checkpoint.STAGES:
			raise ValueError('Invalid stage. Must be one of: {}'.format(', '.join(Checkpoint.STAGES)))

		fetched = self.exists(fetch=True)

		if fetched:
			self.unmap(fetched)
			self._exists = True
		else:
			self._exists = False
			self.show = show if show else env.getEnvironment('show')

			if not self.show:
				raise ValueError('Tried to fallback to environment-set show, but it was null.')

			s = Show(self.show)

			if not s.exists():
				raise ValueError('No such show: {}'.format(self.show))

			self.status = Checkpoint.STATUS[0] # Set to N/A to begin with
			self.begin_date = None
			self.completion_date = None
			self.assigned_to = None

	@property
	def pk(self):
		return Checkpoint.PK

	@property
	def id(self):
		return super(Checkpoint, self)._id(
			'{}_{}'.format(
				self.shotId,
				self.stage
			)
		)

	@staticmethod
	def dummy():
		return Checkpoint('', '', dummy=True)

