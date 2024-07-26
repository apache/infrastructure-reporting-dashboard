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
"""Handler for userID availability/syntax checks"""
from ..lib import middleware, config
import os
import yaml
import psycopg
import re
import asyncio
import asfpy.clitools
import asfquart

# Dict of existing users from various canonical sources
existing_users = {
    "jira": [],  # Local Jira accounts
    "confluence": [],  # Local confluence accounts
    "ldap": [],  # LDAP accounts
    "reserved": [],  # Reserved IDs
}

# Valid user ID syntax, defined in config yaml
VALID_USERID_RE = re.compile(config.reporting.userid["valid_userid_syntax"])
SCAN_INTERVAL = 3600  # Scan for changes every one hour


async def scan_for_userids():
    """Scans for all userids in use by the various large systems"""
    while True:
        # LDAP users
        print("Fetching userids from LDAP")
        try:
            ldap_response = await asyncio.wait_for(
                asfpy.clitools.ldapsearch_cli_async(
                    ldap_base="ou=people,dc=apache,dc=org", ldap_scope="sub", ldap_query="uid=*", ldap_attrs=("uid",)
                ),
                120,
            )
            if ldap_response and len(ldap_response) > 1000:
                existing_users["ldap"] = [x["uid"][0] for x in ldap_response]
        except asyncio.exceptions.TimeoutError:
            print("LDAP timed out, retrying later")

        # Jira users, if set up for such (TODO: replace with crowd??)
        if "jirapsql" in config.reporting.userid:
            psql_dsn = psycopg.conninfo.make_conninfo(**config.reporting.userid["jirapsql"])
            print("Fetching local Jira users")
            try:
                temp_list = []
                async with await psycopg.AsyncConnection.connect(psql_dsn) as conn:
                    async with conn.cursor() as cur:
                        await cur.execute("SELECT lower_user_name from cwd_user WHERE directory_id != 10000")
                        async for row in cur:
                            if row[0] and isinstance(row[0], str):  # Ensure only non-empty strings here
                                temp_list.append(row[0])
                # Replace old list with new
                existing_users["jira"] = temp_list
            except psycopg.OperationalError as e:
                print(f"Operational error while querying Jira PSQL: {e}")
                print("Retrying later...")

        # Reserved IDs file
        reserved_ids_filename = config.reporting.userid.get("reserved_ids_file")
        if reserved_ids_filename and os.path.isfile(reserved_ids_filename):
            try:
                reserved_ids = yaml.safe_load(open(reserved_ids_filename))
                existing_users["reserved"] = reserved_ids
            except yaml.YAMLError as e:
                print(f"Could not load {reserved_ids_filename}, skipping: {e}")

        await asyncio.sleep(SCAN_INTERVAL)


@asfquart.APP.route(
    "/api/userid",
    methods=[
        "GET",  # Session get/delete
    ],
)
async def process_userid(form_data):
    form_data = await asfquart.utils.formdata()
    session = await asfquart.session.read()
    userid = form_data.get("id")
    # Check syntax validity
    is_valid = userid and VALID_USERID_RE.match(userid) is not None

    # Check if we already have a user like this
    for group, userlist in existing_users.items():
        if userid in userlist:
            return {
                "checked_id": userid,
                "is_valid": is_valid,
                "exists": True,
                "exists_where": group,
            }

    # No such user, just return validity
    return {
        "checked_id": userid,
        "is_valid": is_valid,
        "exists": False,
        "exists_where": None,
    }



# The userid scan is added as a generic loop. There is no web page for this feature, no need to the plugin registry
asfquart.APP.add_background_task(scan_for_userids)
