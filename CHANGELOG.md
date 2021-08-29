# CHANGELOG

## FUTURE (may or may not be implemented):
 - Reorganize config.ini file
 - Start using pip for third-party plugins
 - Rename `plex_accessible_ip`/`plex_accessible_port` to `advertise_ip`/`advertise_port`. Add `bind_ip`/`bind_port` options (https://github.com/tgorgdotcom/locast2plex/pull/98)
 - Hopefully phase out FCC channel checking (when locast reports proper channel numbers)
 - Install script for those not using docker
 - Enable multiplatform Docker image
 - Wrap HTTP requests around error handling that existed in do_tuner() previously
 - Documentation added for Kodi, Emby/Jellyfin
 - Implement proper logging
 - Some kind of web based UI to modify config
 - Look into pull requests suggestions for ip addressing
 - A way to daemonize the script for those running outside of docker

## 1.0.0 (unreleased)
 - Most bugs squashed

## 0.6.3
 - Add error handling for when a channel in the EPG exists that does not exist in the channel list

## 0.6.2
 - Fix an issue where logins fail when passwords with a '%' are used

## 0.6.1
 - Create dev branch, add contributing docs to mention dev branch
 - rename master branch to main branch
 - moved most SSDP messages to show when new config option `verbose` is set to true
 - potential fix for error in getting fcc database
 - fixed a bug in deleting stale cache EPG data

## 0.6.0
 - Reorganized codebase for better modularity (@deathbybandaid)
 - Included all DMA codes so we don't have to update whenever locast rolls out to a new market (@deathbybandaid)
 - Added automatic pulling from FCC database (@deathbybandaid)
 - Added m3u/xmltv playlist endpoint (for Emby, Kodi etc.) (with help from @deathbybandaid)
 - Fixes to resolve legal complaints and...
 - ...uses a new way to connect to Plex
 - Some fixes for SSDP, may start working for applicable systems
 - Added ability to disable SSDP using config.ini
 - Fixes issue with query string in GET requests to the tuner
 - Made sure all errors return nonzero

## 0.5.3-hotfix
 - Switch to Python 3 (Thanks @ratherDashing! & @deathbybandaid)
 - Fix to resolve Locast auth issues

## 0.5.3
 - Scripts are now fully linted (Thanks @deathbybandaid!)
 - Updated Readme for spelling/clarity/credits (Thanks @tri-ler and @gogorichie!)
 - Added ability to place config in /app/config folder for Kubernetes users (Thanks @dcd!)
 - Added Detroit DMA support (Thanks @precision!)
 - Fix tuner count comparison (Thanks @ratherDashing!)
 - Refactored geolocation to mirror Locast methods (Thanks @FozzieBear!)
 - Added new contributing document and added unreleased section in changelog
 - Changed some var names for clarity.  
 - Fixed a bug where users running on bare command line/terminal could not set their ports. (Thanks @teconmoon)
 - Removed some old stuff in Dockerfile that are confusing users

## 0.5.2
 - Fixed a bug that prevented the success message from showing

## 0.5.1
 - Added success message at the end to indicate successful running
 - Fixed bug in docker-compose.yml
 - Updated readme for better clarity

## 0.5.0
 - Migrated environment settings to ini file -- should fix issues with special 
   characters in username/password, security concerns (thanks for the suggestion 
   @jcastilloalonso), as well as allowing to tweak internal settings without 
   resorting to modifying code.
 - Added ffmpeg.exe for Windows users
 - Merge fix to end ffmpeg zombie processes (thanks @FozzieBear!)
 - Add MINNEAPOLIS-ST. PAUL (thanks @steventwheeler!)
 - Fix for channel detection on subchannels ending in zero.

## 0.4.2
 - Enabled Miami and West Palm Beach markets
 - Fixed issue #10: renamed "docker-compose.env" to ".env"

## 0.4.1
- Added support for Tampa market
- Updated Changelog

## 0.4.0
- Fixed a bug in docker-compose.yml
- Fixed channels that only have one low resolution stream
- Overhauled channel detection and interpolation
- Reorganized api research notes to it's own folder

## 0.3.1
- Fix bugs in callsign detection
- More doc changes

## 0.3.0
- Created changelog!
- Remove telly dependency and doing the managing of streams and requests all by ourselves.
- Proper channel/subchannel applied to lineup
