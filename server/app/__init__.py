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
"""ASF Infra Reporting Dashboard - Plugins"""

import secrets
import asfquart
import quart
from .lib import config, log, middleware, assets
import os


HTDOCS_DIR = os.path.join(os.path.realpath(".."), "htdocs")  # File location of static assets
STATIC_DIR = os.path.join(os.path.realpath(".."), "static")  # Pre-compile static assets
SECRETS_FILE = "quart-secret.txt"

def main(debug=False):
    asfquart.construct(__name__)
    
    # Static files (or index.html if requesting a dir listing)
    @asfquart.APP.route("/<path:path>")
    @asfquart.APP.route("/")
    async def static_files(path="index.html"):
        if path.endswith("/"):
            path += "index.html"
        return await quart.send_from_directory(HTDOCS_DIR, path)

    @asfquart.APP.before_serving
    async def load_endpoints():
        """Load all API end points and tasks. This is run before Quart starts serving requests"""
        async with asfquart.APP.app_context():
            from . import endpoints
            from . import plugins

            # Regenerate documentation
            if debug:
                asfquart.APP.add_background_task(assets.loop, STATIC_DIR, HTDOCS_DIR)
            else:
                assets.generate_assets(STATIC_DIR, HTDOCS_DIR)

    @asfquart.APP.after_serving
    async def shutdown():
        """Ensure a clean shutdown of the platform by stopping background tasks"""
        log.log("Shutting down infrastructure reporting dashboard...")
        asfquart.APP.background_tasks.clear()  # Clear repo polling etc

    return asfquart.APP
