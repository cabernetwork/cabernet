
## Installation
1. Requirements
- Python 3.7+
- python cryptography module
- ffmpeg

2. Installation
- Download source
- Unzip source in the installation folder
- Create a data folder inside the installation folder and create a config.ini file inside the data folder
- Edit the config.ini and add the following lines
<pre>
[plutotv_default]
label = PlutoTV Instance
</pre>
- Launch the app by running the command "python3 tvh_main.py"
- Bring up browser and go to http://ipaddress:6077/
- Go to settings and make changes you want.
    - Logging: Change log level from warning to info if needed
    - Under Providers > PlutoTV enable
        - URL Filtering
        - PTS/DTS Resync
- From XML/JSON Links try some of the links

Enjoy

