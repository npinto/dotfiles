#!/bin/bash

set -e
set -x

curl -s https://raw.githubusercontent.com/sivel/speedtest-cli/master/speedtest.py | python3 - --secure
