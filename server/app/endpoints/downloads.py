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

"""Handler for download stats - ported from https://github.com/apache/infrastructure-dlstats"""
import quart
from ..lib import middleware, config, asfuid
import elasticsearch
import elasticsearch_dsl
from .. import plugins
import re
import time
import ua_parser.user_agent_parser

MAX_HITS = 60  # Max number of artifacts to track in a single search
MAX_HITS_UA = 60  # Max number of user agents to collate
DOWNLOADS_CACHE_ITEMS = 200  # Keep the 200 latest search results in cache. 200 results is ~50MB
DOWNLOADS_CACHE_TTL = 7200   # Only cache items for 2 hours

INTERNAL_AGENTS = {
    "Windows Package Manager": ("winget-cli", "Microsoft-Delivery-Optimization", "WindowsPackageManager", "Microsoft BITS",),
    "NSIS (plugin)": ("NSIS_Inetc", ),
    "Transmission": ("Transmission/", ),
    "Free Download Manager": ("FDM", ),
    "Patch My PC Client": ("Patch My PC Publishing Service", ),
    "Artifactory": ("Artifactory", ),
    "Scoop/Shovel": ("Scoop/", "Shovel/", ),
    "BigFix": ("BigFix", ),
}

# Different indices have different field names, account for it here:
FIELD_NAMES = {
    "fastly": { # the index prefix
        "geo_country": "geo_country_code",
        "bytes": "bytes",
        "vhost": "vhost",
        "uri": "url",
        "timestamp": "timestamp",
        "_vhost_": "dlcdn.apache.org", # This is a variable field value, not a name
        "request_method": "request",
        "useragent": "request_user_agent",
    },
    "loggy": { # the index prefix
        "geo_country": "geo_country",
        "bytes": "bytes",
        "vhost": "vhost",
        "uri": "uri",
        "timestamp": "@timestamp",
        "_vhost_": "downloads.apache.org", # This is a variable field value, not a name
        "request_method": "request_method",
        "useragent": "useragent",
    },
}

dataurl = "http://localhost:9200"
if hasattr(config.reporting, "downloads"):  # If prod...
    dataurl = config.reporting.downloads["dataurl"]

es_client = elasticsearch.AsyncElasticsearch(hosts=[dataurl], timeout=45)

# WARNING: whilst operations on lists are generally thread-safe, this cache is not,
# because updating the cache requires several operations which are not currently protected by a lock.
# However, it appears that access to instances of this code are single-threaded by hypercorn,
# so the lack of thread safety should not be a problem.
downloads_data_cache = []

async def make_query(provider, field_names, project, duration, filters, max_hits=MAX_HITS, max_ua=MAX_HITS_UA, downscaled=False):
    q = elasticsearch_dsl.Search(using=es_client)
    q = q.filter("range", **{field_names["timestamp"]: {"gte": f"now-{duration}d"}})
    q = q.filter("match", **{field_names["request_method"]: "GET"})
    q = q.filter("range", bytes={"gt": 5000}) # this filters out hashes and (most?) sigs
    q = q.filter("prefix", **{field_names["uri"] + ".keyword": f"/{project}/"})
    q = q.filter("match", **{field_names["vhost"]: field_names["_vhost_"]})

    # Various standard filters for weeding out bogus requests
    if "empty_ua" in filters:  # Empty User-Agent header, usually automation gone wrong
        q = q.exclude("terms", **{field_names["useragent"]+".keyword": ["", "-"]})
    # TODO: Make this not extremely slow. For now, we'll filter in post.
    #if "no_query" in filters:  # Don't show results with query strings in them
    #    q = q.exclude("wildcard", **{field_names["uri"]+".keyword": "*="})

    # Bucket sorting by most downloaded items
    main_bucket = q.aggs.bucket(
        "most_downloads", elasticsearch_dsl.A("terms", field=f"{field_names['uri']}.keyword", size=max_hits)
    )
    main_bucket.metric("useragents", "terms", field=field_names["useragent"]+".keyword", size=max_ua)
    main_bucket.bucket("per_day", "date_histogram", interval="day", field=field_names["timestamp"]
                       ).metric(
        "bytes_sum", "sum", field=field_names["bytes"]
    ).metric(
        "unique_ips", "cardinality", field="client_ip.keyword"
    ).metric(
        "cca2", "terms", field=field_names["geo_country"] + ".keyword"
    )

    # Bucket sorting by most bytes downloaded (may differ from most downloads top 50!)
    main_bucket = q.aggs.bucket(
        "most_traffic", elasticsearch_dsl.A("terms", field=f"{field_names['uri']}.keyword", size=max_hits, order={"bytes_sum": "desc"})
    )
    main_bucket.metric("useragents", "terms", field=field_names["useragent"]+".keyword", size=max_ua)
    main_bucket.metric(
        "bytes_sum", "sum", field=field_names["bytes"]
    ).bucket("per_day", "date_histogram", interval="day", field=field_names["timestamp"]
             ).metric(
        "bytes_sum", "sum", field=field_names["bytes"]
    ).metric(
        "unique_ips", "cardinality", field="client_ip.keyword"
    ).metric(
        "cca2", "terms", field=field_names["geo_country"] + ".keyword"
    )
    try:
        resp = await es_client.search(index=f"{provider}-*", body=q.to_dict(), size=0, timeout="60s")
        if downscaled and resp:
            resp["downscaled"] = True
        return resp
    except elasticsearch.TransportError as e:
        # If too many buckets for us to handle, downscale the UA search
        if isinstance(e.info, dict) and 'too_many_buckets_exception' in e.info["error"].get("caused_by", {}).get("type", ""):
            max_ua = int(max_ua*0.67)
            max_hits = int(max_hits*0.67)
            print(f"Too many buckets for {project}, downscaling query by 33%")
            if max_ua > 2:
                return await make_query(provider, field_names, project, duration, filters, max_hits, max_ua, True)
    return {"downscaled": downscaled}



@asfuid.session_required
async def process(form_data):
    project = form_data.get("project", "httpd")    # Project/podling to fetch stats for
    duration = form_data.get("duration", 7)        # Timespan to search (in whole days)
    filters = form_data.get("filters", "empty_ua,no_query") # Various search filters
    if isinstance(duration, str):
        if duration.endswith("d"):
            duration = duration[:-1]
        try:
            duration = int(duration)
        except ValueError:
            return {"success": False, "message": "Invalid duration window! Please specify a whole number of days"}

    downloaded_artifacts = {}

    # Check if we have a cached result
    cache_found = False
    # TODO: the cache key needs to take account of form_data filters as they affect the content
    cache_key = f"{project}-{duration}"
    cache_timeout_ts = time.time() - DOWNLOADS_CACHE_TTL
    for item in downloads_data_cache:  # (cache_key, cache_ts, cache_data)
        if item[0] == cache_key and item[1] >= cache_timeout_ts:
            cache_found = True
            downloaded_artifacts = item[2]
            break

    if not cache_found:
        downscaled = False
        for provider, field_names in FIELD_NAMES.items():
            resp = await make_query(provider, field_names, project, duration, filters)
            if "aggregations" not in resp:  # Skip this provider if no data is available
                continue
            if resp.get("downscaled"):  # Too many damn buckets
                downscaled = True
            for methodology in (
                "most_downloads",
                "most_traffic",
            ):
                for entry in resp["aggregations"][methodology]["buckets"]:
                    # url, shortened = /incubator/ponymail/foo.tar.gz -> foo.tar.gz
                    url = re.sub(r"/+", "/", entry["key"]).replace(f"/{project}/", "", 1)
                    # TODO: Address in OpenSearch later on...
                    if "no_query" in filters and "?" in url:
                        continue
                    if "." not in url or url.endswith("/") or url.endswith("KEYS"):  # Never count KEYS or non-files
                        continue
                    if url not in downloaded_artifacts:
                        downloaded_artifacts[url] = {
                            "bytes": 0,
                            "hits": 0,
                            "hits_unique": 0,
                            "cca2": {},
                            "daily_stats": {},
                            "useragents": {},
                        }
                    no_bytes = 0
                    no_hits = 0
                    no_hits_unique = 0
                    cca2_hits = {}
                    daily_data = []

                    # User Agent (Browser + OS) summation
                    uas = {}
                    for uaentry in entry["useragents"]["buckets"]:
                        ua_agent = uaentry["key"] # the full agent string
                        # NOTE: ua_parser will set OS and UA Family to "Other" when it doesn't recognize the UA string.
                        ua = ua_parser.user_agent_parser.Parse(ua_agent)
                        ua_os_family = ua.get("os", {}).get("family", "Unknown")
                        # If OS is "Other", we'll adjust it to "Unknown" ourselves.
                        if ua_os_family == "Other":
                            ua_os_family = "Unknown"
                        # UA family will typically be "Other" when unknown to the parser, we'll address this below.
                        # If the family is empty, we'll also set to Other and adjust later on.
                        ua_agent_family = ua.get("user_agent", {}).get("family", "Other")
                        # Adjust for various package managers we know of
                        if ua_agent_family == "Other":
                            for ia_key, ia_names in INTERNAL_AGENTS.items():
                                if any(x in ua_agent for x in ia_names):
                                    ua_agent_family = ia_key
                                    break
                        # If we still don't know what this is, mark as "Unknown", to distinguish from the combined "Other" chart group.
                        if ua_agent_family == "Other":
                            ua_agent_family = "Unknown"
                        ua_key = ua_os_family + " / " + ua_agent_family
                        uas[ua_key] = uas.get(ua_key, 0) + uaentry["doc_count"]
                    for key, val in uas.items():
                        # There will be duplicate entries here, so we are going to go for the highest count found for each URL
                        downloaded_artifacts[url]["useragents"][key] = max(downloaded_artifacts[url]["useragents"].get(key, 0), val)

                    for daily_entry in entry["per_day"]["buckets"]:
                        day_ts = int(daily_entry["key"] / 1000)
                        nb_daily = int(daily_entry["bytes_sum"]["value"])
                        nh_daily = int(daily_entry["doc_count"])
                        no_bytes += nb_daily

                        visits_unique = int(daily_entry["unique_ips"]["value"])
                        no_hits += nh_daily
                        no_hits_unique += visits_unique

                        for ccaentry in daily_entry["cca2"]["buckets"]:
                            cca2 = ccaentry["key"]
                            cca2_count = ccaentry["doc_count"]
                            if cca2 and cca2 != "-":
                                cca2_hits[cca2] = cca2_hits.get(cca2, 0) + cca2_count
                        daily_data.append([day_ts, nh_daily, visits_unique, nb_daily])

                    # The prevailing agg (most hits or most traffic) wins
                    if no_bytes > downloaded_artifacts[url]["bytes"]:
                        downloaded_artifacts[url]["bytes"] += no_bytes
                        downloaded_artifacts[url]["daily_stats"] = daily_data
                    if no_hits > downloaded_artifacts[url]["hits"]:
                        downloaded_artifacts[url]["hits"] += no_hits
                        downloaded_artifacts[url]["daily_stats"] = daily_data
                    if no_hits_unique > downloaded_artifacts[url]["hits_unique"]:
                        downloaded_artifacts[url]["hits_unique"] += no_hits_unique
                    if sum([x for x in cca2_hits.values()]) > sum([x for x in downloaded_artifacts[url]["cca2"].values()]):
                        downloaded_artifacts[url]["cca2"] = cca2_hits
            # Ensure all entries are properly marked if query was downscaled
            if downscaled:
                for key, val in downloaded_artifacts.items():
                    val["downscaled"] = True

        # Set cache data and cull old cache list if needed
        new_cache_list = [item for item in downloads_data_cache if item[1] >= cache_timeout_ts]
        downloads_data_cache.clear()
        downloads_data_cache.extend(new_cache_list)
        # Make sure there is room to add another entry
        # entries are added in date order, so [0] is the oldest
        while len(downloads_data_cache) >= DOWNLOADS_CACHE_ITEMS:
            del downloads_data_cache[0]
        downloads_data_cache.append((cache_key, time.time(), downloaded_artifacts))

    return downloaded_artifacts or {"success": False, "message": "No results found"}


quart.current_app.add_url_rule(
    "/api/downloads",
    methods=[
        "GET",  # Session get/delete
    ],
    view_func=middleware.glued(process),
)

plugins.root.register(slug="downloads", title="Download Statistics", icon="bi-cloud-download", private=True)
