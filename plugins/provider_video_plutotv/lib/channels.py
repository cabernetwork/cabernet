"""
MIT License

Copyright (C) 2023 ROCKY4546
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

import re

import lib.common.exceptions as exceptions
from lib.plugins.plugin_channels import PluginChannels

from .translations import plutotv_groups


class Channels(PluginChannels):

    def __init__(self, _instance_obj):
        super().__init__(_instance_obj)

    def get_channels(self):
        channels_url = ''.join([self.plugin_obj.unc_pluto_base, '.json'])
        ch_json = self.get_uri_json_data(channels_url)
        ch_list = []
        if ch_json is None or len(ch_json) == 0:
            self.logger.warning(
                '{} HTTP Channel Request Failed for instance {}'
                .format(self.plugin_obj.name, self.instance_key))
            raise exceptions.CabernetException(
                '{} HTTP Channel Request Failed'
                .format(self.plugin_obj.name))
        self.logger.info("{}: Found {} stations on instance {}"
                         .format(self.plugin_obj.name, len(ch_json),
                                 self.instance_key))
        counter = 0
        for channel_dict in ch_json:
            if (channel_dict["isStitched"]
                    and channel_dict["visibility"] in ["everyone"]
                    and channel_dict["name"] != "Announcement"
                    and not channel_dict['onDemand']):

                hd = 0
                ch_id = str(channel_dict['_id'])
                ch_callsign = channel_dict['name']
                thumbnail = None
                thumbnail_size = None
                for tn in [self.config_obj.data[self.plugin_obj.name.lower()]['channel-thumbnail'],
                           "colorLogoPNG", "colorLogoSVG", "solidLogoSVG",
                           "solidLogoPNG", "thumbnail", "logo", "featuredImage"]:
                    if tn in channel_dict.keys():
                        thumbnail = channel_dict[tn]['path']
                        thumbnail_size = self.get_thumbnail_size(thumbnail, ch_id)
                        break

                stream_url = channel_dict['stitched']['urls'][0]['url']
                stream_url = stream_url \
                    .replace('&appName=', '&appName=web') \
                    .replace('&deviceMake=', '&deviceMake=Chrome') \
                    .replace('&deviceModel=', '&deviceModel=Chrome') \
                    .replace('&deviceType=', '&deviceType=web') \
                    .replace('&includeExtendedEvents=false', '&includeExtendedEvents=true') \
                    .replace('&sid=', '&sid=' +
                             self.config_obj.data['main']['uuid'] +
                             str(counter))
                counter += 1
                channel = channel_dict['number']
                friendly_name = channel_dict['name']
                if channel_dict['category'] in plutotv_groups:
                    groups_other = plutotv_groups[channel_dict['category']]
                else:
                    # Need to replace spaces with "_" and remove special characters.
                    self.logger.info(
                        'Missing PlutoTV group translation for: {}'
                        .format(channel_dict['category']))
                    groups_other = re.sub('[ +&*%$#@!:;,<>?]', '', channel_dict['category'])

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

    def get_channel_uri(self, _channel_id):
        self.logger.info(
            '{}: Getting video stream info for {}'
            .format(self.plugin_obj.name, _channel_id))
        ch_dict = self.db.get_channel(_channel_id, self.plugin_obj.name, self.instance_key)
        stream_url = ch_dict['json']['stream_url']
        return self.get_best_stream(stream_url, _channel_id)
