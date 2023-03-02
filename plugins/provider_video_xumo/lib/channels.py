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

import datetime
import json
import time

import lib.common.exceptions as exceptions
from lib.plugins.plugin_channels import PluginChannels
from lib.db.db_epg_programs import DBEpgPrograms

from .translations import xumo_groups
from .epg import EPG


class Channels(PluginChannels):

    def __init__(self, _instance_obj):
        super().__init__(_instance_obj)
        self.db_programs = DBEpgPrograms(self.config_obj.data)
        self.epg = EPG(_instance_obj)

    def get_channels(self):
        channels_url = ''.join([self.plugin_obj.unc_xumo_base,
                                self.plugin_obj.unc_xumo_channels
                               .format(self.plugin_obj.geo.channelListId)])
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
                         .format(self.plugin_obj.name, len(ch_json['channel']['item']),
                                 self.instance_key))

        for channel_dict in ch_json['channel']['item']:
            hd = 0
            ch_id = str(channel_dict['guid']['value'])
            ch_callsign = channel_dict['callsign']

            thumbnail = self.plugin_obj.unc_xumo_icons \
                .format(ch_id)
            thumbnail_size = self.get_thumbnail_size(thumbnail, ch_id)

            channel = channel_dict['number']
            friendly_name = channel_dict['title']
            groups_other = None
            if 'genre' in channel_dict:
                if channel_dict['genre'][0]['value'] in xumo_groups:
                    groups_other = xumo_groups[channel_dict['genre'][0]['value']]
                else:
                    # Need to replace spaces with "_" and remove special characters.
                    self.logger.warning(
                        'Missing XUMO group translation for: {}'
                        .format(channel_dict['genre'][0]['value']))
                    groups_other = self.clean_group_name(channel_dict['genre'][0]['value'])
            vod = False
            if 'properties' in channel_dict and 'has_vod' in channel_dict['properties']:
                vod = channel_dict['properties']['has_vod'] == 'true'
            self.logger.debug("{}: Adding Channel {}"
                              .format(self.plugin_obj.name, friendly_name))
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
                'VOD': vod
            }
            ch_list.append(channel)
        return ch_list

    def get_channel_uri(self, _channel_id):
        self.logger.info(
            '{} : Getting video stream for channel {}'
            .format(self.plugin_obj.name, _channel_id))

        start_hour = datetime.datetime.utcnow().hour
        url = ''.join([self.plugin_obj.unc_xumo_base,
                       self.plugin_obj.unc_xumo_channel
                      .format(_channel_id, start_hour)])
        time_now = time.time()
        listing = self.get_uri_json_data(url)
        prog_id = None
        for prog in listing['assets']:
            if time_now < prog['timestamps']['end']:
                prog_id = prog['id']
                break

        if prog_id is None:
            if len(listing['assets']) > 0:
                prog_id = listing['assets'][len(listing['assets']) - 1]['id']
                self.logger.debug(
                    'XUMO current list of current topics are outside of current time {} using {}'
                    .format(listing['assets'], prog_id))
            else:
                self.logger.debug('XUMO program id not provided, unable to obtain URL, aborting')
                return None

        prog_dict = self.db_programs.get_program(self.plugin_obj.name, prog_id)
        update_prog_data = False
        if len(prog_dict) == 0:
            update_prog_data = True
        else:
            json_list = json.loads(prog_dict[0]['json'])
            if json_list['stream_url'] is None:
                update_prog_data = True

        if update_prog_data:
            self.logger.info(
                'XUMO program not in database so EPG is not upto date. Try refreshing EPG. prog:{} ch:{}'
                .format(prog_id, _channel_id))
            json_list = self.epg.update_program_info(prog_id)
            if json_list is None:
                self.logger.warning(
                    'Unable to find program uri stream from XUMO, aborting {}'
                    .format(prog_id))
                return None
        else:
            json_list = json.loads(prog_dict[0]['json'])

        stream_url = json_list.get('stream_url')
        if stream_url is None:
            self.logger.info('XUMO: Unable to find stream URL for program, aborting')
            return None

        return self.get_best_stream(stream_url, _channel_id)
