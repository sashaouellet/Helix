from helix.database.database import DatabaseObject
from helix.database.shot import Shot
from helix.database.show import Show
import helix.environment.environment as env

class Checkpoint(DatabaseObject):
	TABLE = 'checkpoints'
	PK = 'shotId'

	def __init__(self, shotId, show=None, dummy=False):
		self.table = Checkpoint.TABLE
		self.shotId = shotId
		self._exists = False

		if dummy:
			return

		shot = Shot.fromPk(self.shotId)

		if shot is None or not shot.exists():
			raise ValueError('Checkpoint shot does not exist')

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

			self.new = env.getCreationInfo(format=False)[1]
			self.layout = None
			self.camera_polish = None
			self.editorial = None
			self.lock_for_anim = None
			self.anim_rough = None
			self.anim_final = None
			self.set_decoration = None
			self.shading = None
			self.master_lighting = None
			self.shot_lighting = None
			self.fx = None
			self.cfx = None
			self.comp = None
			self.director_review = None
			self.delivered = None

	@property
	def pk(self):
		return Checkpoint.PK

	@staticmethod
	def dummy():
		return Checkpoint('', dummy=True)

	@staticmethod
	def getStages():
		from helix.database.sql import Manager
		with Manager() as mgr:
			stages = [c[0] for c in mgr.getColumnNames(Checkpoint.TABLE) if c[0] not in ('shotId', 'show')]

			return stages

