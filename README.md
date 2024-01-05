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
- Restart Cabernet twice from   Scheduled Tasks > Applications > Restart
- Go to settings and make changes you want.
    - Logging: Change log level from warning to info if needed
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

#### a. Using docker-compose
To install Cabernet:
```
1. Grab the cabernet source and unpack into a folder
2. Edit docker-compose.yml and set the volume folder locations
3. docker-compose pull cabernet
4. docker-compose up -d cabernet
```

#### b. docker cli
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

##### Parameters
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

#### c. Other Docker Info
Cabernet configuration setting Clients > Web Sites > plex_docker_ip should be set to your computers IP address and not the internal IP inside the docker container.  This will allow the channels.m3u file to have the correct IP address for streaming.


#### d. Updating Info
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

#### e. Via Watchtower auto-updater
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
