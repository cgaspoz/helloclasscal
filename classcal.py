# -*- coding: UTF-8 -*-
# classcal.py
#
# Copyright (C) 2015 Cédric Gaspoz
#
# Author(s): Cédric Gaspoz <cedric@gaspoz-fleiner.com>
#
# This file is part of helloclasscal.
#
# helloclasscal is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# helloclasscal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with helloclasscal. If not, see <http://www.gnu.org/licenses/>.

# Stdlib imports
import requests
import mysql.connector
import datetime
import pytz
from yaml import load
from xmpp_bot import send_xmpp
import dateutil
from icalendar import Calendar, Event
import tempfile
import os


CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(CURRENT_PATH, 'config', 'helloclass.yaml'), 'r') as stream:
    config = load(stream)

HELLO = config['helloclass']
DB = config['mysql']

URL = 'https://www.helloclass.ch/login/'

messages = []

session = requests.Session()

# Retrieve the CSRF token first
session.get(URL)  # sets cookie
csrftoken = session.cookies['csrftoken']

login_data = dict(username=HELLO['username'], password=HELLO['password'], csrfmiddlewaretoken=csrftoken)
session.post(URL, data=login_data, headers=dict(Referer=URL))
r = session.get('https://www.helloclass.ch/api/v1/assignment/?limit=100&offset=0&start__gte=%s&year_subject__in=2451' % (datetime.datetime.now()-datetime.timedelta(weeks=1)).strftime("%Y-%m-%d"))
j = r.json()

cnx = mysql.connector.connect(user=DB['user'], password=DB['password'], host=DB['host'], database=DB['database'])
cursor = cnx.cursor()

add_assignment = ("INSERT INTO assignment (idassignment, kind_name, kind, background_color, text, start, end, created, modified) "
                  "VALUES (%(id)s, %(kind_name)s, %(kind)s, %(background_color)s, %(text)s, %(start)s, %(end)s, %(created)s, %(modified)s) "
                  "ON DUPLICATE KEY UPDATE kind_name=%(kind_name)s, kind=%(kind)s, background_color=%(background_color)s, text=%(text)s, start=%(start)s, end=%(end)s, modified=%(modified)s")
add_assignment_file = ("INSERT INTO assignment_file (idassignment_file, url, filename, created, modified, idassignment) "
                       "VALUES (%(id)s, %(url)s, %(filename)s, %(created)s, %(modified)s, %(idassignment)s) "
                       "ON DUPLICATE KEY UPDATE url=%(url)s, filename=%(filename)s, modified=%(modified)s")

for assignment in j['objects']:
    data_assignment = {
        'id': assignment['id'],
        'kind_name': assignment['kind_name'],
        'kind': assignment['kind'],
        'background_color': assignment['background_color'],
        'text': assignment['text'],
        'start': assignment['start'],
        'end': assignment['end'],
        'created': assignment['created'],
        'modified': assignment['modified'],
        }
    if dateutil.parser.parse(assignment['modified']) > datetime.datetime.now()-datetime.timedelta(hours=1):
        messages.append("%s\n%s - %s" % (data_assignment['kind_name'], dateutil.parser.parse(data_assignment['start']).strftime("%d.%m.%Y"), data_assignment['text']))
    # Insert new assignment
    cursor.execute(add_assignment, data_assignment)
    for assignment_file in assignment['files']:
        # Insert files information
        data_assignment_file = {
            'id': assignment_file['id'],
            'url': assignment_file['url'],
            'filename': assignment_file['filename'],
            'created': assignment_file['created'],
            'modified': assignment_file['modified'],
            'idassignment': assignment['id']
            }
        cursor.execute(add_assignment_file, data_assignment_file)
    # Make sure data is committed to the database
    cnx.commit()
cursor.close()

cal = Calendar()
cal.add('prodid', '-//Hello Class Yann//yann.ga-fl.net//')
cal.add('version', '2.0')

cursor = cnx.cursor()

query = ("SELECT idassignment, kind_name, kind, text, start, end, modified FROM assignment "
         "WHERE start > %s")

start_date = datetime.datetime.now()-datetime.timedelta(weeks=1)

cursor.execute(query, (start_date, ))

for (idassignment, kind_name, kind, text, start, end, modified) in cursor:
    event = Event()
    event.add('summary', "%s - %s" % (kind_name, text))
    event.add('dtstart', start)
    event.add('dtend', end)
    event.add('dtstamp', modified)
    event['uid'] = '%s/yann@ga-fl.net' % idassignment
    cal.add_component(event)

cursor.close()
cnx.close()

f = open(HELLO['ics'], 'wb')
f.write(cal.to_ical())
f.close()

if len(messages) > 0:
    for msg in messages:
        send_xmpp(msg)
