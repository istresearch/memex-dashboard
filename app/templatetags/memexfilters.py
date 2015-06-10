from bs4 import BeautifulSoup as bs
from django import template
import time
import urllib

register = template.Library()

def timestamp(content):
    try:
        ts = float(content) / 1000.0
    except:
        return ''
    return time.strftime("%m/%d/%y %H:%M:%S", time.gmtime(ts))

register.filter(timestamp)

def prettifyhtml(content):
    try:
        soup = bs(content)
        return soup.prettify()
    except:
        return content

register.filter(prettifyhtml)
