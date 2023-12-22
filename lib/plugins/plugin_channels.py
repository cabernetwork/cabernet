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

import collections
import datetime
import json
import logging
import io
import re
import threading
import time

import lib.m3u8 as m3u8
import lib.config.config_callbacks as config_callbacks
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

        self.ch_num_enum = self.config_obj.data[self.config_section].get('channel-start_ch_num')
        if self.ch_num_enum is None or self.ch_num_enum < 0:
            self.ch_num_enum = 0

    def terminate(self):
        """
        Removes all has a object from the object and calls any subclasses to also terminate
        Not calling inherited class at this time
        """
        self.logger = None
        self.instance_obj = None
        self.config_obj = None
        self.plugin_obj = None
        self.instance_key = None
        self.db = None
        self.config_section = None
        self.ch_num_enum = None

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
    def get_uri_json_data(self, _uri, _retries):
        header = {
            'Content-Type': 'application/json',
            'User-agent': utils.DEFAULT_USER_AGENT}
        resp = self.plugin_obj.http_session.get(_uri, headers=header, timeout=8)
        x = resp.json()
        resp.raise_for_status()
        return x

    @handle_url_except()
    def get_uri_data(self, _uri, _retries, _header=None, _data=None):
        if _header is None:
            header = {
                'User-agent': utils.DEFAULT_USER_AGENT}
        else:
            header = _header
        if _data:
            resp = self.plugin_obj.http_session.post(_uri, headers=header, data=_data, timeout=8)
        else:
            resp = self.plugin_obj.http_session.get(_uri, headers=header, timeout=8)
        x = resp.content
        return x

    @handle_url_except()
    def get_m3u8_data(self, _uri, _retries, _header=None):
        if _header is None:
            return m3u8.load(_uri,
                             headers={'User-agent': utils.DEFAULT_USER_AGENT},
                             http_session=self.plugin_obj.http_session)
        else:
            return m3u8.load(_uri,
                             headers=_header,
                             http_session=self.plugin_obj.http_session)

    def refresh_channels(self, force=False):
        self.ch_num_enum = self.config_obj.data[self.config_section].get('channel-start_ch_num')
        if self.ch_num_enum is None or self.ch_num_enum < 0:
            self.ch_num_enum = 0
        last_update = self.db.get_status(self.plugin_obj.name, self.instance_key)
        update_needed = False
        if not last_update:
            update_needed = True
        else:
            delta = datetime.datetime.now() - last_update
            if delta.total_seconds() / 3600 >= \
                    self.config_obj.data[self.config_section]['channel-update_timeout']:
                update_needed = True
        if update_needed or force:
            i = 0
            ch_dict = self.get_channels()
            while ch_dict is None and i < 2:
                i += 1
                time.sleep(0.5)
                ch_dict = self.get_channels()
            if ch_dict is None:
                self.logger.warning(
                    'Unable to retrieve channel data from {}:{}, aborting refresh'
                    .format(self.plugin_obj.name, self.instance_key))
                return False
            if 'channel-import_groups' in self.config_obj.data[self.config_section]:
                self.db.save_channel_list(
                    self.plugin_obj.name, self.instance_key, ch_dict,
                    self.config_obj.data[self.config_section]['channel-import_groups'])
            else:
                self.db.save_channel_list(self.plugin_obj.name, self.instance_key, ch_dict)
            if self.config_obj.data[self.config_section].get('channel-start_ch_num') > -1:
                config_callbacks.update_channel_num(self.config_obj, self.config_section, 'channel-start_ch_num')
            self.logger.debug(
                '{}:{} Channel update complete'
                .format(self.plugin_obj.name, self.instance_key))
        else:
            self.logger.debug(
                'Channel data still new for {} {}, not refreshing'
                .format(self.plugin_obj.name, self.instance_key))
            return False

        return True

    def clean_group_name(self, group_name):
        return re.sub('[ +&*%$#@!:;,<>?]', '', group_name)

    @handle_url_except()
    def get_thumbnail_size(self, _thumbnail, _retries, _ch_uid, ):
        thumbnail_size = (0, 0)
        if _thumbnail is None or _thumbnail == '':
            return thumbnail_size

        if _ch_uid is not None:
            ch_row = self.db.get_channel(_ch_uid, self.plugin_obj.name, self.instance_key)
            if ch_row is not None:
                if ch_row['json']['thumbnail'] == _thumbnail:
                    return ch_row['json']['thumbnail_size']

        h = {'User-Agent': utils.DEFAULT_USER_AGENT,
             'Accept': '*/*',
             'Accept-Encoding': 'identity',
             'Connection': 'Keep-Alive'
             }
        resp = self.plugin_obj.http_session.get(_thumbnail, headers=h, timeout=8)
        resp.raise_for_status()
        img_blob = resp.content
        fp = io.BytesIO(img_blob)
        sz = len(img_blob)
        try:
            thumbnail_size = get_image_size.get_image_size_from_bytesio(fp, sz)
        except get_image_size.UnknownImageFormat as e:
            self.logger.warning('{}: Thumbnail unknown format. {}'
                                .format(self.plugin_obj.name, str(e)))
            pass
        return thumbnail_size

    @handle_url_except
    def get_best_stream(self, _url, _retries, _channel_id, _referer=None):
        if self.config_obj.data[self.config_section]['player-stream_type'] == 'm3u8redirect':
            return _url

        self.logger.debug(
            '{}: Getting best video stream info for {} {}'
            .format(self.plugin_obj.name, _channel_id, _url))
        best_stream = None
        if _referer:
            header = {
                'User-agent': utils.DEFAULT_USER_AGENT,
                'Referer': _referer}
        else:
            header = {'User-agent': utils.DEFAULT_USER_AGENT}

        ch_dict = self.db.get_channel(_channel_id, self.plugin_obj.name, self.instance_key)
        ch_json = ch_dict['json']
        best_resolution = -1
        video_url_m3u = m3u8.load(
            _url, headers=header,
            http_session=self.plugin_obj.http_session)

        if not video_url_m3u:
            self.logger.notice('{}:{} Unable to obtain m3u file, aborting stream {}'
                               .format(self.plugin_obj.name, self.instance_key, _channel_id))
            return
        self.logger.debug("Found " + str(len(video_url_m3u.playlists)) + " Playlists")

        if len(video_url_m3u.playlists) > 0:
            max_bitrate = self.config_obj.data[self.config_section]['player-stream_quality']
            bitrate_list = {}
            for video_stream in video_url_m3u.playlists:
                bitrate_list[video_stream.stream_info.bandwidth] = video_stream
            bitrate_list = collections.OrderedDict(sorted(bitrate_list.items(), reverse=True))
            # bitrate is sorted from highest to lowest
            if list(bitrate_list.keys())[0] > max_bitrate:
                is_set_by_bitrate = True
            else:
                is_set_by_bitrate = False
            for bps, seg in bitrate_list.items():
                if bps < max_bitrate:
                    best_stream = seg
                    if seg.stream_info.resolution:
                        best_resolution = seg.stream_info.resolution[1]
                    break
                else:
                    best_stream = seg
                    if seg.stream_info.resolution:
                        best_resolution = seg.stream_info.resolution[1]

            for video_stream in video_url_m3u.playlists:
                if best_stream is None:
                    best_stream = video_stream
                    if video_stream.stream_info.resolution:
                        best_resolution = video_stream.stream_info.resolution[1]
                elif not video_stream.stream_info.resolution:
                    # already set earlier
                    continue
                elif ((video_stream.stream_info.resolution[0] > best_stream.stream_info.resolution[0]) and
                      (video_stream.stream_info.resolution[1] > best_stream.stream_info.resolution[1]) and
                      not is_set_by_bitrate):
                    best_stream = video_stream
                    best_resolution = video_stream.stream_info.resolution[1]
                elif ((video_stream.stream_info.resolution[0] == best_stream.stream_info.resolution[0]) and
                      (video_stream.stream_info.resolution[1] == best_stream.stream_info.resolution[1]) and
                      (video_stream.stream_info.bandwidth > best_stream.stream_info.bandwidth) and
                      not is_set_by_bitrate):
                    best_stream = video_stream
                    best_resolution = video_stream.stream_info.resolution[1]

            json_needs_updating = False
            if best_stream is not None:
                # use resolution over 720 as HD or
                # bandwidth over 3mil
                if best_resolution >= 720 and ch_json['HD'] == 0:
                    ch_json['HD'] = 1
                    json_needs_updating = True
                elif 0 < best_resolution < 720 and ch_json['HD'] == 1:
                    ch_json['HD'] = 0
                    json_needs_updating = True
                elif best_stream.stream_info.bandwidth > 3000000 and ch_json['HD'] == 0:
                    ch_json['HD'] = 1
                    json_needs_updating = True
                elif best_stream.stream_info.bandwidth <= 3000000 and ch_json['HD'] == 1:
                    ch_json['HD'] = 0
                    json_needs_updating = True

                if best_stream.stream_info.resolution is None:
                    self.logger.debug(
                        '{} will use bandwidth at {} bps'
                        .format(_channel_id, str(best_stream.stream_info.bandwidth)))
                else:
                    self.logger.notice(
                        self.plugin_obj.name + ': ' + _channel_id + " will use " +
                        str(best_stream.stream_info.resolution[0]) + "x" +
                        str(best_stream.stream_info.resolution[1]) +
                        " resolution at " + str(best_stream.stream_info.bandwidth) + "bps")

                if json_needs_updating:
                    self.db.update_channel_json(ch_json, self.plugin_obj.name, self.instance_key)
                return best_stream.absolute_uri
        else:
            self.logger.debug('{}: {} No variant streams found for this station.  Assuming single stream only.'
                              .format(self.plugin_obj.name, _channel_id))
            return _url

    def check_logger_refresh(self):
        if not self.logger.isEnabledFor(40):
            self.logger = logging.getLogger(__name__ + str(threading.get_ident()))
