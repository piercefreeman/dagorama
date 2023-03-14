#!/bin/ash -e

if [ "$1" = "broker" ]; then
    exec /broker
else
    exec "$@"
fi
