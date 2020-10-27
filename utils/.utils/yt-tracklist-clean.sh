#!/bin/bash

cat "$1" \
    | grep -v 'Copyright owners' \
    | grep -v 'Ad revenue' \
    | grep -v 'Content found during' \
    | grep  -v 'some territories' \
    | grep -v 'cannot be monetized' \
    | grep -v 'Copyright owner' \
    | grep -v 'On behalf' \
    | grep -v 'GmbH' \
    | grep -v 'LLC' \
    | grep -v 'Content used' \
    | grep -v 'Claim type' \
    | grep -v 'Impact on the video' \
    | grep -v 'Actions' \
    | grep -v '\/' \
    | grep -v 'Blocked in all' \
    | grep -v 'or monetized' \
    | grep -v '^1\.00$' \

