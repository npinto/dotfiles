#!/usr/bin/env python

import sys
import urllib
from BeautifulSoup import BeautifulSoup

url = sys.argv[1]

html = urllib.urlopen(url)
soup = BeautifulSoup(html)

for a in soup.findAll('a'):
    print a['href']
