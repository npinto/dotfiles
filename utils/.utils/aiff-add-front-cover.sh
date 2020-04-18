#!/bin/bash

frontcover="$1"
audiofile="$2"

kid3-cli -c 'select "'"${audiofile}"'"' -c 'set picture:"'"${frontcover}"'" "Picture Description"' -c 'save'
