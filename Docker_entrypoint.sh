#!/bin/bash

# Add local user
# Either use the USER_ID if passed in at runtime or
# fallback

USER_ID=${PUID:-1000}
GROUP_ID=${PGID:-1000}
USERNAME=cabernet

# Set IP and Netmask
LOCAL_IP="$(hostname -i)"
_IP_ADDRESS=${IP_ADDRESS:-$LOCAL_IP}
_NETMASK=${NETMASK:-${_IP_ADDRESS}/32}

# Start message
echo "Starting with UID : $USER_ID"
echo "Starting with Playlist/Plex IP : $_IP_ADDRESS"
echo "Starting with Netmask : $_NETMASK"

# Add local user
addgroup -S -g $GROUP_ID $USERNAME
adduser -S -D -H -h /app -u $USER_ID -G $USERNAME $USERNAME

# Block update from webui
blockUpdate="/app/Do_Not_Upgrade_from_WEBUI_on_Docker"

# Backward compatibility
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


# Generate config.ini
confFile="/app/data/config.ini"

# Update config.ini
if [ -f "$confFile" ] && [ -n "$IP_ADDRESS" ]; then
    sed -i "s|^plex_accessible_ip = .*|plex_accessible_ip = $IP_ADDRESS|" "$confFile"
fi

if [ -f "$confFile" ] && [ -n "$NETMASK" ]; then
    sed -i "s|^udp_netmask = .*|udp_netmask = $NETMASK|g" "$confFile"
fi

# Generate config.ini if does not exist
if [ ! -f "$confFile" ]; then
mkdir -p /app/data

cat <<EOF > "$confFile"
[hdhomerun]
udp_netmask = $_NETMASK

[web]
plex_accessible_ip = $_IP_ADDRESS

[ssdp]
udp_netmask = $_NETMASK
EOF
fi

# Download Plugins
if [ -n "$PLUGINS" ]; then
    [ ! -d /app/plugins_ext ] && mkdir -p /app/plugins_ext
    for plugin in ${PLUGINS,,}; do
    [ "$plugin" == "tvguide" ] && TYPE="epg" || TYPE="video"
    PURL="$(curl -sL https://api.github.com/repos/cabernetwork/provider_${TYPE}_${plugin}/releases/latest | grep tarball_url | cut -d'"' -f4)"
    if [ "$?" == "0" ] && [ ! -d "/app/plugins_ext/provider_${TYPE}_${plugin}" ]; then
        echo "Installing plugin ${plugin}..."
        mkdir -p /tmp/plugins
        curl -sL "$PURL" | tar -xzf - -C /tmp/plugins
    elif [ -d "/app/plugins_ext/provider_${TYPE}_${plugin}" ]; then
        echo "Plugin ${plugin} already installed"
    elif [ "$?" != "0" ]; then
        echo "Plugin ${plugin} not found"
    fi
    done
    if [ -d "/tmp/plugins" ]; then
        mv -n /tmp/plugins/*/provider_* /app/plugins_ext/
        rm -rf /tmp/plugins
    fi
fi

# Set permissions
chown -R $USER_ID:$GROUP_ID /app

[ ! -f "$blockUpdate" ] && touch "$blockUpdate"

su-exec $USERNAME python3 /app/tvh_main.py "$@"