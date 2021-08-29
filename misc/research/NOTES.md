# Developer Notes
Some developer notes that may be interesting for those modifying the source code are here.  I tend to be OCD with the readme, so if I find I'm rambling on something, I'll copy it here :)


## Obtaining the Channel/Subchannel

Since locast does not return channel numbers, getting the proper station and subchannel is a somewhat dicey affair.  I manually run a script (separate from the `main.py` locast2plex command) to download a station list directly from the FCC, filter out non-TV and unlicenced stations and convert it to a JSON friendly format.  When you run locast2plex, I compare the callsign given by locast to the callsign in the JSON to get the channel number.  To get the subchannel, locas2plex looks at the number after the callsign returned from locast (so far this is what it seems they use to indicate subchannel).

When a station has an inaccurate channel/subchannel, either a station will receive an outdated channel number, or (for stations we don't recognize at all their channel numbers assigned sequentially from 1000 on).  Some callsigns are also incorrectly repored via locast.  For instance, in the Philadelphia market, WYBE has been renamed WPPT in 2018, yet this hasn't been reflected in the API.  