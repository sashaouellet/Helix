import calendar
from datetime import datetime, timedelta
import re
import sys

def dbTimetoDt(dbTime):
	try:
		return datetime.strptime(dbTime, '%Y-%m-%d %H:%M:%S.%f')
	except ValueError:
		return datetime.strptime(dbTime, '%Y-%m-%d')

def prettyDate(dbTime):
	dt = dbTimetoDt(dbTime)

	return dt.strftime('%x')

def relativeDate(dbTime):
	dt = dbTimetoDt(dbTime)
	now = datetime.now()
	diff = now - dt
	seconds = diff.total_seconds()
	minutes = seconds / 60
	hours = seconds / 3600
	days = seconds / 86400
	weeks = seconds / 604800
	months = seconds / 2592000
	years = seconds / 31104000

	if seconds < 1:
		return '< 1 second ago'
	elif minutes < 1:
		return '{} seconds ago'.format(int(round(seconds)))
	elif hours < 1:
		num = int(round(minutes))
		return '{} {} ago'.format(num, 'minutes' if num > 1 else 'minute')
	elif days < 1:
		num = int(round(hours))
		return '{} {} ago'.format(num, 'hours' if num > 1 else 'hour')
	elif months < 1:
		num = int(round(days))
		if weeks < 1:
			return '{} {} ago'.format(num, 'days' if num > 1 else 'day')
		else:
			return '{} {} ago'.format(int(round(weeks)), 'weeks' if num > 1 else 'week')
	elif diff.year < 1:
		num = int(round(months))
		return '{} {} ago'.format(num, 'months' if num > 1 else 'month')
	else:
		num = int(round(years))
		return '{} {} ago'.format(num, 'years' if num > 1 else 'year')

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

def isSanitary(input, minChars=2, maxChars=10):
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

	# regx = re.compile(r'^(?!^[\-_]*$|^[0-9_\-]+$)[a-zA-Z][a-zA-Z_\-0-9]*[^\W_]$')
	sanitary = True
	reasons = []

	# if regx.match(input):
	# 	return (True, [])

	# TODO: make reasons an enum

	if minChars != -1 and len(input) < minChars:
		reasons.append('Must be at least {} character(s) long'.format(minChars))
		sanitary = False

	if maxChars != -1 and len(input) > maxChars:
		reasons.append('Must be less than {} character(s) long'.format(maxChars))
		sanitary = False

	if len(input) > 0 and re.compile(r'[\-_\d]+').match(input[0]):
		reasons.append('Cannot start with a dash, underscore, or number')
		sanitary = False

	if len(input) > 0 and re.compile(r'[\-_]+').match(input[-1]):
		reasons.append('Cannot end with a dash or underscore')
		sanitary = False

	if re.compile(r'\s').search(input):
		reasons.append('Cannot contain spaces')
		sanitary = False

	if re.compile(r'[^a-zA-Z_\-0-9\s]').search(input):
		reasons.append('Cannot contain special characters')
		sanitary = False


	return (sanitary, reasons)

def capitalize(text):
	parts = text.split()
	ret = []

	for p in parts:
		if p and len(p) > 1:
			ret.append(p[0].upper() + p[1:])
		else:
			ret.append(p[0].upper())

	return ' '.join(ret)

