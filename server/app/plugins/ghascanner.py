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
"""ASF Infrastructure Reporting Dashboard - GitHub Actions Statistics Tasks"""
import asyncio
import os
import json
import aiohttp
import dateutil.parser
import re
import asfpy.pubsub
import asfpy.sqlite
from ..lib import config
from .. import plugins

CREATE_RUNS_DB = """CREATE TABLE "runs" (
    "id"	INTEGER NOT NULL UNIQUE,
    "project"	TEXT NOT NULL,
    "repo"	TEXT NOT NULL,
    "workflow_id" INTEGER NOT NULL,
    "workflow_name"	TEXT,
    "seconds_used"	INTEGER NOT NULL,
    "run_start"	INTEGER NOT NULL,
    "run_finish"	INTEGER NOT NULL,
    "jobs"	TEXT,
    PRIMARY KEY("id" AUTOINCREMENT)
);"""
DEFAULT_PROJECTS_LIST = "https://whimsy.apache.org/public/public_ldap_projects.json"
projects = []

token = ""
db = None
if hasattr(config, "github"):  # If prod...
    token = config.github.read_token
    db_filepath = os.path.join(config.github.datadir, "ghactions.db")
    db = asfpy.sqlite.DB(db_filepath)
    if not db.table_exists("runs"):
        db.runc(CREATE_RUNS_DB)

headers = {
    "Authorization": f"Bearer {token}",
    "X-GitHub-Api-Version": "2022-11-28",
    "Accept": "application/vnd.github+json",
}


async def gather_stats(payload):
    url = payload["jobs_url"]
    repo = payload["repository"]
    m = re.match(r"^(?:incubator-)?([^-.]+)", repo)
    if m:
        project = m.group(1)
    else:
        project = "unknown"
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as hc:
            async with hc.get(url[:-5], headers=headers) as req:
                if req.status == 200:
                    workflow_data = await req.json()
                    workflow_name = workflow_data.get("name", "Unknown")
                    workflow_id = workflow_data.get("id", 0)
                else:
                    return
            async with hc.get(url, headers=headers) as req:
                if req.status == 200:
                    data = await req.json()
                    seconds_used = 0
                    earliest_runner = None
                    last_finish = None
                    jobs = []
                    for job in data["jobs"]:
                        if job["started_at"] and job["completed_at"]:
                            start_ts = dateutil.parser.isoparse(job["started_at"]).timestamp()
                            end_ts = dateutil.parser.isoparse(job["completed_at"]).timestamp()
                            job_name = job["workflow_name"]
                            job_name_unique = f"{repo}/{job_name}"
                            job_time = end_ts - start_ts
                            seconds_used += job_time
                            labels = job["labels"]
                            steps = []
                            if not earliest_runner or start_ts < earliest_runner:
                                earliest_runner = start_ts
                            if not last_finish or last_finish < end_ts:
                                last_finish = end_ts
                            for step in job["steps"]:
                                stepname = step["name"]
                                step_start_ts = dateutil.parser.isoparse(step["started_at"]).timestamp()
                                step_end_ts = dateutil.parser.isoparse(step["completed_at"]).timestamp()
                                step_time = step_end_ts - step_start_ts
                                steps.append((stepname, step_start_ts, step_time))
                            jobs.append(
                                {
                                    "name": job_name,
                                    "name_unique": job_name_unique,
                                    "job_duration": job_time,
                                    "steps": steps,
                                    "labels": labels,
                                    "runner_group": job.get("runner_group_name", "GitHub Actions") or "GitHub Actions",
                                }
                            )
                    if earliest_runner:
                        run_dict = {
                            "project": project,
                            "repo": repo,
                            "workflow_id": workflow_id,
                            "workflow_name": workflow_name,
                            "seconds_used": seconds_used,
                            "run_start": earliest_runner,
                            "run_finish": last_finish,
                            "jobs": json.dumps(jobs),
                        }
                        if seconds_used > 0:
                            db.insert("runs", run_dict)
                            # print(f"[{time.ctime()}] Parsed {url}")
                    await asyncio.sleep(0.2)
    except (json.JSONDecodeError, ValueError):
        pass


async def scan_builds():
    if not token:  # If not prod, nothing to do...
        return
    async for payload in asfpy.pubsub.listen("https://pubsub.apache.org:2070/github/actions"):
        if "stillalive" in payload:  # Ignore pongs
            continue
        try:
            await gather_stats(payload)
        except Exception as e:
            print(f"GitHub Actions poll failed: {e}")


async def list_projects():
    global projects
    """Grabs a list of all projects from whimsy"""
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as hc:
        try:
            async with hc.get(DEFAULT_PROJECTS_LIST) as req:
                if req.status == 200:
                    projects = list((await req.json())["projects"].keys())
        except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError) as e:
            print(f"GHA stats: Could not fetch list of projects from {DEFAULT_PROJECTS_LIST}: {e}")



plugins.root.register(
    scan_builds, list_projects, slug="ghactions", title="GitHub Actions Usage", icon="bi-envelope-exclamation-fill", private=True
)
