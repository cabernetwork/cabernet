## NOTICE: 
By default this app doesn't provide any video sources, only the plugins access the providers streams for personal use.

## Installation
### 1. Requirements
- Python 3.7+
- python cryptography module
- python requests module
- (optional) streamlink module
- ffmpeg and ffprobe

### 2. Installation
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
- From XML/JSON Links try some of the links

### 3. Docker
See http://ghcr.io/cabernetwork/cabernet:latest

### 4. Notes
- URL used can include plugin and instance levels to filter down to a specific set of data
    - http://ipaddress:6077/channels.m3u
    - http://ipaddress:6077/pLuToTv/channels.m3u
    - http://ipaddress:6077/PlutoTV/Default/channels.m3u
- config.ini group tag requirements
    - All lower case
    - Underscore is a key character in section tags and separates the plugin name from the instance name
    - Use a single word if possible for the instance name
    - Do not change the instance name unless you go into data management and remove the instance first.
    - [plutotv_mychannels]

Enjoy
