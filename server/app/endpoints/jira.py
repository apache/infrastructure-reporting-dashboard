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
import asfquart
import asfquart.auth
from asfquart.auth import Requirements as R
import asfquart.session
from ..lib import middleware, config
from ..plugins import jirastats


@asfquart.auth.require({R.root})
@asfquart.APP.route( 
    "/api/jira",
)
async def process_jira():
    form_data = await asfquart.utils.formdata()
    session = await asfquart.session.read()
    action = form_data.get("action")
    if action == "stats":  # Basic stats
        return jirastats.get_issues()


