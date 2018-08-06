import argparse

def parseArgs():
	parser = argparse.ArgumentParser(
		prog='makeTake',
		description='Makes/exports a take given an input movie or frame sequence'
	)

	parser.add_argument(
		'input',
		help='The input movie/file sequence'
	)
	parser.add_argument(
		'--seqOut',
		default=None,
		help='The full output file path for the image sequence. This should use "#" notation for the frames.'
	)
	parser.add_argument(
		'--movOut',
		default=None,
		help='The full output file path for the movie.'
	)
	parser.add_argument(
		'--showProgress',
		default=False,
		action='store_true',
		help='When enabled and a UI is available, will present a progress bar for the render operation'
	)

	return parser.parse_args()

def main(args):
	import nuke
	import helix.api.nuke.utils as nkutils
	import helix.environment.environment as env

	read = nkutils.read(file=args.input)
	first = read.knob('first').value()
	last = read.knob('last').value()
	seqWrite = None
	movWrite = None

	if args.seqOut is not None:
		seqWrite = nkutils.write(file=args.seqOut)
		seqWrite.knob('first').setValue(first)
		seqWrite.knob('last').setValue(last)

		nkutils.connect(read, seqWrite)

	if args.movOut is not None:
		movWrite = nkutils.write(file=args.movOut)
		movWrite.knob('first').setValue(first)
		movWrite.knob('last').setValue(last)

		nkutils.connect(read, movWrite)

	if seqWrite is not None:
		nuke.execute(seqWrite)

	if movWrite is not None:
		nuke.execute(movWrite)

if __name__ == '__main__':
	args = parseArgs()
	main(args)