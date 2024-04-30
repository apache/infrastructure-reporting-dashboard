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
"""ASF Infrastructure Reporting Dashboard"""
"""Handler for builds data"""
import quart
import asyncio
from ..lib import middleware, asfuid
from ..plugins import ghascanner
import time
import json

MAX_BUILD_SPAN = 720  # Max 720 hours worth of data per grab
DEFAULT_BUILD_SPAN = 168  # Default to one week of data
BUILDS_CACHE = []


async def fetch_n_days(hours=DEFAULT_BUILD_SPAN):
    """Fetches the last N (seven) days of builds into memory for faster processing"""
    while True:
        temp_cache = []
        start_from = time.time() - (hours * 3600)
        stmt = "SELECT * FROM `runs` WHERE (`run_start` >= ? OR `run_finish` >= ?)"
        values = [start_from, start_from]
        ghascanner.db.cursor.execute(stmt, values)
        while True:
            rowset = ghascanner.db.cursor.fetchmany()
            if not rowset:
                break
            for row in rowset:
                row_as_dict = dict(row)
                row_as_dict["jobs"] = json.loads(row_as_dict["jobs"])
                temp_cache.append(row_as_dict)
        # Wipe cache, set to new bits
        BUILDS_CACHE.clear()
        BUILDS_CACHE.extend(temp_cache)

        # Sleep it off for 15 minutes
        await asyncio.sleep(900)


@asfuid.session_required
async def show_gha_stats(form_data):
    """GitHub Actions stats"""
    hours = int(form_data.get("hours", DEFAULT_BUILD_SPAN))
    project = form_data.get("project", "")
    selfhosted = form_data.get("selfhosted", "false")  # if 'true', count self-hosted time
    session = asfuid.Credentials()
    if project:
        try:
            assert session.root or project in session.projects
        except AssertionError:
            return quart.Response(status=403,
                                  response=f"Access denied: You do not have access to view statistics for {project}")
    if hours > MAX_BUILD_SPAN:
        hours = MAX_BUILD_SPAN

    start_from = time.time() - (hours * 3600)
    rows = []
    for original_row in BUILDS_CACHE:
        row = original_row.copy()  # We MAY pop 'jobs', so copy the dict, don't modify the original
        if row["run_start"] < start_from or row["run_finish"] < start_from:
            continue
        if (project and row["project"] != project) or (
                not project and row["project"] not in session.projects) and not session.root:
            continue
        # Discount self-hosted unless asked for
        if selfhosted != "true":
            for job in row.get("jobs", []):
                if any("self-hosted" in label for label in job["labels"]):
                    row["seconds_used"] -= job["job_duration"]
        if not project:  # If not viewing a single project, dismiss the jobs data to cut down on traffic
            row.pop('jobs', '')
        rows.append(row)
    return {
        "all_projects": ghascanner.projects,
        "selected_project": project,
        "builds": rows,
    }


quart.current_app.add_url_rule(
    "/api/ghactions",
    methods=[
        "GET",  # Session get/delete
    ],
    view_func=middleware.glued(show_gha_stats),
)

quart.current_app.add_background_task(fetch_n_days)
