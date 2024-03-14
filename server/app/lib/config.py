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
"""ASF Infra Reporting Dashboard - Configuration"""
import yaml

CONFIG_FILE = "../reporting-dashboard.yaml"


def text_to_int(size):
    """Convert short-hand size notation to integer (kb,mb,gb)"""
    if isinstance(size, int):
        return size
    assert isinstance(size, str), "Byte size must be either integer or string value!"
    if size.endswith("kb"):
        return int(size[:-2]) * 1024
    elif size.endswith("mb"):
        return int(size[:-2]) * 1024 * 1024
    elif size.endswith("gb"):
        return int(size[:-2]) * 1024 * 1024 * 1024
    else:
        return int(size)


class ServerConfiguration:
    def __init__(self, yml: dict):
        assert yml, f"No server configuration directives could be found in {CONFIG_FILE}!"
        self.bind = yml["bind"]
        self.port = int(yml["port"])
        self.error_reporting = yml.get("error_reporting", "json")


class ReportingConfiguration:
    def __init__(self, yml: dict):
        assert yml, f"No reporting configuration directives could be found in {CONFIG_FILE}!"
        self.__dict__.update(yml)


class GitHubConfiguration:
    def __init__(self, yml: dict):
        assert yml, f"No github configuration directives could be found in {CONFIG_FILE}!"
        self.__dict__.update(yml)



cfg_yaml = yaml.safe_load(open(CONFIG_FILE, "r"))
server = ServerConfiguration(cfg_yaml.get("server", {}))
reporting = ReportingConfiguration(cfg_yaml.get("reporting", {}))
github = GitHubConfiguration(cfg_yaml.get("github", {}))
