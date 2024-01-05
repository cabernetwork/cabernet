#!/bin/sh

# Add local user
# Either use the USER_ID if passed in at runtime or
# fallback

USER_ID=${PUID:-1000}
GROUP_ID=${PGID:-1000}
USERNAME=cabernet
echo "Starting with UID : $USER_ID"
addgroup -S -g $GROUP_ID $USERNAME
adduser -S -D -H -h /app -u $USER_ID -G $USERNAME $USERNAME

blockUpdate="/app/Do_Not_Upgrade_from_WEBUI_on_Docker"

oldKeyFile="/root/.cabernet/key.txt"
newKeyFile="/app/.cabernet/key.txt"

if [ -f "$oldKeyFile" ]; then

cat <<EOF
----------
!!!WARNING!!!
==> DECREPTED Volume Option
Please update your volume for 'key.txt' to new location.
$newKeyFile
----------
EOF

cp "$oldKeyFile" "$newKeyFile"
fi

# Set permissions
chown -R $USER_ID:$GROUP_ID /app

[ ! -f "$blockUpdate" ] && touch "$blockUpdate"

su-exec $USERNAME python3 /app/tvh_main.py "$@"