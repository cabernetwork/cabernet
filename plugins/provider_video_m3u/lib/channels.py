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

import pathlib
import re
import urllib.request
import urllib.parse

import lib.m3u8 as m3u8
import lib.common.exceptions as exceptions
from lib.plugins.plugin_channels import PluginChannels
from lib.common.tmp_mgmt import TMPMgmt
from lib.db.db_scheduler import DBScheduler

TMP_FOLDERNAME = 'm3u'


class Channels(PluginChannels):

    def __init__(self, _instance_obj):
        super().__init__(_instance_obj)
        self.tmp_mgmt = TMPMgmt(self.config_obj.data)
        self.filter_dict = self.compile_m3u_filter(
            self.config_obj.data[self.config_section]['channel-m3u_filter'])
        self.url_chars = re.compile(r'[^-._~0-9a-zA-z]')

    def compile_m3u_filter(self, _str):
        """
        _dict contains a
        """
        if _str is None:
            return None
        nv_dict = {}
        split_nv = re.compile(r'([^ =]+)=([^,]+),*')
        nv_pairs = re.findall(split_nv, _str)
        for nv in nv_pairs:
            nv_dict[nv[0]] = re.compile(nv[1])
        return nv_dict

    def get_channels(self):
        global TMP_FOLDERNAME
        if self.config_obj.data[self.config_section]['channel-m3u_file'] is None:
            raise exceptions.CabernetException(
                '{}:{} M3U File config not set, unable to get channel list'
                .format(self.plugin_obj.name, self.instance_key))
        url = self.config_obj.data[self.config_section]['channel-m3u_file']
        file_type = self.detect_filetype(url)
        try:
            dn_filename = self.tmp_mgmt.download_file(url, TMP_FOLDERNAME, None, file_type)
            if dn_filename is None:
                raise exceptions.CabernetException(
                    '{} M3U Channel Request Failed for instance {}'
                    .format(self.plugin_obj.name, self.instance_key))
            m3u_file = self.extract_file(dn_filename, file_type)
            m3u8_obj = m3u8.load(str(m3u_file))

            ch_list = []
            if len(m3u8_obj.segments) == 0:
                raise exceptions.CabernetException(
                    '{} M3U Channel Request Failed for instance {}'
                    .format(self.plugin_obj.name, self.instance_key))
            self.logger.info("{}: Found {} stations on instance {}"
                             .format(self.plugin_obj.name, len(m3u8_obj.segments),
                                     self.instance_key))
            for seg in m3u8_obj.segments:
                if self.is_m3u_filtered(seg):
                    continue
                ch_number = None
                if 'tvg-num' in seg.additional_props:
                    ch_number = seg.additional_props['tvg-num']
                elif 'tvg-chno' in seg.additional_props:
                    ch_number = seg.additional_props['tvg-chno']
                else:
                    ch_number = self.set_channel_num(ch_number)

                if 'channelID' in seg.additional_props and \
                        len(seg.additional_props['channelID']) != 0:
                    ch_id = seg.additional_props['channelID']
                elif 'tvg-id' in seg.additional_props and \
                        len(seg.additional_props['tvg-id']) != 0:
                    ch_id = seg.additional_props['tvg-id']
                elif ch_number is not None:
                    ch_id = str(ch_number)
                else:
                    ch_id = None
                ch_id = re.sub(self.url_chars, '_', ch_id)

                if 'tvg-logo' in seg.additional_props and seg.additional_props['tvg-logo'] != '':
                    thumbnail = seg.additional_props['tvg-logo']
                    if self.config_obj.data[self.config_section]['player-decode_url']:
                        thumbnail = urllib.parse.unquote(thumbnail)
                    thumbnail_size = self.get_thumbnail_size(thumbnail, ch_id)
                else:
                    thumbnail = None
                    thumbnail_size = None
                stream_url = seg.absolute_uri

                if 'group-title' in seg.additional_props:
                    groups_other = seg.additional_props['group-title']
                else:
                    groups_other = None

                ch_callsign = seg.title
                channel = {
                    'id': ch_id,
                    'enabled': True,
                    'callsign': ch_callsign,
                    'number': ch_number,
                    'name': ch_callsign,
                    'HD': 0,
                    'group_hdtv': None,
                    'group_sdtv': None,
                    'groups_other': groups_other,
                    'thumbnail': thumbnail,
                    'thumbnail_size': thumbnail_size,
                    'stream_url': stream_url
                }
                ch_list.append(channel)

            sched_db = DBScheduler(self.config_obj.data)
            active = sched_db.get_num_active()
            if active < 2:
                self.tmp_mgmt.cleanup_tmp(TMP_FOLDERNAME)
            return ch_list
        except exceptions.CabernetException:
            self.tmp_mgmt.cleanup_tmp(TMP_FOLDERNAME)
            raise

    def get_channel_uri(self, _channel_id):
        ch_dict = self.db.get_channel(_channel_id, self.plugin_obj.name, self.instance_key)
        if self.config_obj.data[self.config_section]['player-decode_url']:
            stream_url = urllib.parse.unquote(ch_dict['json']['stream_url'])
        else:
            stream_url = ch_dict['json']['stream_url']
        return self.get_best_stream(stream_url, _channel_id)

    def detect_filetype(self, _filename):
        file_type = self.config_obj.data[self.config_section]['channel-m3u_file_type']
        if file_type == 'autodetect':
            extension = pathlib.Path(_filename).suffix
            if extension == '.gz':
                file_type = '.gz'
            elif extension == '.zip':
                file_type = '.zip'
            elif extension == '.m3u':
                file_type = '.m3u'
            elif extension == '.m3u8':
                file_type = '.m3u'
            else:
                raise exceptions.CabernetException(
                    '{}:{} M3U File unknown File Type.  Set the M3U File Type in config.'
                    .format(self.plugin_obj.name, self.instance_key))
        elif file_type == 'gzip':
            file_type = '.gz'
        elif file_type == 'zip':
            file_type = '.zip'
        elif file_type == 'm3u':
            file_type = '.m3u'
        elif file_type == 'm3u8':
            file_type = '.m3u'
        else:
            raise exceptions.CabernetException(
                '{}:{} M3U File unknown File Type in config.'
                .format(self.plugin_obj.name, self.instance_key))
        return file_type

    def extract_file(self, _filename, _file_type):
        if _file_type == '.zip':
            return self.tmp_mgmt.extract_zip(_filename)
        elif _file_type == '.gz':
            return self.tmp_mgmt.extract_gzip(_filename)
        elif _file_type == '.m3u':
            return _filename
        else:
            raise exceptions.CabernetException(
                '{}:{} M3U File unknown File Type {}'
                .format(self.plugin_obj.name, self.instance_key, _file_type))

    def is_m3u_filtered(self, _segment):
        """
        format: name=regexvalue, Note: regex string cannot have a comma in it...
        """
        all_matched = True
        if self.filter_dict is not None:
            for filtered in self.filter_dict:
                if filtered in _segment.additional_props:
                    if not bool(re.search(self.filter_dict[filtered], _segment.additional_props[filtered])):
                        all_matched = False
                        break
                else:
                    all_matched = False
                    break
        return not all_matched
