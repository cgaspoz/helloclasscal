# -*- coding: UTF-8 -*-
# material_web.py
#
# Copyright (C) 2014 HES-SO//HEG Arc
#
# Author(s): Cédric Gaspoz <cedric.gaspoz@he-arc.ch>
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
from yaml import load
from xmpp_bot import send_xmpp
import dateutil
from icalendar import Calendar, Event
import os
import pickle


CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))

try:
    hellocron = pickle.load(open(os.path.join(CURRENT_PATH, 'config', 'helloclass.pickle'), 'rb'))
    LAST_UPDATE = hellocron['last_update']
except:
    LAST_UPDATE = datetime.datetime.now()-datetime.timedelta(days=2)


with open(os.path.join(CURRENT_PATH, 'config', 'helloclass.yaml'), 'r') as stream:
    config = load(stream)

HELLO = config['helloclass']
DB = config['mysql']

KIND = {4091: 'blue', 4093: 'yellow', 4097: 'red'}


def generate_web():
    cnx = mysql.connector.connect(user=DB['user'], password=DB['password'], host=DB['host'], database=DB['database'])

    html = """<!DOCTYPE html>
<html lang="de">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1.0"/>
  <meta name="mobile-web-app-capable" content="yes">
  <title>Hello Class</title>
  <!-- CSS  -->
  <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
  <link href="materialize/css/materialize.min.css" type="text/css" rel="stylesheet" media="screen,projection"/>
  <link href="css/style.css" type="text/css" rel="stylesheet" media="screen,projection"/>
</head>
<body>
<div class="navbar-fixed">
  <nav class="green lighten-1" role="navigation">
    <div class="nav-wrapper container"><a id="logo-container" href="#" class="brand-logo">Hello Class Yann</a>
      <ul class="right hide-on-med-and-down">
        <li><a href="#">Past homeworks</a></li>
      </ul>
      <ul id="nav-mobile" class="side-nav">
        <li><a href="#">Past homeworks</a></li>
      </ul>
      <a href="#" data-activates="nav-mobile" class="button-collapse"><i class="material-icons">menu</i></a>
    </div>
  </nav>
</div>
  <div class="container">
    <div class="section">"""

    cursor = cnx.cursor()

    query = ("SELECT idassignment, kind_name, kind, text, start, end, modified FROM assignment "
             "WHERE start > %s ORDER BY start")

    start_date = datetime.datetime.now()-datetime.timedelta(weeks=1)

    cursor.execute(query, (start_date, ))

    start_cal = start_date - datetime.timedelta(days=1)
    start_month = ""
    open_div = False

    for (idassignment, kind_name, kind, text, start, end, modified) in cursor:
        if start.date().strftime('%B') != start_month:
            if open_div:
                html += "</div></div>"
                open_div = False
            html += """<h2>%s</h2>""" % start.strftime('%B')
            start_month = start.strftime('%B')
        if start.date() != start_cal.date():
            if open_div:
                html += "</div></div>"
                open_div = False
            html += """<!-- New day -->
      <div class="divider"></div>
      <div class="row">
        <div class="col s2 m2">
            <h5 class="">%s</h5>
            <p class="light">%s.</p>
        </div>
        <div class="col s10 m10">""" % (start.strftime('%d'), start.strftime('%a'))
        open_div = True
        html += """
           <div class="card-panel %s lighten-2">%s</div>""" % (KIND[kind], text)

        start_cal = start

    cursor.close()
    cnx.close()

    html += """    </div></div>
  </div>
  <footer class="page-footer orange">
    <div class="footer-copyright">
      <div class="container">
      Last update: 2015-11-11 23:00
      </div>
    </div>
  </footer>
  <!--  Scripts-->
  <script src="https://code.jquery.com/jquery-2.1.1.min.js"></script>
  <script src="materialize/js/materialize.js"></script>
  <script src="js/init.js"></script>
  </body>
</html>"""

    f = open(HELLO['html'], 'w')
    f.write(html)
    f.close()

generate_web()