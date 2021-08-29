#!/bin/sh
# place file in the /storage/.config/ folder and make it executable
# This script is based on installing/unzipping the app in /storage/tvheadend-locast
#
(
sleep 10
python3 /storage/tvheadend-locast/tvh_main.py
) &
