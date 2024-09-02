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
"""Handler for site source page"""
import asfquart
from ..lib import middleware, config
from .. import plugins

site_source_url = middleware.CachedJson("https://www.apache.org/site-sources.json", expiry=1800)


@asfquart.APP.route(
    "/api/sitesource",
)
async def process_sitesource():
    form_data = await asfquart.utils.formdata()
    session = await asfquart.session.read()
    return await site_source_url.json



plugins.root.register(slug="sitesource", title="Site Source Checker", icon="bi-share-fill")
