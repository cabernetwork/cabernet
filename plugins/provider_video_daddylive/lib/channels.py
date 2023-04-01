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

import html
import importlib
import importlib.resources
import json
import re

from lib.plugins.plugin_channels import PluginChannels
from lib.common.decorators import handle_json_except
from lib.common.decorators import handle_url_except
import lib.common.utils as utils
from ..lib import daddylive
from .. import resources

class Channels(PluginChannels):

    def __init__(self, _instance_obj):
        super().__init__(_instance_obj)

        self.search_url = re.compile(b'iframe src=\"(.*?)\" width')
        self.search_m3u8 = re.compile(b'source:\'(.*?)\'')
        self.search_ch = re.compile(r'div class="grid-item">'
                                    + r'<a href=\"(\D+(\d+).php.*?)\" target.*?<strong>(.*?)</strong>')
        self.ch_db_list = None

    def get_channels(self):
        self.ch_db_list = self.db.get_channels(self.plugin_obj.name, self.instance_key)

        ch_list = self.get_channel_list()
        if len(ch_list) == 0:
            self.logger.warning('DaddyLive channel list is empty from provider, not updating Cabernet')
            return
        self.logger.info("{}: Found {} stations on instance {}"
                         .format(self.plugin_obj.name, len(ch_list), self.instance_key))
        ch_list = sorted(ch_list, key=lambda d: d['name'])
        ch_num = 1
        for ch in ch_list:
            ch['number'] = ch_num
            ch_num += 1
        return ch_list

    @handle_url_except(timeout=10.0)
    @handle_json_except
    def get_channel_ref(self, _channel_id):
        """
        gets the referer required to obtain the ts or stream files from server
        """
        text = self.get_uri_data(self.plugin_obj.unc_daddylive_base +
                                 self.plugin_obj.unc_daddylive_stream.format(_channel_id))
        m = re.search(self.search_url, text)
        if not m:
            # unable to obtain the url, abort
            self.logger.info('{}: {} Unable to obtain url, aborting'
                             .format(self.plugin_obj.name, _channel_id))
            return
        return m[1].decode('utf8')

    @handle_url_except(timeout=10.0)
    @handle_json_except
    def get_channel_uri(self, _channel_id):
        json_needs_updating = False
        ch_url = self.get_channel_ref(_channel_id)
        if not ch_url:
            return

        header = {
            'User-agent': utils.DEFAULT_USER_AGENT,
            'Referer': self.plugin_obj.unc_daddylive_base + self.plugin_obj.unc_daddylive_stream.format(_channel_id)}

        text = self.get_uri_data(ch_url, _header=header)
        m = re.search(self.search_m3u8, text)
        if not m:
            # unable to obtain the url, abort
            self.logger.notice('{}: {} Unable to obtain m3u8, aborting'
                               .format(self.plugin_obj.name, _channel_id))
            return
        stream_url = m[1].decode('utf8')

        if self.config_obj.data[self.config_section]['player-stream_type'] == 'm3u8redirect':
            self.logger.warning('Stream Type of m3u8redirect not available with this plugin')
            return stream_url

        m3u8_uri = self.get_best_stream(stream_url, _channel_id, ch_url)
        if not m3u8_uri:
            return stream_url
        return m3u8_uri

    def get_channel_list(self):
        ch_list = []
        results = []

        # first get the list of channels to get from the epg plugin
        tvg_list = self.get_tvg_reference()
        epg_plugins = {u['plugin']: u for u in tvg_list}.keys()
        for plugin in epg_plugins:
            zones = {u['zone']: u for u in tvg_list if u['plugin'] == plugin}.keys()
            for zone in zones:
                ch_ids = [n['id'] for n in tvg_list if n['zone'] == zone]
                chs = self.plugin_obj.plugins[plugin].plugin_obj \
                    .get_channel_list_ext(zone, ch_ids)
                if chs is None:
                    return
                ch_list.extend(chs)

        # Get the list of channels daddylive provides by channel name
        uri = self.plugin_obj.unc_daddylive_base + self.plugin_obj.unc_daddylive_channels
        text = self.get_uri_data(uri).decode()
        if text is None:
            return
        text = text.replace('\n', ' ')
        match_list = re.findall(self.search_ch, text)
        # url, id, name
        for m in match_list:
            if len(m) != 3:
                self.logger.warning(
                    'get_channel_list - DaddyLive channel extraction failed. Extraction procedure needs updating')
                return None
            uid = m[1]
            name = html.unescape(m[2])
            if name.lower().startswith('the '):
                name = name[4:]
            group = None
            ch = [d for d in tvg_list if d['name'] == name]
            if len(ch):
                tvg_id = ch[0]['id']
                ch = [d for d in ch_list if d['id'] == tvg_id]

                if len(ch):
                    ch = ch[0]
                    ch_db_data = self.ch_db_list.get(uid)
                    if ch_db_data is not None:
                        ch['enabled'] = ch_db_data[0]['enabled']
                        ch['id'] = ch_db_data[0]['uid']
                        ch['name'] = ch_db_data[0]['json']['name']
                        ch['HD'] = ch_db_data[0]['json']['HD']
                        if ch_db_data[0]['json']['thumbnail'] == ch['thumbnail']:
                            thumb = ch_db_data[0]['json']['thumbnail']
                            thumb_size = ch_db_data[0]['json']['thumbnail_size']
                        else:
                            thumb = ch['thumbnail']
                            thumb_size = self.get_thumbnail_size(thumb, uid)
                        ch['thumbnail'] = thumb
                        ch['thumbnail_size'] = thumb_size
                        ch['ref_url'] = ch_db_data[0]['json']['ref_url']
                        ch['Header'] = ch_db_data[0]['json']['Header']
                        ch['use_date_on_m3u8_key'] = False
                    else:
                        ch['id'] = uid
                        ch['name'] = name
                        ch['thumbnail_size'] = self.get_thumbnail_size(ch['thumbnail'], uid)

                        ref_url = self.get_channel_ref(uid)
                        if not ref_url:
                            self.logger.notice('{} BAD CHANNEL found {}:{}'
                                               .format(self.plugin_obj.name, uid, name))
                            header = None
                        else:
                            header = {'User-agent': utils.DEFAULT_USER_AGENT,
                                      'Referer': ref_url}
                        ch['Header'] = header
                        ch['ref_url'] = ref_url
                        ch['use_date_on_m3u8_key'] = False
                        self.logger.debug('{} New Channel Added {}:{}'.format(self.plugin_obj.name, uid, name))

                    group = [n.get('group') for n in tvg_list if n['name'] == ch['name']]
                    if len(group):
                        group = group[0]
                    ch['groups_other'] = group
                    results.append(ch)
                    ch['found'] = True
                    continue

            ch_db_data = self.ch_db_list.get(uid)
            if ch_db_data is not None:
                enabled = ch_db_data[0]['enabled']
                hd = ch_db_data[0]['json']['HD']
                thumb = ch_db_data[0]['json']['thumbnail']
                thumb_size = ch_db_data[0]['json']['thumbnail_size']
                ref_url = self.get_channel_ref(uid)
                self.logger.debug('{} Updating Channel {}:{}'.format(self.plugin_obj.name, uid, name))
            else:
                self.logger.debug('{} New Channel Added {}:{}'.format(self.plugin_obj.name, uid, name))
                enabled = True
                hd = 0
                thumb = None
                thumb_size = None
                ref_url = self.get_channel_ref(uid)

            if not ref_url:
                self.logger.notice('{} BAD CHANNEL found {}:{}'
                                   .format(self.plugin_obj.name, uid, name))
                header = None
            else:
                header = {'User-agent': utils.DEFAULT_USER_AGENT,
                          'Referer': ref_url}

            channel = {
                'id': uid,
                'enabled': enabled,
                'callsign': uid,
                'number': 0,
                'name': name,
                'HD': hd,
                'group_hdtv': None,
                'group_sdtv': None,
                'groups_other': None,
                'thumbnail': thumb,
                'thumbnail_size': thumb_size,
                'VOD': False,
                'Header': header,
                'ref_url': ref_url,
                'use_date_on_m3u8_key': False,
            }
            results.append(channel)

        found_tvg_list = [u for u in ch_list if u.get('found') is None]
        for ch in found_tvg_list:
            self.logger.warning(
                '{} Channel {} {} from channel_list.json not found on providers site'.format(self.plugin_obj.name,
                                                                                             ch['id'], ch['name']))
        found_tvg_list = [u for u in ch_list if u.get('found') is not None]
        for ch in found_tvg_list:
            del ch['found']

        return results

    def get_tvg_reference(self):
        """
        Returns a list of channels with zone and channel id info
        This is sorted so we can get all channels from each zone together
        """
        if self.config_obj.data[self.plugin_obj.name.lower()]['epg-plugin'] == 'ALL':
            ch_list = json.loads(
                importlib.resources.read_text(resources, resource='channel_list.json'))
            ch_list = sorted(ch_list, key=lambda d: d['zone'])
            return ch_list
        else:
            return []
