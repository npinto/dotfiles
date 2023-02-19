#!/bin/bash

: ${3?"Usage: $0 URL NUMBER_OF_SLIDES PASSCODE"}

set -e
set -x

command -v curl
command -v jq

url=$1
code=$(basename ${url})
tmpdir=$(mktemp -d)
cookies=${tmpdir}/cookies.txt
jsondir=${tmpdir}/json_files
PASSCODE=$3

curl -c ${cookies} -b ${cookies} ${url} -H 'Connection: keep-alive' -H 'Upgrade-Insecure-Requests: 1' -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.67 Safari/537.36' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8' -H 'Accept-Encoding: gzip, deflate, br' -H 'Accept-Language: en-US,en;q=0.9,fr;q=0.8' --compressed > /dev/null


curl -c ${cookies} -b ${cookies} ${url} \
-H 'Connection: keep-alive' -H 'Cache-Control: max-age=0' -H 'Origin: https://docsend.com' -H 'Upgrade-Insecure-Requests: 1' -H 'Content-Type: application/x-www-form-urlencoded' -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8' -H 'Accept-Encoding: gzip, deflate, br' -H 'Accept-Language: en-US,en;q=0.9,fr;q=0.8' --data 'utf8=%E2%9C%93&_method=patch&link_auth_form%5Bemail%5D=nicolas.pinto%40gmail.com&link_auth_form%5Bpasscode%5D='${PASSCODE}'&commit=Continue' --compressed

#curl -c ${cookies} -b ${cookies} ${url} \
  #-H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9' \
  #-H 'Accept-Language: en-US;q=0.5' \
  #-H 'Cache-Control: max-age=0' \
  #-H 'Connection: keep-alive' \
  #-H 'Content-Type: application/x-www-form-urlencoded' \
  #-H 'Origin: https://docsend.com' \
  #-H 'Referer: https://docsend.com/view/6aduhvx736ys3uyv/d/ixika7w38q4b3hhf' \
  #-H 'Sec-Fetch-Dest: document' \
  #-H 'Sec-Fetch-Mode: navigate' \
  #-H 'Sec-Fetch-Site: same-origin' \
  #-H 'Sec-Fetch-User: ?1' \
  #-H 'Sec-GPC: 1' \
  #-H 'Upgrade-Insecure-Requests: 1' \
  #-H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.115 Safari/537.36' \
  #--data-raw 'utf8=%E2%9C%93&_method=patch&authenticity_token=J7DEnRwySEQGvg8%2FrUdf0FLeg0pY7ZxXAIGSbH9US2s4qD7n2BYtipK21gKf0Jc6XhABj%2BuKPbSiqCs%2Ft07EvA%3D%3D&link_auth_form%5Bemail%5D=nicolas.pinto%40gmail.com&link_auth_form%5Bpasscode%5D='${PASSCODE}'&link_auth_form%5Btimezone_offset%5D=' \
  #--compressed

mkdir -p ${jsondir}
mkdir -p ./${code}_image_files
for i in $(seq 1 $2); do
    ii=$(printf "%03d" $i);
    curl -b ${cookies} -c ${cookies} ${url}/page_data/${i} -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.67 Safari/537.36' -H 'Accept: application/json, text/javascript, */*; q=0.01' > ${jsondir}/page_data_${ii}.json;
    curl $(jq -r .imageUrl ${jsondir}/page_data_${ii}.json) > ./${code}_image_files/slide_${ii}.png;
done;

