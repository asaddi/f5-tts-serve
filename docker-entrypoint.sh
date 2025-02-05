#!/bin/sh

exec /usr/local/bin/python server.py \
    --host 0.0.0.0 \
    "$@"
