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

"""Handler for uptime stats"""
import asfquart
from ..lib import config
from ..plugins import uptime


@asfquart.APP.route(
    "/api/uptime",
)
async def process_uptime():
    uptime_stats = uptime.get_stats()
    series = config.reporting.uptime.get("series", {})
    uptime_collated = {}
    if series:
        u_y = 0
        u_m = 0
        u_w = 0
        u_c = 0
        for key, hosts in series.items():
            series_stats = []
            series_months = {}
            for host in hosts:
                if host in uptime_stats:
                    u_avg = uptime_stats[host]["uptime_average"]
                    u_monthly = list(uptime_stats[host]["uptime_monthly"].values())
                    u_month = u_monthly[-1] if u_monthly else 100.0
                    u_week = uptime_stats[host]["uptime_past_week"]
                    series_stats.append((u_avg, u_month, u_week, u_monthly))
                    for month, value in uptime_stats[host]["uptime_monthly"].items():
                        series_months[month] = series_months.get(month, [])
                        series_months[month].append(value)
                    # total stats across all hosts
                    u_c += 1
                    u_y += u_avg
                    u_m += u_month
                    u_w += u_week

            uptime_collated[key] = {
                "average": sum([x[0] for x in series_stats]) / float(len(series_stats)) if series_stats else 100.0,
                "past_month": sum([x[1] for x in series_stats]) / float(len(series_stats)) if series_stats else 100.0,
                "past_week": sum([x[2] for x in series_stats]) / float(len(series_stats)) if series_stats else 100.0,
                "monthly": {k: sum(vx for vx in v) / float(len(v)) if v else 100.0 for k, v in series_months.items()},
            }
    return {
        "uptime_total": {
            "year": float(u_y / u_c),
            "month": float(u_m / u_c),
            "week": float(u_w / u_c),
        },
        "uptime_collated": uptime_collated,
        "uptime_individual": uptime_stats,
    }


