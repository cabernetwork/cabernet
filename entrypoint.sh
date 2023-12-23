#!/bin/bash

# Add local user
# Either use the USER_ID if passed in at runtime or
# fallback

USER_ID=${PUID:-1000}
GROUP_ID=${PGID:-1000}
USERNAME=cabernet
echo "Starting with UID : $USER_ID"
addgroup -S -g $GROUP_ID $USERNAME
adduser -S -D -H -u $USER_ID -G $USERNAME $USERNAME
chown -R $USER_ID:$GROUP_ID /app

su-exec $USERNAME python3 /app/tvh_main.py "$@"