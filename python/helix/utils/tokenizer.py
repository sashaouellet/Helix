import re

class ConstantToken(object):
	def __init__(self, value):
		self.value = value

	def __repr__(self):
		return self.value

class VarToken(object):
	def __init__(self, var, value):
		self.var = var
		self.value = value

	def __repr__(self):
		return '{} ({})'.format(self.var, self.value)

class Tokenizer(object):
	TOKEN_PATTERN = r'({(\w+)})'

	def __init__(self, input, pattern):
		self.input = input
		self.tokens = self.tokenize(input, pattern)

	def tokenize(self, input, pattern):
		tokenNames = []
		regxPattern = '^' + pattern.replace('.', r'\.').replace('\\', '\\\\')

		for completeToken, tokenName in re.findall(Tokenizer.TOKEN_PATTERN, pattern):
			tokenNames.append(tokenName)
			regxPattern = regxPattern.replace(completeToken, '(?P<{}>.+)'.format(tokenName))

		regxPattern += '$'
		match = re.match(regxPattern, input)

		if not match:
			raise ValueError('{} does not match token pattern: {}'.format(input, pattern))

		tokens = []
		lastEndIndex = 0

		for tn in tokenNames:
			completeToken = '{' + tn + '}'
			i = pattern.index(completeToken)

			tokens.append(ConstantToken(pattern[lastEndIndex:i]))
			tokens.append(VarToken(tn, match.group(tn)))

			lastEndIndex = i + len(completeToken)

		tokens.append(ConstantToken(pattern[lastEndIndex:]))

		return tokens

	def hasToken(self, token):
		return token in [t.var for t in self.tokens if isinstance(t, VarToken)]

	def convertTo(self, newPattern):
		for token in self.tokens:
			if isinstance(token, VarToken):
				newPattern = newPattern.replace('{' + token.var + '}', token.value)

		return newPattern

	def replace(self, token, value):
		ret = ''

		for tk in self.tokens:
			if isinstance(tk, ConstantToken):
				ret += tk.value
			elif isinstance(tk, VarToken):
				if tk.var == token:
					ret += value
				else:
					ret += tk.value

		return ret

