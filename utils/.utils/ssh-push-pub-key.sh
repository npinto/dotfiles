#!/bin/bash

fname=$1;
host=$2;
if [ "$(echo $fname | tail -c 5)" = ".pub" ]; then
    cat $fname | ssh $host 'mkdir -p ~/.ssh && cd ~/.ssh && touch authorized_keys && chmod 640 authorized_keys && cat >> authorized_keys';
else
    echo "Wrong extension detected! Use a public key with extension .pub!!!";
    echo "Usage: $0 /path/to/key.pub user@host";
    exit 1
fi
