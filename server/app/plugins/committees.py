#!/usr/bin/env python3
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""ASF Infrastructure Reporting Dashboard - Mail Transport Statistics Tasks"""
import asyncio

#from ..lib import config
#from .. import plugins
import aiohttp
import json
import time
import yaml
import getpass
import svn.remote
import svn.local
import svn.exception
import re
import datetime
import sys

_committers: dict = {}

NAME_MAP = None
COMMITTEES = None

def load_data():
    creds = get_creds()
    client = svn.remote.RemoteClient('https://svn.apache.org/repos/private/committers/board', creds['usernm'], creds['passwd'])
    globals()['NAME_MAP'] = yaml.safe_load(open('tlp_aliases.yml', 'r'))
    try:
        globals()['COMMITTEES'] = re.split('\n\d\.', client.cat('committee-info.txt').decode('utf-8'))
    except svn.exception.SvnException as e:
        print("There was an error in the SVN call, please ensure your credentials are correct")
        sys.exit(0)

def get_creds():
    return { "usernm": input("Username: "), "passwd": getpass.getpass("Password: ") }

def get_committers():
    return _committers

class Committee:
    def __init__(self):
        self.chairs = []
        self.roster = {}
        self.established = None
        self.paragraph = None
        self.report_sched = []
        self.display_name = None

#def parse_officers(officers, committees):

def parse_rosters(data):
    projects = re.split('\n\* ', data)
    projects_processed = 0
    committees = {}
    roster_counts = {}
    for project in projects[1:-1]:
        proj = Committee()
        roster = {}
        key = None
        p = project.split('\n')
        for l in p:
            if l and re.match(r"^[A-z]", l):
                t = [ item.strip(')').strip() for item in l.split(' (') ]
                setattr(proj, "display_name", t[0].capitalize())
                setattr(proj, "established", t[1])
                if t[0].lower() in NAME_MAP:
                    key = NAME_MAP[t[0].lower()]
                else:
                    key = t[0].lower()
            if l and re.match(r"^\s{4}", l):
                u = re.split(r'\s{2,}', l.strip('^    '))
                if len(u) > 2: roster[u[0]] = {'name': f"{u[1]}", 'date': f"{u[2]}"}
            setattr(proj, "roster", roster)
            setattr(proj, "roster_count", len(roster))
            roster_counts[key] = len(roster.keys())
        committees[key] = vars(proj)
        projects_processed += 1
    return projects_processed, committees, roster_counts

def parse_committees_info():
    """builds committee-info.json"""
    projects_processed, committees, roster_counts = parse_rosters(COMMITTEES[3])
    chairs, boards, prescoms, execs, officers = re.split(r":\n\n", COMMITTEES[1])[1:]
    for chair in chairs.split('\n')[2:-3]:
        d = re.split("\s\s+", chair.lstrip())
        if d[0].lower() in NAME_MAP.keys():
            key = NAME_MAP[d[0].lower()]
        elif re.match(r"portable runtime", d[0].lower()):
            key = "apr"
        elif re.match(r"zookeeper", d[0].lower()):
            key = "zookeeper"
        else:
            key = d[0].lower()
        
        committees[key]["chair"] = {} 
        committees[key]["chair"][d[1].split()[0]] = {"name": d[1].split()[1].split("@")[0]}
    print(committees)

    data = { 
        "last_updated": str(datetime.datetime.now().isoformat()),
        "roster_counts": roster_counts,
        "committees": committees,
        "committee_count": projects_processed,
    }
    return data
#    _committers.clear()

async def scan_loop():
    while True:
        await mail_scan()
        await asyncio.sleep(300)

committees = {}
load_data()
data = parse_committees_info()
#print(json.dumps(data, indent=4))
#committees.update(parse_rosters(COMMITTEES[3]))
#plugins.root.register(scan_loop, slug="mailstats", title="Mail Transport Statistics", icon="bi-envelope-exclamation-fill", private=True)
