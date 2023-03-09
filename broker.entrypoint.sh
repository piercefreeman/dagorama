#!/bin/ash -e

if [ "$1" = "broker" ]; then
    exec /broker --port $PORT
else
    exec "$@"
fi
