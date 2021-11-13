
## Installation in a CoreELEC environment
### 1. Requirements
- CoreELEC 19+
- entware
- ffmpeg
- python3 with cryptography module
- python3 pip environment

The following commands run in a CoreELEC shell will install the needed prerequisites:
<pre>
installentware
opkg install ffmpeg
opkg install python3-cryptography
opkg install python3-pip
</pre>

### 2. Installation location
- it is recomended that you Unzip the cabernet source into /storage/cabernet and then follow the installation instructions

### 3. Autostarting cabernet with CoreELEC/Kodi
- copy autostart.sh to the /storage/.config/ folder and make it executable
- reboot CoreELEC and cabernet should start 10 seconds after Kodi starts

### 4. Notes
- If cabernet does not start the following command should show if any errors that were encountered in autostart.sh
<pre>
systemctl status kodi-autostart.service -l --no-pager
</pre>
- If you encounter "ModuleNotFoundError: No module named '_cffi_backend'" you will likely need to delete entware and reinstall from scratch. Here is how to do that:
<pre>
# remove entware including all installed packages/modules/etc
rm -rf /opt/* 
#  
# install entware (reboot when prompted)
installentware
#
# install ffmpeg
opkg install ffmpeg
#
# install python3 with cryptography (including ALL needed other modules)
opkg install python3-cryptography
#
# install pip 
opkg install python3-pip
</pre>
