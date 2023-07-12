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
import quart
from .lib import config, log, middleware, assets
import os


HTDOCS_DIR = os.path.join(os.path.realpath(".."), "htdocs")  # File location of static assets
STATIC_DIR = os.path.join(os.path.realpath(".."), "static")  # Pre-compile static assets
SECRETS_FILE = "quart-secret.txt"

def main(debug=False):
    app = quart.Quart(__name__)
    # Cookie secrets
    if os.path.isfile(SECRETS_FILE):
        app_secret = open(SECRETS_FILE).read().strip()
    else:
        app_secret = secrets.token_hex()
        try:
            open(SECRETS_FILE, "w").write(app_secret)
        except PermissionError:
            print(f"Could not write cookie secret to {SECRETS_FILE}, not storing permanent secret.")
    app.secret_key = app_secret

    app.url_map.converters["filename"] = middleware.FilenameConverter  # Special converter for filename-style vars

    # Static files (or index.html if requesting a dir listing)
    @app.route("/<path:path>")
    @app.route("/")
    async def static_files(path="index.html"):
        if path.endswith("/"):
            path += "index.html"
        return await quart.send_from_directory(HTDOCS_DIR, path)

    @app.before_serving
    async def load_endpoints():
        """Load all API end points and tasks. This is run before Quart starts serving requests"""
        async with app.app_context():
            from . import endpoints
            from . import plugins

            # Regenerate documentation
            if debug:
                app.add_background_task(assets.loop, STATIC_DIR, HTDOCS_DIR)
            else:
                assets.generate_assets(STATIC_DIR, HTDOCS_DIR)

    @app.after_serving
    async def shutdown():
        """Ensure a clean shutdown of the platform by stopping background tasks"""
        log.log("Shutting down infrastructure reporting dashboard...")
        app.background_tasks.clear()  # Clear repo polling etc

    return app
