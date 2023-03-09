#!/bin/ash -e

if [ "$1" = "broker" ]; then
    exec /broker --port $PORT --host $HOST
else
    exec "$@"
fi
