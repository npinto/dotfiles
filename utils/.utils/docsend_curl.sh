#!/bin/bash

: ${2?"Usage: $0 URL NUMBER_OF_SLIDES"}

set -e
set -x

command -v curl
command -v jq

tmpdir=$(mktemp -d)
cookies=${tmpdir}/cookies.txt
jsondir=${tmpdir}/json_files

curl -c ${cookies} -b ${cookies} $1 -H 'Connection: keep-alive' -H 'Upgrade-Insecure-Requests: 1' -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.67 Safari/537.36' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8' -H 'Accept-Encoding: gzip, deflate, br' -H 'Accept-Language: en-US,en;q=0.9,fr;q=0.8' --compressed > /dev/null


mkdir -p ${jsondir}
mkdir -p ./image_files
for i in $(seq 1 $2); do
    ii=$(printf "%03d" $i);
    curl -b ${cookies} -c ${cookies} ${1}/page_data/${i} -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.67 Safari/537.36' -H 'Accept: application/json, text/javascript, */*; q=0.01' > ${jsondir}/page_data_${ii}.json;
    curl $(jq -r .imageUrl ${jsondir}/page_data_${ii}.json) > image_files/slide_${ii}.png;
done;

