"""
MIT License

Copyright (C) 2021 ROCKY4546
https://github.com/rocky4546

This file is part of Cabernet

Permission is hereby granted, free of charge, to any person obtaining a copy of this software
and associated documentation files (the "Software"), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software
is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software.
"""

import datetime
import json
import logging
import urllib.request

import lib.m3u8 as m3u8
import lib.common.exceptions as exceptions
from lib.common.decorators import handle_url_except
from lib.common.decorators import handle_json_except
from lib.db.db_channels import DBChannels
import lib.clients.channels.channels as channels

from . import constants
from .translations import plutotv_groups

class Channels:
    logger = None

    def __init__(self, _plutotv_instance):
        self.plutotv_instance = _plutotv_instance
        self.plutotv = _plutotv_instance.plutotv
        self.instance = _plutotv_instance.instance
        self.db = DBChannels(self.plutotv_instance.config_obj.data)
        self.config_section = self.plutotv_instance.config_section

    def refresh_channels(self, force=False):
        last_update = self.db.get_status(self.plutotv.name, self.instance)
        update_needed = False
        if not last_update:
            update_needed = True
        else:
            delta = datetime.datetime.now() - last_update
            if delta.total_seconds() / 3600 >= self.plutotv_instance.config_obj.data[self.plutotv.name.lower()]['channel-update_timeout']:
                update_needed = True
        if update_needed or force:
            ch_dict = self.get_plutotv_channels()
            self.db.save_channel_list(self.plutotv.name, self.instance, ch_dict)
        else:
            self.logger.debug('Channel data still new for {} {}, not refreshing'.format(self.plutotv.name, self.instance))

    @handle_json_except
    @handle_url_except
    def get_plutotv_channels(self):
        channels_url = 'https://api.pluto.tv/v2/channels.json'
        url_headers = {
            'Content-Type': 'application/json',
            'User-agent': constants.DEFAULT_USER_AGENT}
        req = urllib.request.Request(channels_url, headers=url_headers)
        with urllib.request.urlopen(req) as resp:
            ch_json = json.load(resp)

        ch_list = []
        if len(ch_json) == 0:
            self.logger.warning('plutotv HTTP Channel Request Failed for instance {}'.format(self.instance))
            raise exceptions.CabernetException('plutotv HTTP Channel Request Failed')

        self.logger.info("{}: Found {} stations on instance {}"
            .format(self.plutotv.name, len(ch_json),
            self.instance))

        counter=0
        for plutotv_channel in ch_json:
            if (plutotv_channel["isStitched"]
                   and plutotv_channel["visibility"] in ["everyone"]
                   and not plutotv_channel['onDemand']
                   and plutotv_channel["name"] != "Announcement"):
        
                hd = 0
                ch_id = str(plutotv_channel['_id'])
                ch_callsign = plutotv_channel['name']
                thumbnail = None
                thumbnail_size = None
                for tn in [self.plutotv_instance.config_obj.data[self.plutotv.name.lower()]['channel-thumbnail'],
                    "colorLogoPNG", "colorLogoSVG", "solidLogoSVG",
                    "solidLogoPNG", "thumbnail", "logo", "featuredImage"]:
                    if tn in plutotv_channel.keys():
                        thumbnail = plutotv_channel[tn]['path']
                        thumbnail_size = channels.get_thumbnail_size(thumbnail)
                        break

                stream_url = plutotv_channel['stitched']['urls'][0]['url']
                stream_url = stream_url.replace('&appName=', '&appName=web') \
                    .replace('&deviceMake=', '&deviceMake=Chrome') \
                    .replace('&deviceModel=', '&deviceModel=Chrome') \
                    .replace('&deviceType=', '&deviceType=web') \
                    .replace('&sid=', '&sid=' + \
                    self.plutotv_instance.config_obj.data['main']['uuid'] + \
                    str(counter))
                counter += 1
                channel = plutotv_channel['number']
                friendly_name = plutotv_channel['name']
                if self.plutotv_instance.config_obj.data[self.plutotv.name.lower()]['channel-import_groups']:
                    if plutotv_channel['category'] in plutotv_groups:
                        groups_other = plutotv_groups[plutotv_channel['category']]
                    else:
                        groups_other = [ plutotv_channel['category'] ]
                        self.logger.info('Missing plutotv category translation for: {}' \
                            .format(plutotv_channel['category']))
                else:
                    groups_other = None
                
                channel = {
                    'id': ch_id,
                    'enabled': True,
                    'callsign': ch_callsign,
                    'number': channel,
                    'name': friendly_name,
                    'HD': hd,
                    'group_hdtv': None,
                    'group_sdtv': None,
                    'groups_other': groups_other,
                    'thumbnail': thumbnail,
                    'thumbnail_size': thumbnail_size,
                    'stream_url': stream_url
                }
                ch_list.append(channel)
        return ch_list

    @handle_json_except
    @handle_url_except
    def get_channel_uri(self, _channel_id):
        self.logger.info(self.plutotv.name + ": Getting station info for " + _channel_id)
        ch_dict = self.db.get_channel(_channel_id, None, None)
        stream_url = ch_dict['json']['stream_url']

        #stream_headers = {'Content-Type': 'application/json',
        #    'User-agent': constants.DEFAULT_USER_AGENT}
        #req = urllib.request.Request(stream_url, headers=stream_headers)
        #with urllib.request.urlopen(req) as resp:
        #    stream_result = json.load(resp)

        self.logger.debug("Determining best video stream for " + _channel_id + "...")
        bestStream = None

        # find the heighest stream url bandwidth and save it to the list
        videoUrlM3u = m3u8.load(stream_url,
            headers={'User-agent': constants.DEFAULT_USER_AGENT})
        self.logger.debug("Found " + str(len(videoUrlM3u.playlists)) + " Playlists")

        if len(videoUrlM3u.playlists) > 0:
            for videoStream in videoUrlM3u.playlists:
                if bestStream is None:
                    bestStream = videoStream
                elif videoStream.stream_info.bandwidth > bestStream.stream_info.bandwidth:
                    bestStream = videoStream

            if bestStream is not None:
                self.logger.debug(_channel_id + " will use " +
                    " bandwidth at " + str(bestStream.stream_info.bandwidth) + " bps")
                return bestStream.absolute_uri
        else:
            self.logger.debug("No variant streams found for this station.  Assuming single stream only.")
            return stream_url


Channels.logger = logging.getLogger(__name__)
