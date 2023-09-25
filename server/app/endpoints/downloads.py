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
import functools

"""Handler for download stats - ported from https://github.com/apache/infrastructure-dlstats"""
import quart
from ..lib import middleware, config, asfuid
import elasticsearch
import elasticsearch_dsl
from .. import plugins
import re
import time

MAX_HITS = 50  # Max number of artifacts to track in a single search
DOWNLOADS_CACHE_ITEMS = 200  # Keep the 200 latest search results in cache. 200 results is ~50MB
DOWNLOADS_CACHE_TTL = 7200   # Only cache items for 2 hours

# Different indices have different field names, account for it here:
FIELD_NAMES = {
    "fastly": {
        "geo_country": "geo_country_code",
        "bytes": "bytes",
        "vhost": "vhost",
        "uri": "url",
        "timestamp": "timestamp",
        "_vhost_": "dlcdn.apache.org",
        "request_method": "request",
    },
    "loggy": {
        "geo_country": "geo_country",
        "bytes": "bytes",
        "vhost": "vhost",
        "uri": "uri",
        "timestamp": "@timestamp",
        "_vhost_": "downloads.apache.org",
        "request_method": "request_method",
    },
}

dataurl = "http://localhost:9200"
if hasattr(config.reporting, "downloads"):  # If prod...
    dataurl = config.reporting.downloads["dataurl"]

es_client = elasticsearch.AsyncElasticsearch(hosts=[dataurl], timeout=45)
downloads_data_cache = []


@asfuid.session_required
async def process(form_data):
    project = form_data.get("project", "httpd")
    duration = form_data.get("duration", 7)
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
    cache_key = f"{project}-{duration}"
    cache_timeout_ts = time.time() - DOWNLOADS_CACHE_TTL
    for item in downloads_data_cache:  # (cache_key, cache_ts, cache_data)
        if item[0] == cache_key and item[1] >= cache_timeout_ts:
            cache_found = True
            downloaded_artifacts = item[2]
            break

    if not cache_found:
        for provider, field_names in FIELD_NAMES.items():
            q = elasticsearch_dsl.Search(using=es_client)
            q = q.filter("range", **{field_names["timestamp"]: {"gte": f"now-{duration}d"}})
            q = q.filter("match", **{field_names["request_method"]: "GET"})
            q = q.filter("range", bytes={"gt": 5000})
            q = q.filter("match", **{field_names["uri"]: project})
            q = q.filter("prefix", **{field_names["uri"] + ".keyword": f"/{project}/"})
            q = q.filter("match", **{field_names["vhost"]: field_names["_vhost_"]})

            q.aggs.bucket(
                "most_downloads", elasticsearch_dsl.A("terms", field=f"{field_names['uri']}.keyword", size=MAX_HITS)
            ).bucket("per_day", "date_histogram", interval="day", field=field_names["timestamp"]).metric(
                "bytes_sum", "sum", field=field_names["bytes"]
            ).metric(
                "unique_ips", "cardinality", field="client_ip.keyword"
            ).metric(
                "cca2", "terms", field=field_names["geo_country"] + ".keyword"
            ).pipeline(
                "product_by_unique", "bucket_sort", sort=[{"unique_ips": "desc"}]
            )

            q.aggs.bucket(
                "most_traffic", elasticsearch_dsl.A("terms", field=f"{field_names['uri']}.keyword", size=MAX_HITS)
            ).bucket("per_day", "date_histogram", interval="day", field=field_names["timestamp"]).metric(
                "bytes_sum", "sum", field=field_names["bytes"]
            ).metric(
                "unique_ips", "cardinality", field="client_ip.keyword"
            ).metric(
                "cca2", "terms", field=field_names["geo_country"] + ".keyword"
            ).pipeline(
                "product_by_sum", "bucket_sort", sort=[{"bytes_sum": "desc"}]
            )

            resp = await es_client.search(index=f"{provider}-*", body=q.to_dict(), size=0, timeout="60s")
            if "aggregations" not in resp:  # Skip this provider if no data is available
                continue

            for methodology in (
                "most_downloads",
                "most_traffic",
            ):
                for entry in resp["aggregations"][methodology]["buckets"]:
                    url = re.sub(r"/+", "/", entry["key"])
                    if "." not in url or url.endswith("/") or url.endswith("KEYS"):  # Never count KEYS or non-files
                        continue
                    if url not in downloaded_artifacts:
                        downloaded_artifacts[url] = {
                            "bytes": 0,
                            "hits": 0,
                            "hits_unique": 0,
                            "cca2": {},
                            "daily_stats": {},
                        }
                    no_bytes = 0
                    no_hits = 0
                    no_hits_unique = 0
                    cca2_hits = {}
                    daily_data = []

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
