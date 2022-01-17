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
import io
import os
import pathlib
import re
import shutil
import threading
import time
import urllib.request

import lib.m3u8 as m3u8
import lib.common.utils as utils
import lib.image_size.get_image_size as get_image_size
from lib.db.db_channels import DBChannels
from lib.common.decorators import handle_url_except
from lib.common.decorators import handle_json_except


class PluginChannels:

    def __init__(self, _instance_obj):
        self.logger = logging.getLogger(__name__)
        self.instance_obj = _instance_obj
        self.config_obj = self.instance_obj.config_obj
        self.plugin_obj = _instance_obj.plugin_obj
        self.instance_key = _instance_obj.instance_key
        self.db = DBChannels(self.config_obj.data)
        self.config_section = self.instance_obj.config_section
        self.ch_num_enum = self.config_obj.data[self.config_section]['channel-start_ch_num']


    def set_channel_num(self, _number):
        """
        if _number is None then will set the channel number based
        on the enum counter
        """
        if _number is None:
            ch_number = self.ch_num_enum
            self.ch_num_enum += 1
            return ch_number
        else:
            return _number


    def get_channels(self):
        """
        Interface method to override
        """
        pass

    @handle_url_except()
    @handle_json_except
    def get_uri_json_data(self, _uri):
        header = {
            'Content-Type': 'application/json',
            'User-agent': utils.DEFAULT_USER_AGENT}
        req = urllib.request.Request(_uri, headers=header)
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            return json.load(resp)

    @handle_url_except()
    def get_uri_data(self, _uri, _header=None, _data=None):
        if _header is None:
            header = {
                'User-agent': utils.DEFAULT_USER_AGENT}
        else:
            header = _header
        req = urllib.request.Request(_uri, data=_data, headers=header)
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            return resp.read()

    @handle_url_except(timeout=10.0)
    @handle_json_except
    def get_m3u8_data(self, _uri):
        return m3u8.load(_uri,
            headers={'User-agent': utils.DEFAULT_USER_AGENT})
    
    def refresh_channels(self, force=False):
        self.ch_num_enum = self.config_obj.data[self.config_section]['channel-start_ch_num']
        last_update = self.db.get_status(self.plugin_obj.name, self.instance_key)
        update_needed = False
        if not last_update:
            update_needed = True
        else:
            delta = datetime.datetime.now() - last_update
            if delta.total_seconds() / 3600 >= self.config_obj.data[
                    self.config_section]['channel-update_timeout']:
                update_needed = True
        if update_needed or force:
            i = 0
            ch_dict = self.get_channels()
            while ch_dict is None and i < 2:
                i += 1
                time.sleep(0.5)
                ch_dict = self.get_channels()
            if ch_dict == None:
                self.logger.warning('Unable to retrieve channel data from {}:{}, aborting refresh' \
                    .format(self.plugin_obj.name, self.instance_key))
                return
            if 'channel-import_groups' in self.config_obj.data[self.config_section]:
                self.db.save_channel_list(self.plugin_obj.name, self.instance_key, ch_dict, \
                    self.config_obj.data[self.config_section]['channel-import_groups'])
            else:
                self.db.save_channel_list(self.plugin_obj.name, self.instance_key, ch_dict)
            self.logger.debug('{}:{} Channel update complete' \
                .format(self.plugin_obj.name, self.instance_key))
        else:
            self.logger.debug('Channel data still new for {} {}, not refreshing' \
                .format(self.plugin_obj.name, self.instance_key))

    def clean_group_name(self, group_name):
        return re.sub('[ +&*%$#@!:;,<>?]', '', group_name)

    @handle_url_except()
    def get_thumbnail_size(self, _thumbnail, _ch_uid, ):
        thumbnail_size = (0, 0)
        if _thumbnail is None or _thumbnail == '':
            return thumbnail_size

        if _ch_uid is not None:
            ch_row = self.db.get_channel(_ch_uid, self.plugin_obj.name, self.instance_key)
            if ch_row is not None:
                ch_dict = ch_row['json']
                if ch_row['json']['thumbnail'] == _thumbnail:
                    return ch_row['json']['thumbnail_size']
        h = {'User-Agent': utils.DEFAULT_USER_AGENT,
            'Accept': '*/*',
            'Accept-Encoding': 'identity',
            'Connection': 'Keep-Alive'
            }
        req = urllib.request.Request(_thumbnail, headers=h)
        with urllib.request.urlopen(req) as resp:
            img_blob = resp.read()
            fp = io.BytesIO(img_blob)
            sz = len(img_blob)
            try:
                thumbnail_size = get_image_size.get_image_size_from_bytesio(fp, sz)
            except get_image_size.UnknownImageFormat:
                pass
        return thumbnail_size

    @handle_url_except
    def get_best_stream(self, _url, _channel_id):
        self.logger.notice('{}: Getting best video stream info for {} {}' \
            .format(self.plugin_obj.name, _channel_id, _url))
        bestStream = None
        videoUrlM3u = m3u8.load(_url,
            headers={'User-agent': utils.DEFAULT_USER_AGENT})
        self.logger.debug("Found " + str(len(videoUrlM3u.playlists)) + " Playlists")

        if len(videoUrlM3u.playlists) > 0:
            for videoStream in videoUrlM3u.playlists:
                if bestStream is None:
                    bestStream = videoStream
                elif videoStream.stream_info.resolution is None:
                    if videoStream.stream_info.bandwidth > bestStream.stream_info.bandwidth:
                        bestStream = videoStream
                elif ((videoStream.stream_info.resolution[0] > bestStream.stream_info.resolution[0]) and
                      (videoStream.stream_info.resolution[1] > bestStream.stream_info.resolution[1])):
                    bestStream = videoStream
                elif ((videoStream.stream_info.resolution[0] == bestStream.stream_info.resolution[0]) and
                      (videoStream.stream_info.resolution[1] == bestStream.stream_info.resolution[1]) and
                      (videoStream.stream_info.bandwidth > bestStream.stream_info.bandwidth)):
                    bestStream = videoStream
            if bestStream is not None:
                if bestStream.stream_info.resolution is None:
                    self.logger.debug('{} will use bandwidth at {} bps' \
                        .format(_channel_id, str(bestStream.stream_info.bandwidth)))
                else:
                    self.logger.debug(_channel_id + " will use " +
                        str(bestStream.stream_info.resolution[0]) + "x" +
                        str(bestStream.stream_info.resolution[1]) +
                        " resolution at " + str(bestStream.stream_info.bandwidth) + "bps")
                return bestStream.absolute_uri
        else:
            self.logger.debug("No variant streams found for this station.  Assuming single stream only.")
            return _url

    def check_logger_refresh(self):
        if not self.logger.isEnabledFor(40):
            self.logger = logging.getLogger(__name__+str(threading.get_ident()))
            self.logger.notice('######## CHECKING AND UPDATING LOGGER 40')
