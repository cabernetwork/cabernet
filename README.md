## NOTICE: 
By default this app doesn't provide any video sources, only the plugins access the providers streams for personal use.

## Installation
### 1. Requirements
- Python 3.8+
- python cryptography module
- python httpx[http2] module
- (optional) streamlink module
- ffmpeg and ffprobe

### 2. Installation
- Download source
- Unzip source in the installation folder
- Launch the app by running the command "python3 tvh_main.py". This should create a data folder and a config.ini inside that folder
- Bring up browser and go to http://ip address:6077/
- From Plugins, install PlutoTV plugin
- Stop the app
- Edit the data/config.ini and add the following lines (Update: This is suppose to automatically happen in 0.9.14)
<pre>
[plutotv_default]
label = PlutoTV Instance
</pre>
- Launch the app by running the command "python3 tvh_main.py"
- Bring up browser and go to http://ip address:6077/
- Go to settings and make changes you want.
    - Logging: Change log level from warning to info if needed
- Enable the PlutoTV instance in the Settings page
- Restart the app (from the Scheduler/Applications) to have the plugin fully activate
- From XML/JSON Links try some of the links

### 3. Services
- MS Windows
    - Services for MS Windows is auto-created using the installer provided for each release.
- Unix/Linux
    - Services for CoreELEC and Debian/Ubuntu are found here. Follow the instructions found in the files.
    - https://github.com/cabernetwork/cabernet/tree/master/lib/tvheadend/service

### 4. Docker
See http://ghcr.io/cabernetwork/cabernet:latest
- Use or Review ports and remote mount points at docker-compose.yml
- Note: it requires unzipping the cabernet source into ./docker/cabernet/config/app to run
- Recommended Docker file: Dockerfile_tvh_crypt.alpine
- Bring up browser and go to http://ip address:6077/
- From Plugins, install PlutoTV plugin
- Stop the app
- Edit the data/config.ini and add the following lines
<pre>
[plutotv_default]
label = PlutoTV Instance
</pre>
- Restart the app (from the Scheduler/Applications) to have the plugin fully activate
- From XML/JSON Links try some of the links

### 5. Notes
- URL used can include plugin and instance levels to filter down to a specific set of data
    - http://ip address:6077/channels.m3u
    - http://ip address:6077/pLuToTv/channels.m3u
    - http://ip address:6077/PlutoTV/Default/channels.m3u
- config.ini group tag requirements when creating an instance
    - All lower case
    - Underscore is a key character in section tags and separates the plugin name from the instance name
    - Use a single word if possible for the instance name
    - Do not change the instance name unless you go into data management and remove the instance first.
    - [plutotv_mychannels]

### 6. Forum
https://tvheadend.org/boards/5/topics/43052

Enjoy
