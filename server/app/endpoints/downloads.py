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

"""Handler for download stats - ported from https://github.com/apache/infrastructure-dlstats"""
import asfquart
from asfquart.auth import Requirements as R
from ..lib import middleware, config
from ..plugins import downloads

@asfquart.auth.require
@asfquart.APP.route(
    "/api/downloads",
)
async def process_downloads():
    form_data = await asfquart.utils.formdata()
    session = await asfquart.session.read()

    project = form_data.get("project", "httpd")    # Project/podling to fetch stats for
    duration = form_data.get("duration", 7)        # Timespan to search (in whole days)
    filters = form_data.get("filters", "empty_ua,no_query") # Various search filters
    add_metadata = form_data.get("meta", "no")
    stats, params = await downloads.generate_stats(project, duration, filters)
    if add_metadata == "yes":
        return {
            "query": params,
            "files": stats,
        }
    return stats




