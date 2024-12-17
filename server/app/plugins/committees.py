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
"""ASF Infrastructure Reporting Dashboard - Committee Info"""
import asyncio

# from ..lib import config
# from .. import plugins
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

NAME_MAP = None
COMMITTEES = None
COMMITTEE_INFO_JSON = None

# JSON get committee_info.json
def get_committee_info():
    return globals()["COMMITTEE_INFO_JSON"]


def get_different_info():
    return True


# Needs to be async
def load_data():
    creds = get_creds()
    client = svn.remote.RemoteClient(
        "https://svn.apache.org/repos/private/committers/board",
        creds["usernm"],
        creds["passwd"],
    )
    globals()["NAME_MAP"] = yaml.safe_load(open("aliases.yml", "r"))
    try:
        globals()["COMMITTEES"] = re.split(
            "\n\d\.", client.cat("committee-info.txt").decode("utf-8")
        )
    except svn.exception.SvnException as e:
        sys.stderr.write(
            "There was an error in the SVN call, please ensure your credentials are correct"
        )
        sys.exit(0)


class Committee:
    def __init__(self):
        self.chairs = []
        self.roster = {}
        self.established = None
        self.paragraph = None
        self.report_sched = []
        self.display_name = None


# Needs to go away and use system creds instead
def get_creds():
    sys.stderr.write("Username: ")
    return {"usernm": input(), "passwd": getpass.getpass("Password: ")}


def set_key(project):
    if project.lower() in globals()["NAME_MAP"].keys():
        key = globals()["NAME_MAP"][project.lower()]
    else:
        key = project.lower()
    return key


def parse_rosters(data):
    projects = re.split("\n\* ", data)
    projects_processed = 0
    boards_processed = 0
    committees = {}
    pmcs = {}
    roster_counts = {}
    for project in projects[1:]:
        proj = Committee()
        roster = {}
        key = None
        ctype = None
        p = project.split("\n")
        for l in p:
            if l and re.match(r"^[A-z]", l):
                t = [item.strip(")").strip() for item in l.split(" (")]
                ctype = t[-1].lstrip("(")
                setattr(proj, "display_name", t[0].capitalize())
                setattr(proj, "established", t[1])
                key = set_key(t[0])
            if l and re.match(r"^\s{4}", l):
                u = re.split(r"\s{2,}", l.strip("^    "))
                if len(u) > 2:
                    roster[u[0]] = {"name": f"{u[1]}", "date": f"{u[2]}"}
            setattr(proj, "roster", roster)
            setattr(proj, "roster_count", len(roster))
        if ctype == "President's Committee" or ctype == "Board Committee":
            committees[key] = vars(proj)
            boards_processed += 1
        else:
            roster_counts[key] = len(roster.keys())
            pmcs[key] = vars(proj)
            projects_processed += 1
    return projects_processed, pmcs, roster_counts, committees, boards_processed


def parse_committees_info():
    """builds committee-info.json"""
    (
        projects_processed,
        pmcs,
        roster_counts,
        committees,
        boards_processed,
    ) = parse_rosters(COMMITTEES[3])
    chairs, boards, prescoms, execs, officers = re.split(r":\n\n", COMMITTEES[1])[1:]
    pmcs.update(committees)
    # Parse Chairs
    for chair in chairs.split("\n")[2:-3]:
        c = re.split("\s\s+", chair.lstrip())
        key = set_key(c[0])

        # weird edge cases here:
        if re.match(r"portable runtime", c[0].lower()):
            key = "apr"

        if key in pmcs.keys():
            pmcs[key]["chair"] = {}
            pmcs[key]["chair"][c[1].split()[0]] = {
                "name": c[1].split()[1].split("@")[0]
            }
        else:
            continue
    officers_temp = {}

    # Parse Boards
    for board in boards.split("\n")[2:-3]:
        b = re.split("\s\s+", board.lstrip())
        temp_roster = b[1].strip(">").split(" <")
        temp_roster.append(temp_roster[1].split("@")[0])
        committees[set_key(b[0])] = {
            "display_name": b[0],
            "paragraph": "Committee",
            "roster": {f"{temp_roster[2]}": {"name": temp_roster[0]}},
        }

    # parse Presidential Committees
    for prescom in prescoms.split("\n")[2:-3]:
        p = re.split("\s\s+", prescom.lstrip())

    # parse Executive Officers
    for executive in execs.split("\n")[2:-3]:
        x = re.split("\s\s+", executive.lstrip())
        temp_roster = x[1].strip(">").split(" <")
        temp_roster.append(temp_roster[1].split("@")[0])
        officers_temp[set_key(x[0])] = {
            "display_name": x[0],
            "paragraph": "Executive Officer",
            "roster": {f"{temp_roster[2]}": {"name": temp_roster[0]}},
        }

    # parse Additional Officers
    for officer in officers.split("\n")[2:-9]:
        o = re.split("\s\s+", officer.lstrip())
        temp_roster = o[1].strip(">").split(" <")
        temp_roster.append(temp_roster[1].split("@")[0])
        officers_temp[set_key(o[0])] = {
            "display_name": o[0],
            "paragraph": "Additional Officers",
            "roster": {f"{temp_roster[2]}": {"name": temp_roster[0]}},
        }

    data = {
        "last_updated": str(datetime.datetime.now().isoformat()),
        "roster_counts": roster_counts,
        "committees": pmcs,
        "committee_count": projects_processed + boards_processed,
        "pmc_count": projects_processed,
        "officers": officers_temp,
    }

    globals()["COMMITTEE_INFO"] = data


async def scan_loop():
    while True:
        await parse_committees_info()
        await asyncio.sleep(300)


load_data()
parse_committees_info()
print(globals()["COMMITTEE_INFO"])

# plugins.root.register(scan_loop, slug="json", title="Mail Transport Statistics", icon="bi-envelope-exclamation-fill", private=True)
