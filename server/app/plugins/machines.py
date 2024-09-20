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

""" Machine fingerprint scanner and checker app thingy
Spits out:
    - index.html: a human readable page with all fingerprints
    - machines.json: a json file to keep score of previous fingerprints
    - fp.json: a json file for nodeping to work with
 """
import asyncio
from ..lib import config
from .. import plugins
import aiohttp
import aiohttp.client_exceptions
import functools
import os
import json
import requests
import subprocess
import base64
import hashlib
import time
import datetime
import fnmatch
import sys

KEYSCAN = "/usr/bin/ssh-keyscan"
IPDATA = requests.get("https://svn.apache.org/repos/infra/infrastructure/trunk/dns/zones/ipdata.json").json()
IGNORE_HOSTS = (
    "bb-win10",
    "ci.hive",
    "ci2.ignite",
    "cloudstack-gateway",
    "corpora.tika",
    "demo.*",
    "donate",
    "jenkins-*",
    "metrics.beam",
    "mtcga*.ignite",
    "reviews.ignite",
    "vpn.plc4x",
    "weex",
    "pnap-us-west-generic-nat",
    "bb-win-azr-1",
    "bb-win-azr-2",
    "www",
    "www.play*",
)
JSON_FILE = "/tmp/machines.json"
FPDATA = {}

def get_fps():
    if 'HTML' not in globals()['FPDATA'] and os.path.exists(JSON_FILE):
        print(f"Found fingerprint cache {JSON_FILE}")
        globals()['FPDATA'] = json.load(open(JSON_FILE, "r"))
    return globals()['FPDATA']

class Host:
    def __init__(self, name, ip):
        self.ips = [ip]
        self.name = name

def l2fp(line):
    """Public key to fingerprints"""
    key = base64.b64decode(line.strip().split()[-1])
    fp_plain = hashlib.md5(key).hexdigest()
    fp_md5 = ":".join(a + b for a, b in zip(fp_plain[::2], fp_plain[1::2]))
    fp_sha256 = base64.b64encode(hashlib.sha256(key).digest()).decode("ascii").rstrip("=")
    return fp_md5, fp_sha256


def fpscan():
    old_hosts = {}
    hosts = {}
    for ip, name in IPDATA.items():
        if name in hosts:
            hosts[name].ips.append(ip)
        else:
            hosts[name] = Host(name, ip)

    reachable = 0
    unreachable = []
    all_notes = []

    if not "quick" in sys.argv:
        for name, host_data in sorted(hosts.items()):
            if any(fnmatch.fnmatch(name, pattern) for pattern in IGNORE_HOSTS):
                continue
            ipv4 = [x for x in host_data.ips if "." in x][0]

            try:
                keydata_rsa = subprocess.check_output(
                    (KEYSCAN, "-T", "1", "-4", "-t", "rsa", "%s.apache.org" % name), stderr=subprocess.PIPE
                )
                keydata_ecdsa = subprocess.check_output(
                    (KEYSCAN, "-T", "1", "-4", "-t", "ecdsa", "%s.apache.org" % name), stderr=subprocess.PIPE
                )
                if not keydata_rsa:
                    unreachable.append(name)
                    continue
                gunk, rsa_sha256 = l2fp(keydata_rsa)
                gunk, ecdsa_sha256 = l2fp(keydata_ecdsa)
                print(name, ipv4, rsa_sha256, ecdsa_sha256)
                reachable += 1
                now = int(time.time())
                now_str = datetime.datetime.fromtimestamp(now).strftime("%c")

                if name not in old_hosts:
                    old_hosts[name] = {
                        "ipv4": ipv4,
                        "fingerprint_ecdsa": ecdsa_sha256,
                        "fingerprint_rsa": rsa_sha256,
                        "first_seen": now,
                        "last_seen": now,
                        "okay": True,
                        "notes": [],
                    }
                else:
                    oho = old_hosts[name]
                    if oho["fingerprint_rsa"] != rsa_sha256:
                        note = f"Fingerprint of {name} changed at {now_str}, from {oho['fingerprint_rsa']} to {rsa_sha256}!"
                        oho["okay"] = False
                        oho["notes"].append(note)
                        all_notes.append(note)
                        #print(note)

            except KeyboardInterrupt:
                break
            except subprocess.CalledProcessError as e:
                print(f"Could not fetch fingerprint for {name}.apache.org, continuing..." + str(e))
                unreachable.append(name)

    stamp = time.strftime("%Y-%m-%d %H:%M:%S %z", time.gmtime())
    rtxt = ""
    if unreachable:
        rtxt = f"({len(unreachable)} hosts not reachable)"
    html = """
        <style>
                    #fingerprints td:last-child {
        font-size: 0.8rem;
                        font-family: sans-serif;
                    }
                    #fingerprints tr:nth-child(even) {
        background-color: #f4f4f4
                    }
                    #fingerprints>kbd,#fingerprints td:not(:first-child) kbd,#fingerprints li>kbd {
        -moz-border-radius:3px;
                        -moz-box-shadow:0 1px 0 rgba(0,0,0,0.2),0 0 0 2px #fff inset;
                        -webkit-border-radius:3px;
                        -webkit-box-shadow:0 1px 0 rgba(0,0,0,0.2),0 0 0 2px #fff inset;
                        background-color:#f7f7f7;
                        border:1px solid #ccc;
                        border-radius:3px;
                        box-shadow:0 1px 0 rgba(0,0,0,0.2),0 0 0 2px #fff inset;
                        color:#333;
                        display:inline-block;
                        font-family:monospace;
                        font-size:11px;
                        line-height:1.4;
                        margin:0 .1em;
                        padding:.1em .6em;
                        text-shadow:0 1px 0 #fff;
                    }
                    #fingerprints th, #fingerprints td {
        padding: 6px !important;
                    }

                </style>
    """ + f"<h2>{reachable} verified hosts {rtxt} @ {stamp}</h2>"
    html += "<table id='fingerprints' cellpadding='6' cellspacing='0' style='border: 0.75px solid #333;'><tr><th>Hostname</th><th>IPv4</th><th>RSA Fingerprint (SHA256)</th><th>ECDSA Fingerprint (SHA256)</th><th>Status</th></tr>\n"

    # Print each known host
    for name, data in sorted(old_hosts.items()):
        if name in hosts:
            status = "Verified (OK)"
            if name in unreachable:
                status = "Unreachable"
            if data["notes"]:
                status = "<span color='F70'>CHANGED</span>"
            html += (
                    "<tr style='background: inherit;'><td><kbd><b>%s</b></kbd></td><td><kbd>%s</kbd></td><td><kbd>%s</kbd></td><td><kbd>%s</kbd></td><td>%s</td></tr>\n"
                    % (name, data["ipv4"], data["fingerprint_rsa"], data["fingerprint_ecdsa"], status)
            )

    # Print unknown unreachables at the bottom
    for name in unreachable:
        if name in old_hosts:
            continue
        data = hosts[name]
        ipv4 = [x for x in data.ips if "." in x][0]
        html += (
                "<tr style='background: inherit;'><td><kbd><b>%s</b></kbd></td><td><kbd>%s</kbd></td><td><kbd>N/A</kbd></td><td><kbd>N/A</kbd></td><td>Unreachable</td></tr>\n"
                % (name, ipv4)
        )
    html += "</table>"
    
    globals()['FPDATA'].update({"HTML": html, "changes": {"changed": len(all_notes), "notes": all_notes}, "old_hosts": old_hosts})
    print("writing to file...")
    with open(JSON_FILE, "w+") as f:
        json.dump(globals()['FPDATA'], f)
    f.close()

#if __name__ == "__main__":
#    print("Scanning...")
#    print(get_fps())
#    fpscan()
#    print(fpdata['HTML'])

async def fp_scan_loop():
    while True:
        fpscan()
        await asyncio.sleep(43200)

plugins.root.register(fp_scan_loop, slug="machines", title="Machine Fingerprints", icon="bi-fingerprint")
