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

from ..lib import config
from .. import plugins
import aiohttp
import json
import time

_stats: dict = {}


def get_stats():
    return _stats


def trim_stats(stats):
    """Trims the stats, removing items that we do not currently use, shortening syntax for other items"""
    trimmed_stats = []
    for entry in stats:
        all_pending = [
            sum(x["pending"] for x in entry["recipients"].values()),
            sum(x["pending"] for x in entry["senders"].values())
            ]
        entry_trimmed = {
            "ts": entry["timestamp"],
            "pending": max(all_pending),
            "pending_by_recipient": {k: v["pending"] for k, v in entry["recipients"].items()},
            "pending_by_sender": {k: v["pending"] for k, v in entry["senders"].items()},
        }
        trimmed_stats.append(entry_trimmed)
    return trimmed_stats


def collate_stats(*stats):
    """Collates (sums up) stats from all hosts into one unified, global stat"""
    pending_by_recipient = {}
    pending_by_sender = {}
    pending_count = {}
    cutoff = int(time.time() - 86400)  # Only grab stats if from less than 24h ago
    for stat in stats:
        for entry in stat:
            ts = entry["ts"]
            if ts < cutoff:
                continue
            ts = str(ts)  # convert to string for dict to work
            if ts not in pending_by_recipient:
                pending_by_recipient[ts] = entry["pending_by_recipient"].copy()
            else:
                p_r = pending_by_recipient.get(ts)
                p_r.update({k: v+p_r.get(k, 0) for k, v in entry["pending_by_recipient"].items()})
            if ts not in pending_by_sender:
                pending_by_sender[ts] = entry["pending_by_sender"].copy()
            else:
                p_s = pending_by_sender[ts]
                p_s.update({k: v+p_s.get(k, 0) for k, v in entry["pending_by_sender"].items()})
            pending_count[ts] = pending_count.get(ts, 0) + entry["pending"]
    return [{
        "ts": int(k),
        "pending": pending_count[k],
        "pending_by_recipient": pending_by_recipient[k],
        "pending_by_sender": pending_by_sender[k]
    } for k in pending_count]

async def mail_scan():
    """Grabs mxout statistics from all hosts, collates it"""
    mxout_stats = {}
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as hc:
        for hostname in config.reporting.mailstats.get("hosts", []):
            try:
                async with hc.get(f"http://{hostname}:8083/qshape.json") as req:
                    if req.status == 200:
                        mxout_stats[hostname] = trim_stats(await req.json())
            except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError) as e:
                print(f"Could not fetch JSON from {hostname}: {e}")
    _stats.clear()
    _stats.update(mxout_stats)
    _stats["collated"] = collate_stats(*mxout_stats.values())



async def scan_loop():
    while True:
        await mail_scan()
        await asyncio.sleep(300)


plugins.root.register(scan_loop, slug="mailstats", title="Mail Transport Statistics", icon="bi-envelope-exclamation-fill", private=True)
