from django import template
import time
register = template.Library()

def ts(timestamp):
    try:
        ts = float(timestamp) / 1000.0
    except ValueError:
        return None
    return time.strftime("%m/%d/%y %H:%M:%S", time.gmtime(ts))

register.filter(ts)

