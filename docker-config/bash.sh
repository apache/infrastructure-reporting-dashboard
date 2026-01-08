#!/usr/bin/env bash

# start container with shell

# by default, run does not define ports to avoid clashes
docker compose run --service-ports --rm --entrypoint /bin/bash infra-reports
