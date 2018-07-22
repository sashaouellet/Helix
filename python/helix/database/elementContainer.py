import helix.environment.environment as env

class ElementContainer(object):
	def __init__(self, show=None, sequence=None, shot=None):
		self.show = show if show else env.show

		if not self.show:
			raise ValueError('Tried to fallback to environment-set show, but it was null.')

		if not Show(self.show).exists():
			raise ValueError('No such show: {}'.format(self.show))

		self.sequence = sequence
		self.shot = shot

	def getElement(self, name, elType):
		from helix.database.element import Element

		try:
			el = Element(name, elType, show=self.show, sequence=self.sequence, shot=self.shot)

			if el.exists():
				return el
			else:
				return None
		except:
			return None