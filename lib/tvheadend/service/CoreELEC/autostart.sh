#!/bin/sh
# place file in the /storage/.config/ folder and make it executable
# This script is based on installing/unzipping the app in /storage/cabernet
#
(
sleep 10
. /opt/etc/profile
cd /storage/cabernet
/opt/bin/python3 /storage/cabernet/tvh_main.py
) &
