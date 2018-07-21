import calendar
from datetime import datetime, timedelta
import re

def utcToLocal(utcDT):
	"""Converts the given datetime object (naive, UTC) into a datetime object
	for the current timezone.

	Implementation from:
	https://stackoverflow.com/questions/4563272/convert-a-python-utc-datetime-to-a-local-datetime-using-only-python-standard-lib/13287083#13287083

	Args:
		utcDT (datetime): The naive datetime object to convert

	Returns:
		datetime: The timezone converted datetime object
	"""
	timestamp = calendar.timegm(utcDT.timetuple())
	localDT = datetime.fromtimestamp(timestamp)

	assert utcDT.resolution >= timedelta(microseconds=1)

	return localDT.replace(microsecond=utcDT.microsecond)

def isSanitary(input):
	"""Any letter character followed by any number of alphanumeric characters followed by
	any character except non-alphanumeric and underscores, as long as the string is
	not comprised of ONLY digits or ONLY dashes/underscores

	In other words, the string must not start with a dash/underscore/digit and cannot end
	with a dash/underscore. The string can also not ONLY be digits or dashes/underscores,
	it must have at least 1 letter.

	Examples:
	    PASS - "foobar"
	    PASS - "fooBar2"
	    PASS - "foo2_bar"
	    PASS - "foo-bar-bar"
	    PASS - "foo_2_the_bar-bar"

	    FAIL - "2foo"
	    FAIL - "2_1"
	    FAIL - "2-1-1"
	    FAIL - "2"
	    FAIL - " "
	    FAIL - "_"
	    FAIL - "__"
	    FAIL - "-_"
	    FAIL - "-a"
	    FAIL - "-_a"
	    FAIL - "_aa"
	    FAIL - "aa_"
	    FAIL - "aaa-"
	    FAIL - "@"
	    FAIL - "221"
	    FAIL - "foo@"
	    FAIL - "f_oo@"
	    FAIL - "f!oo"
	    FAIL - "foo bar"
	    FAIL - "."
	    FAIL - "foo.bar"

	Args:
	    input (str): The string to determine if sanitary

	Returns:
	    tuple: A tuple with True/False depending on if the input is sanitary, and
	    	a list of the reasons why it failed the check. If it didn't fail, the
	    	reasons list is empty.
	"""

	regx = re.compile(r'^(?!^[\-_]*$|^[0-9_\-]+$)[a-zA-Z][a-zA-Z_\-0-9]+[^\W_]$')

	if regx.match(input):
		return (True, [])

	reasons = []

	# TODO: make reasons an enum

	if re.compile(r'[\-_\d]+').match(input[0]):
		reasons.append('Cannot start with a dash, underscore, or number')

	if re.compile(r'[\-_]+').match(input[-1]):
		reasons.append('Cannot end with a dash or underscore')

	if re.compile(r'\s').search(input):
		reasons.append('Cannot contain spaces')

	if re.compile(r'[^a-zA-Z_\-0-9\s]').search(input):
		reasons.append('Cannot contain special characters')


	return (False, reasons)

