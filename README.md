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
You can either use docker-compose or the docker cli.

| Architecture | Available |
|:----:|:----:|
| X86-64 | ✅ |
| arm64 | ✅ |
| armhf | ❌ |

**NOTES:** 
- Volume for ```/app/.cabernet``` must be provided before enabling encryption.
- armhf not available due to python cryptography only supports 64bit systems.
[Cryptography supported platforms](https://cryptography.io/en/latest/installation/#supported-platforms)

#### docker-compose
```
version: '2.4'
services:
    cabernet:
        container_name: cabernet
        image: ghcr.io/cabernetwork/cabernet:latest
        environment:
          - TZ="Etc/UTC"  # optional
          - PUID=1000     # optional
          - PGID=1000     # optional
        ports:
          - "6077:6077"
          - "5004:5004"
        restart: unless-stopped
        volumes:
          - /path/to/cabernet/data:/app/data      # optional
          - /path/to/cabernet/plugins_ext:/app/plugins_ext # optional
          - /path/to/cabernet/secrets:/app/.cabernet # optional
```

#### docker cli
```
docker run -d \
  --name=cabernet \
  -e PUID=1000 `#optional` \
  -e PGID=1000 `#optional` \
  -e TZ=Etc/UTC `#optional` \
  -p 6077:6077 \
  -p 5004:5004 \
  -v /path/to/cabernet/data:/app/data `#optional` \
  -v /path/to/plugins_ext:/app/plugins_ext `#optional` \
  -v /path/to/cabernet/secrets:/app/.cabernet `#optional` \
  --restart unless-stopped \
  ghcr.io/cabernetwork/cabernet:latest
```

#### Parameters

| Parameter | Function |
| :----: | :----: |
| -p 6077 | Cabernet WebUI |
| -p 5004 | Cabernet stream port |
| -e PUID=1000  | for UserID    |
| -e PGID=1000  | for GroupID   |
| -e TZ=Etc/UTC | specify a timezone to use, see this [list](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List).|
| -v /app/data | Where Cabernet should store its database and config. |
| -v /app/plugins_ext | External Plugins |
| -v /app/.cabernet | Where encryption key is stored |

#### Updating Info
**Via Docker Compose:**

- Update the image:
```
docker-compose rm --stop -f cabernet
docker-compose pull cabernet
docker-compose up -d cabernet
```

**Via Docker Run:**

- Update the image:   
```docker pull ghcr.io/cabernetwork/cabernet:latest```

- Stop the running container:  
```docker stop cabernet```

- Delete the container:   
```docker rm cabernet```

- You can also remove the old dangling images:
```docker image prune```

#### Via Watchtower auto-updater
```
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  containrrr/watchtower \
  --run-once cabernet
```

- For regulary updates follow Watchtower instructions 
https://containrrr.dev/watchtower/


### 5. Default Ports
- 6007 Web UI
- 5004 Stream port
- 1900 SSDP (if enabled)
- 65001 HDHomeRun (if enabled)

### 6. Notes
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

### 7. Forum
https://tvheadend.org/boards/5/topics/43052

Enjoy
