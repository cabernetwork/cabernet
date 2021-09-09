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

import json
import urllib.request

import lib.m3u8 as m3u8
import lib.common.exceptions as exceptions
import lib.clients.channels.channels as channels
from lib.common.decorators import handle_url_except
from lib.common.decorators import handle_json_except
from lib.plugins.plugin_channels import PluginChannels

from . import constants
from .translations import xumo_groups

class Channels(PluginChannels):

    def __init__(self, _instance_obj):
        super().__init__(_instance_obj)

    @handle_json_except
    @handle_url_except
    def get_channels(self):
        channels_url = 'https://valencia-app-mds.xumo.com/v2/channels/list/{}.json?geoId={}' \
            .format(self.plugin_obj.geo.channelListId, self.plugin_obj.geo.geoId)
        url_headers = {
            'Content-Type': 'application/json',
            'User-agent': constants.DEFAULT_USER_AGENT}
        req = urllib.request.Request(channels_url, headers=url_headers)
        with urllib.request.urlopen(req) as resp:
            ch_json = json.load(resp)
        ch_list = []
        if len(ch_json) == 0:
            self.logger.warning('xumo HTTP Channel Request Failed for instance {}'.format(self.instance_key))
            raise exceptions.CabernetException('xumo HTTP Channel Request Failed')

        self.logger.info("{}: Found {} stations on instance {}"
            .format(self.plugin_obj.name, len(ch_json['channel']['item']),
            self.instance_key))

        for xumo_channel in ch_json['channel']['item']:
            hd = 0
            ch_id = str(xumo_channel['guid']['value'])
            ch_callsign = xumo_channel['callsign']

            thumbnail = "https://image.xumo.com/v1/channels/channel/{}/512x512.png?type=color_onBlack" \
                .format(ch_id)
            thumbnail_size = channels.get_thumbnail_size(thumbnail)
 
            channel = xumo_channel['number']
            friendly_name = xumo_channel['title']
            groups_other = None
            if 'genre' in xumo_channel:
                if xumo_channel['genre'][0]['value'] in xumo_groups:
                    groups_other = xumo_groups[xumo_channel['genre'][0]['value']]
                else:
                    groups_other = [ xumo_channel['genre'][0]['value'] ]
                    self.logger.info('Missing xumo category translation for: {}' \
                        .format(xumo_channel['genre'][0]['value']))
            
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
            }
            ch_list.append(channel)
        return ch_list

    @handle_json_except
    @handle_url_except
    def get_channel_uri(self, _channel_id):
        self.logger.info('{} : Getting video stream for channel {}' \
            .format(self.plugin_obj.name, _channel_id))
        
        url = 'https://valencia-app-mds.xumo.com/v2/channels/channel/{}/onnow.json' \
            .format(_channel_id)
        headers = {'Content-Type': 'application/json',
            'User-agent': constants.DEFAULT_USER_AGENT}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            prog = json.load(resp)
        prog_id = prog['id']
        print(prog_id)

        url = 'https://valencia-app-mds.xumo.com/v2/assets/asset/{}.json?f=providers' \
            .format(prog_id)
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            prog_streams = json.load(resp)

        stream_url = prog_streams['providers'][0]['source'][0]['uri']
        
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
                elif ((videoStream.stream_info.resolution[0] > bestStream.stream_info.resolution[0]) and
                      (videoStream.stream_info.resolution[1] > bestStream.stream_info.resolution[1])):
                    bestStream = videoStream

                elif ((videoStream.stream_info.resolution[0] == bestStream.stream_info.resolution[0]) and
                      (videoStream.stream_info.resolution[1] == bestStream.stream_info.resolution[1]) and
                      (videoStream.stream_info.bandwidth > bestStream.stream_info.bandwidth)):
                    bestStream = videoStream

            if bestStream is not None:
                self.logger.debug(_channel_id + " will use " +
                    str(bestStream.stream_info.resolution[0]) + "x" +
                    str(bestStream.stream_info.resolution[1]) +
                    " resolution at " + str(bestStream.stream_info.bandwidth) + "bps")

                return bestStream.absolute_uri
        else:
            self.logger.debug("No variant streams found for this station.  Assuming single stream only.")
            return stream_url
