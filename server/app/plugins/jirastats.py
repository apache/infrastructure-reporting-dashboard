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
"""ASF Infrastructure Reporting Dashboard - Jira Statistics Tasks"""
import asyncio

from ..lib import config
from .. import plugins
import aiohttp
import time
import re
import asfpy.pubsub
import datetime

DEFAULT_SCAN_INTERVAL = 900  # Always run a scan every 15 minutes
DEFAULT_DISCOUNT_DELTA = 600  # Calculate weekend discounts in 10 min increments
DEFAULT_RETENTION = 120  # Only return tickets that are still open, or were updated in the last 120 days
DEFAULT_SCAN_DAYS = 90  # Scan last 90 days in a full scan. This should be, at max, 500, usually ~375 issues.
DEFAULT_SLA = {  # Default (fallback) SLA
    "respond": 48,  # 48h to respond
    "resolve": 120,  # 120h to resolve
}

_cache: dict = {}
_stats: dict = {}
_scan_schedule: list = []


class JiraTicket:
    def __init__(self, data):
        self._data = data
        self.assignee = data["fields"]["assignee"]["name"] if data["fields"]["assignee"] else None
        self.status = data["fields"]["status"]["name"]
        self.closed = self.status == "Closed"
        self.reopened = False
        self.key = data["key"]
        self.project = self.key.split("-")[0]
        self.url = config.reporting.jira["ticket_url"].format(**data)
        self.summary = data["fields"]["summary"]
        self.created_at = self.get_time(data["fields"]["created"])
        self.updated_at = self.get_time(data["fields"]["updated"])
        self.priority = data["fields"]["priority"]["name"]
        self.author = data["fields"]["creator"] and data["fields"]["creator"]["name"] or "(nobody)"  # May not exist!
        self.issuetype = data["fields"]["issuetype"]["name"]
        self.sla = config.reporting.jira["slas"].get(self.priority, DEFAULT_SLA)

        # SLA stuff
        self.first_response = 0
        self.response_time = 0
        self.resolve_time = 0
        self.closed_at = 0
        self.sla_met_respond = None  # True/False if responded to at all
        self.sla_met_resolve = None
        self.sla_time_counted = 0
        self.statuses = []
        self.changelog = []
        self.paused = self.issuetype in config.reporting.jira.get("no_slas", [])

        # Scan all changelog entries
        for changelog_entry in data.get("changelog", {}).get("histories", []):
            changelog_author = (
                "author" in changelog_entry and changelog_entry["author"]["name"] or "nobody"
            )  # May have been deleted
            changelog_epoch = self.get_time(changelog_entry["created"])
            self.changelog.append((changelog_author, changelog_epoch))
            for item in changelog_entry.get("items", []):
                field = item["field"]
                if field == "assignee":  # Ticket (re)assigned
                    #  self.set_fr(changelog_epoch)
                    pass  # Should not count as a response
                elif field == "resolution":  # Ticket resolved
                    self.set_fr(changelog_epoch)
                    self.closed_at = changelog_epoch
                elif field == "status":  # Status change
                    if (
                        self.closed_at
                    ):  # if we already logged a close, but there are new status changes, it's been reopened
                        self.reopened = True
                    if not self.statuses:  # First status change, log initial status from this
                        self.statuses.append((item["fromString"].lower(), self.created_at))
                    self.statuses.append((item["toString"].lower(), changelog_epoch))  # Note change to status at time

        # Scan all comments, looking for a response earlier than changelog entries
        for comment in data["fields"].get("comment", {}).get("comments", []):
            comment_author = comment["author"]["name"]
            comment_epoch = self.get_time(comment["created"])
            self.changelog.append((comment_author, comment_epoch))
            if comment_author != self.author:  # Comment by someone other than the ticket author
                self.set_fr(comment_epoch)
                break  # Only need to find the first (earliest) occurrence

        # Calculate time spent in WFI
        times_in_wfi = []

        if not self.statuses:  # No status changes, WFI is assumed to be entire duration
            if self.closed:
                times_in_wfi.append((self.created_at, self.closed_at))  # Ticket is closed, use closed_at
            else:
                times_in_wfi.append((self.created_at, int(time.time())))  # Ticket is open, use $now
        else:
            sla_statuses_lower = [x.lower() for x in config.reporting.jira.get("sla_apply_statuses")]
            previous_ts = 0
            previous_is_sla = False
            for status in self.statuses:
                if previous_ts and previous_is_sla:
                    times_in_wfi.append((previous_ts, status[1]))  # From previous TS to this one
                previous_ts = status[1]
                previous_is_sla = status[0] in sla_statuses_lower

            # Not in WFI mode? pause if not paused
            if not self.closed and self.statuses[-1][0] not in sla_statuses_lower:
                self.paused = True

        for spans in times_in_wfi:
            self.sla_time_counted += self.calc_sla_duration(*spans)
        if self.first_response:
            self.response_time = self.calc_sla_duration(self.created_at, self.first_response)
        if self.closed_at:
            self.resolve_time = self.calc_sla_duration(self.created_at, self.closed_at)

        # If closed or responded to, check if the duration met the SLA guides
        # If not closed or responded to, check if time spent in WFI surpasses SLA guides
        if self.closed:
            self.sla_met_resolve = self.resolve_time <= (self.sla["resolve"] * 3600)
        elif self.sla_time_counted > (self.sla["resolve"] * 3600):
            self.sla_met_resolve = False
        if self.first_response:
            self.sla_met_respond = self.response_time <= (self.sla["respond"] * 3600)
        elif self.sla_time_counted > (self.sla["respond"] * 3600):
            self.sla_met_respond = False

    @property
    def as_dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

    @staticmethod
    def calc_sla_duration(from_epoch, to_epoch):
        """Calculates the active SLA time (in seconds) between two durations, discounting weekends"""
        should_discount = config.reporting.jira.get("sla_discount_weekend")
        seconds_spent = to_epoch - from_epoch  # Add seconds between the two transitions
        if should_discount:
            dt_start = datetime.datetime.fromtimestamp(from_epoch)
            dt_end = datetime.datetime.fromtimestamp(to_epoch)
            total_discount = 0
            dt_temp = dt_start
            while dt_temp < dt_end and total_discount < seconds_spent:
                dt_temp += datetime.timedelta(seconds=DEFAULT_DISCOUNT_DELTA)
                if (
                    dt_temp.weekday() in [5, 6]  # Sat, Sun
                    or (dt_temp.weekday() == 4 and dt_temp.hour > 20)  # Fri after 8pm UTC
                    or (dt_temp.weekday() == 0 and dt_temp.hour < 8)  # Mon before 8am UTC
                ):
                    total_discount += DEFAULT_DISCOUNT_DELTA
            seconds_spent -= min(seconds_spent, total_discount)
        return seconds_spent

    def set_fr(self, epoch):
        if self.first_response:
            self.first_response = min(self.first_response, epoch)
        else:
            self.first_response = epoch

    @staticmethod
    def get_time(string):
        """Converts a jira ISO timestamp to unix epoch"""
        return int(time.mktime(time.strptime(re.sub(r"\..*", "", str(string)), "%Y-%m-%dT%H:%M:%S")))


def process_cache(issues):
    if issues:
        _stats.clear()  # Clear stats cache if we have data, so as to remove deleted tickets
    for issue in issues:
        key = issue["key"]
        _cache[key] = issue
        ticket = JiraTicket(issue)
        _stats[key] = ticket
    return len(issues)


def get_issues():
    deadline = time.time() - (DEFAULT_RETENTION * 86400)
    return [x.as_dict for x in _stats.values() if x.closed is False or x.updated_at >= deadline]


async def jira_scan_full(days=DEFAULT_SCAN_DAYS):
    """Performs a full scan of Jira activity in the past [days] days"""
    jira_scan_url = config.reporting.jira["api_url"] + "search"
    jira_project = config.reporting.jira["project"]
    jira_token = config.reporting.jira["token"]

    params = {
        "fields": "key,created,summary,status,assignee,priority,comment,creator,updated,issuetype",
        "expand": "changelog",
        "maxResults": "1000",
        "jql": f"""project={jira_project} and (updated>=-{days}d or status!=closed)""",
    }

    async with aiohttp.ClientSession(headers={"Authorization": f"Bearer: {jira_token}"}) as hc:
        async with hc.get(jira_scan_url, params=params) as req:
            if req.status == 200:
                jira_json = await req.json()
                processed = process_cache(jira_json.get("issues", []))
                return processed


async def scan_loop():
    while True:
        if _scan_schedule:  # Things are scheduled for a scan
            now = time.time()
            print("Starting Jira scan")
            processed = await jira_scan_full()
            print(f"Processed {processed} tickets in {int(time.time()-now)} seconds")
            _scan_schedule.pop()  # pop an item, freeing up space to allocate a new scan
        await asyncio.sleep(60)  # Always wait 60 secs between scan checks


async def poll_loop():
    """Schedules a scan every DEFAULT_SCAN_INTERVAL seconds, plus when a pubsub event happens.
    No more than two events can be scheduled at any given time (iow if a scan is running, and
    we get a pubsub event, we can add one more scan to be done in the future."""
    loop = asyncio.get_running_loop()

    def maybe_timeout(duration):
        "Use asyncio.timeout() for Py3.11; stub out for lower versions."
        if hasattr(asyncio, 'timeout'):
            return asyncio.timeout(duration)
        import contextlib
        class StubTimeout:
            def reschedule(self, t):
                pass
        @contextlib.asynccontextmanager
        async def gen_stub():
            yield StubTimeout()
        return gen_stub()

    pubsub_url = config.reporting.jira.get("pubsub_url")
    while True:
        _scan_schedule.append(time.time())  # Schedule a scan
        if pubsub_url:
            try:
                async with maybe_timeout(60) as to:
                    async for payload in asfpy.pubsub.listen(pubsub_url):
                        to.reschedule(loop.time() + 60)  # Got a response, pubsub works, reschedule timeout
                        if "stillalive" not in payload:  # Not a ping
                            if len(_scan_schedule) < 2:
                                _scan_schedule.append(time.time())  # add scan to schedule
            except TimeoutError:
                print("PubSub connection timed out, re-establishing")
                continue
        else:
            await asyncio.sleep(DEFAULT_SCAN_INTERVAL)


plugins.root.register(poll_loop, scan_loop, slug="jira", title="Jira Tickets", icon="bi-bug-fill", private=True)
