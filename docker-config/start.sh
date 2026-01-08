#!/usr/bin/env bash

# entry script for Docker image

rm /var/log/apache2/* # clear old logs

service syslog-ng start

apachectl start

cd server

exec python3 -m hypercorn -b 0.0.0.0:8000 server:application --error-logfile - --access-logfile /var/log/apache2/server.log
