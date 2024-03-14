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
from ..lib import middleware, asfuid
from ..plugins import ghascanner
import time

MAX_BUILD_SPAN = 720  # Max 720 hours worth of data per grab
DEFAULT_BUILD_SPAN = 168  # Default to one week of data
@asfuid.session_required
async def show_gha_stats(form_data):
    """GitHub Actions stats"""
    hours = int(form_data.get("hours", DEFAULT_BUILD_SPAN))
    project = form_data.get("project", "")
    try:
        session = asfuid.Credentials()
        assert session.root or project in session.projects
    except AssertionError:
        return quart.Response(status=403, response="Access denied")
    if hours > MAX_BUILD_SPAN:
        hours = MAX_BUILD_SPAN
    start_from = time.time() - (hours * 3600)
    stmt = "SELECT * FROM `runs` WHERE (`run_start` >= ? OR `run_finish` >= ?)"
    values = [start_from, start_from]
    if project:
        stmt += " AND `project` = ?"
        values.append(project)
    ghascanner.db.cursor.execute(stmt, values)
    rows = []
    while True:
        rowset = ghascanner.db.cursor.fetchmany()
        if not rowset:
            break
        rows.extend([dict(row) for row in rowset])
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
