import calendar
from datetime import datetime, timedelta

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

dt = datetime.now()

print dt
print utcToLocal(dt)
