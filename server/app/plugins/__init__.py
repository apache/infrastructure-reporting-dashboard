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
"""ASF Infrastructure Reporting Dashboard - Plugin handler"""

import quart
import typing
import collections

pluginEntry = collections.namedtuple(
    "plugin",
    (
        "slug",
        "title",
        "icon",
        "loops",
    ),
)


class PluginList:
    def __init__(self):
        self.plugins = []

    def register(self, slug: str, title: str, icon: str, *loops: typing.Callable):
        """Registers a reporting plugin, adds to sidebar in UI and inits any necessary loops"""
        self.plugins.append(pluginEntry(slug, title, icon, loops))
        if loops:
            for loop in loops:
                quart.current_app.add_background_task(loop)


root: PluginList = PluginList()

from . import jirastats
