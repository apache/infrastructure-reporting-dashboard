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
"""Handler for session operations (view current session, log out)"""
import quart
import time
from ..lib import middleware, asfuid, config


async def process(form_data):
    action = form_data.get("action")
    if action == "logout":  # Clear the session
        quart.session.clear()
        return quart.Response(status=302, response="Signed out, bye!", headers={"Location": "/"})
    try:
        session = asfuid.Credentials()
        quart.session["timestamp"] = int(time.time())  # Update timestamp so we don't time out for another 24h.
        return {
            "uid": session.uid,
            "name": session.name,
            "projects": session.projects,
            "pmcs": session.pmcs,
            "root": session.root,
        }
    except AssertionError:
        return quart.Response(status=403, response="No active session or session expired. Please authenticate.")


quart.current_app.add_url_rule(
    "/api/session",
    methods=[
        "GET",  # Session get/delete
    ],
    view_func=middleware.glued(process),
)
