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
import re
import time
import urllib.request
import urllib.parse

import lib.common.utils as utils
import lib.common.exceptions as exceptions
from lib.common.decorators import handle_url_except
from lib.common.decorators import handle_json_except
from lib.db.db_channels import DBChannels
from lib.plugins.plugin_channels import PluginChannels

from .translations import ustvgo_groups

class Channels(PluginChannels):

    def __init__(self, _instance_obj):
        super().__init__(_instance_obj)

    def get_channels(self):
    
        ch_json = self.get_uri_json_data(self.plugin_obj.unc_ustvgo_channels)
        ch_list = []
        if ch_json is None or len(ch_json) == 0:
            self.logger.warning('{} HTTP Channel Request Failed for instance {}' \
                .format(self.plugin_obj.name, self.instance_key))
            raise exceptions.CabernetException('{} HTTP Channel Request Failed' \
                .format(self.plugin_obj.name))
        self.logger.info("{}: Found {} stations on instance {}"
            .format(self.plugin_obj.name, len(ch_json),
            self.instance_key))
        for channel_dict in ch_json:
            hd = 0
            ch_id = str(channel_dict['channel']['sourceId'])
            ch_callsign = channel_dict['channel']['name']
            thumbnail = None
            thumbnail_size = None
            ch_number = self.set_channel_num(None)
            friendly_name = channel_dict['channel']['fullName']
            groups_other = None            
            channel = {
                'id': ch_id,
                'enabled': True,
                'callsign': ch_callsign,
                'number': ch_number,
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
    
    def get_channel_uri(self, _channel_id):
        ch_dict = self.db.get_channel(_channel_id, self.plugin_obj.name, self.instance_key)
        callsign = ch_dict['json']['callsign']
        stream_url = self.get_ustvgo_stream(callsign)
        return self.get_best_stream(stream_url, _channel_id)

    def get_ustvgo_stream(self, _callsign):
        data = urllib.parse.urlencode({'stream': _callsign}).encode()    
        return self.get_uri_data(self.plugin_obj.unc_ustvgo_stream, _data=data).decode('utf-8')

