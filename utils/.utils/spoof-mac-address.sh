#!/bin/bash

mac=$(openssl rand -hex 6 | sed 's/\(..\)/\1:/g; s/.$//')
echo ${mac}

sudo ifconfig en0 ether ${mac}

ifconfig en0
ifconfig en0 | grep ether
