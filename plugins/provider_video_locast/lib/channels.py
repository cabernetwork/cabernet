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
from lib.common.decorators import handle_url_except
from lib.common.decorators import handle_json_except
from lib.db.db_channels import DBChannels
import lib.clients.channels.channels as channels
from lib.plugins.plugin_channels import PluginChannels

from . import constants
# from .fcc_data import FCCData


class Channels(PluginChannels):

    def __init__(self, _instance_obj):
        super().__init__(_instance_obj)
        if self.instance_obj.location.has_dma_changed:
            self.db.del_channels( 
                self.plugin_obj.name, self.instance_key)
            self.db.del_status( 
                self.plugin_obj.name, self.instance_key)

    @handle_json_except
    @handle_url_except
    def get_locast_channels(self):
        channels_url = 'https://api.locastnet.org/api/watch/epg/{}' \
            .format(self.instance_obj.location.dma)
        url_headers = {
            'Content-Type': 'application/json',
            'authorization': 'Bearer {}'.format(self.instance_obj.token),
            'User-agent': constants.DEFAULT_USER_AGENT}
        req = urllib.request.Request(channels_url, headers=url_headers)
        with urllib.request.urlopen(req) as resp:
            ch_json = json.load(resp)
        ch_list = []
        if len(ch_json) == 0:
            self.logger.warning('Locast HTTP Channel Request Failed for instance {}'.format(self.instance_key))
            raise exceptions.CabernetException('Locast HTTP Channel Request Failed')

        self.logger.info("{}: Found {} stations for DMA {} on instance {}"
            .format(self.plugin_obj.name, len(ch_json),
            str(self.instance_obj.location.dma), self.instance_key))

        for locast_channel in ch_json:
            hd = 0
            ch_id = str(locast_channel['id'])
            ch_callsign = locast_channel['name']
            thumbnail = None
            thumbnail_size = None
            if 'logoUrl' in locast_channel.keys():
                thumbnail = locast_channel['logoUrl']
            elif 'logo226Url' in locast_channel.keys():
                thumbnail = locast_channel['logo226Url']
            if thumbnail is not None:
                thumbnail_size = channels.get_thumbnail_size(thumbnail)
            try:
                if 'videoProperties' in locast_channel['listings'][0]:
                    if 'HD' in locast_channel['listings'][0]['videoProperties']:
                        hd = 1
                    else:
                        hd = 0
            except IndexError:
                pass

            try:
                assert (float(locast_channel['callSign'].split()[0]))
                channel = locast_channel['callSign'].split()[0]
                friendly_name = locast_channel['callSign'].split()[1]
                channel = {
                    'id': ch_id,
                    'enabled': True,
                    'callsign': ch_callsign,
                    'number': channel,
                    'name': friendly_name,
                    'HD': hd,
                    'group_hdtv': self.instance_obj.config_obj.data[self.config_section]['m3u-group_hdtv'],
                    'group_sdtv': self.instance_obj.config_obj.data[self.config_section]['m3u-group_sdtv'],
                    'groups_other': None,  # array list of groups/categories
                    'thumbnail': thumbnail,
                    'thumbnail_size': thumbnail_size
                }
                ch_list.append(channel)
            except ValueError:
                self.logger.warning(
                    '################### CALLSIGN ERROR Channel ignored: {} {}'
                        .format(ch_id, locast_channel['callSign']))
        return ch_list

    @handle_json_except
    @handle_url_except
    def get_channel_uri(self, _channel_id):
        self.logger.info(self.plugin_obj.name + ": Getting station info for " + _channel_id)
        stream_url = ''.join([
            'https://api.locastnet.org/api/watch/station/',
            str(_channel_id), '/',
            self.instance_obj.location.latitude, '/',
            self.instance_obj.location.longitude])
        stream_headers = {'Content-Type': 'application/json',
            'authorization': 'Bearer ' + self.instance_obj.token,
            'User-agent': constants.DEFAULT_USER_AGENT}
        req = urllib.request.Request(stream_url, headers=stream_headers)
        with urllib.request.urlopen(req) as resp:
            stream_result = json.load(resp)
        self.logger.debug("Determining best video stream for " + _channel_id + "...")
        bestStream = None

        # find the heighest stream url resolution and save it to the list
        videoUrlM3u = m3u8.load(stream_result['streamUrl'],
            headers={'authorization': 'Bearer ' + self.instance_obj.token,
                'User-agent': constants.DEFAULT_USER_AGENT})
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
            return stream_result['streamUrl']


