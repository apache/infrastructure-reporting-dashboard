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

"""Documentation rendering library"""

import os
import ezt
import typing
import io
import shutil
import asyncio


def ezt_to_html(
    template_file: typing.Union[os.PathLike, str],
    data: typing.Any,
    target_filename: typing.Optional[typing.Union[os.PathLike, str]] = None,
):
    """Simple wrapper for rendering an EZT template to a target file (or string, if no target file is specified)"""
    template = ezt.Template(template_file)
    if target_filename:  # filesystem target
        output_fd = open(target_filename, "w")
        template.generate(output_fd, data)
    else:  # string buffer target
        output_fd = io.StringIO()
        template.generate(output_fd, data)
        return output_fd.getvalue()


def generate_assets(static_dir, htdocs_dir):
    """Generates the HTML scaffolding from EZT and compiles JS"""
    from .. import plugins

    if not os.path.isdir(htdocs_dir):
        print(f"Creating {htdocs_dir}")
        os.makedirs(htdocs_dir, exist_ok=True)

    # Generate front page HTML
    origin_filepath = os.path.join(static_dir, "templates", "index.ezt")
    target_filepath = os.path.join(htdocs_dir, "index.html")
    # print(f"Writing front page file {target_filepath}")
    datadict = {
        "plugins": plugins.root.plugins,
    }
    ezt_to_html(template_file=origin_filepath, data=datadict, target_filename=target_filepath)

    # Compile JS assets
    js_assets = ""
    plugin_js_dir = os.path.join(static_dir, "plugins")
    for filename in sorted(os.listdir(plugin_js_dir)):
        if filename.endswith(".js"):
            filepath = os.path.join(plugin_js_dir, filename)
            filedata = open(filepath).read()
            js_assets += f"// {filename}:\n\n{filedata}\n"

    # Copy all assets to htdocs
    assets_origin = os.path.join(static_dir, "assets")
    assets_target = os.path.join(htdocs_dir, "_assets")
    shutil.copytree(assets_origin, assets_target, dirs_exist_ok=True)
    with open(os.path.join(assets_target, "plugins.js"), "w") as f:
        f.write(js_assets)


async def loop(static_dir, htdocs_dir):
    while True:
        generate_assets(static_dir, htdocs_dir)
        await asyncio.sleep(2)
