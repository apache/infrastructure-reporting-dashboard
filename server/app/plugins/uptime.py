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
"""ASF Infrastructure Reporting Dashboard - Uptime Statistics Tasks"""
import asyncio

from ..lib import config
from .. import plugins
import aiohttp
import aiohttp.client_exceptions
import datetime
import dateutil.relativedelta
import functools

DEFAULT_TIMESPAN_MONTHS = 13  # Show last 12 months, plus current one

_stats: dict = {}


def get_stats():
    return _stats


async def uptime_scan(months=DEFAULT_TIMESPAN_MONTHS):
    """Performs a full uptime scan from NodePing"""
    nodeping_summary_url = config.reporting.uptime["summary_url"]
    now = datetime.datetime.now()
    cutoff_date = (now - dateutil.relativedelta.relativedelta(months=months)).strftime("%Y-%m")
    async with aiohttp.ClientSession() as hc:
        try:
            async with hc.get(nodeping_summary_url) as req:
                if req.status == 200:
                    hosts_json = await req.json()
                    tmpstats = {}
                    for host_entry in hosts_json.values():
                        uuid = host_entry["uuid"]
                        host_stats = {
                            "uuid": uuid,
                            "label": host_entry["label"],
                            "uptime_monthly": {},
                            "uptime_average": 100.0,
                            "uptime_past_week": 100.0,
                        }
                        # Monthly stats per host
                        host_url = config.reporting.uptime["host_url"].format(uuid=uuid)
                        async with hc.get(host_url, params={"format": "json"}) as hreq:
                            if req.status == 200:
                                host_data = await hreq.json()
                                uptimes = []
                                for month in host_data:
                                    mid = month["id"]
                                    if mid > cutoff_date and mid != "total":
                                        uptime_val = month["uptime"]
                                        if uptime_val != "-":
                                            host_stats["uptime_monthly"][mid] = uptime_val
                                            uptimes.append(uptime_val)
                                host_stats["uptime_average"] = (
                                    functools.reduce(lambda x, y: x + y, uptimes) / float(len(uptimes))
                                    if uptimes
                                    else 100.0
                                )
                        # Last week's stats per host
                        weekly_url = config.reporting.uptime["results_url"].format(uuid=uuid)
                        async with hc.get(weekly_url, params={"format": "json", "span": 168, "limit": 20000}) as wreq:
                            if wreq.status == 200:
                                weekly_json = await wreq.json()
                                checks_done = len(weekly_json)
                                checks_failed = len([x for x in weekly_json if x["su"] is False])
                                weekly_uptime = 100.0
                                if checks_done:
                                    weekly_uptime -= float((checks_failed / checks_done) * 100)
                                host_stats["uptime_past_week"] = weekly_uptime
                        tmpstats[uuid] = host_stats
                        _stats.update(tmpstats)
                    _stats.clear()
                    _stats.update(tmpstats)
        except aiohttp.client_exceptions.ClientError as e:  # Request went awry??
            print(f"Connection to {nodeping_summary_url} failed: {e}")
            print("Retrying later..")

async def scan_loop():
    while True:
        await uptime_scan()
        await asyncio.sleep(3600)


plugins.root.register(scan_loop, slug="uptime", title="Uptime Statistics", icon="bi-router-fill")
