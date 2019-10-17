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
