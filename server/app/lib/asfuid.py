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
"""ASF User Information via LDAP or OAuth"""

from . import config
import re
import quart
import time
import functools

UID_RE = re.compile(r"^(?:uid=)?([^,]+)")
SESSION_TIMEOUT = 86400  # Time out user sessions after 1 day.


class Credentials:
    """Get credentials of user (only via cookie for now)"""

    def __init__(self):
        if quart.session and "uid" in quart.session:
            # Assert that the oauth session is not too old
            assert quart.session.get("timestamp", 0) > int(
                time.time() - SESSION_TIMEOUT
            ), "Session timeout, please authenticate again"
            self.uid = quart.session["uid"]
            self.name = quart.session["fullname"]
            self.projects = quart.session["projects"]
            self.pmcs = quart.session["pmcs"]
            self.root = quart.session["isRoot"]
        else:
            raise AssertionError("User not logged in via Web UI")


def session_required(func):
    """Decorator for calls that require the user to be authenticated against OAuth.
    Calls will be checked for an active, valid session, and if found, it will
    add the session to the list of arguments for the originator. Otherwise, it
    will return the standard no-auth JSON reply.
    Thus, calls that require a session can use:
    @asfuid.session_required
    async def foo(form_data, session):
      ...
    """

    @functools.wraps(func)
    async def session_wrapper(form_data):
        try:
            session = Credentials()  # Must be logged in via ASF OAuth
        except AssertionError as e:
            return {"success": False, "message": str(e)}, 403
        return await func(form_data)

    return session_wrapper
