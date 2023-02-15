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

import base64
import datetime
import hashlib
import html
import json
import re
import sys
import threading
import time
import urllib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
from multiprocessing import Queue, Process

import lib.clients.channels.channels as channels
from lib.plugins.plugin_channels import PluginChannels
from lib.db.db_epg_programs import DBEpgPrograms
from lib.common.decorators import handle_json_except
from lib.common.decorators import handle_url_except
import lib.common.exceptions as exceptions
import lib.common.utils as utils


class Channels(PluginChannels):

    def __init__(self, _instance_obj):
        super().__init__(_instance_obj)
        self.search_ch = re.compile(r'video-thumb\">\n\s*<a href=\".+watch/(.+)/\">\n\s*<img src=\"(.+)\" alt=\"(.+)\">')
        self.search_m3u8 = re.compile(r'(https?:\/\/.*?\.m3u8\?embed=true)')
        self.search2_m3u8 = re.compile(r'source:\'(https?:\/\/.*?\.m3u8)')
        self.search_enc = re.compile(r"'#'\+'v'\+'i'\+'d'\+'eo'\+'-i'\+'d'\)\.val\(\)\)\;\n.+\n(.+)")
        self.search_split = re.compile(r'(?<=\[)[^\]]+(?=\])')
        self.search_key = re.compile(r'(?<=\[)[\d+\,]+(?=\])')
        self.search_query = re.compile(r'(?<=\')\S+(?=\';}$)')
        self.search_epg_id = re.compile(r'<iframe.+\/123tv\.live\/epg\/.+html#(\d+)')
        self.ch_db_list = None

    def get_channels(self):
        is_ch_list_done = False
        channels = []
        ch_list = []

        self.ch_db_list = self.db.get_channels(self.plugin_obj.name, self.instance_key)
        if self.ch_db_list:
            is_run_scans = False
        else:
            is_run_scans = True
        
        page = 0
        while not is_ch_list_done:
            ch_list = self.get_channel_list(page)
            if ch_list is None:
                is_ch_list_done = True
                break
            channels += ch_list
            page += 1

        if len(channels) == 0:
            self.logger.warning('123TV channel list is empty from provider, not updating Cabernet')
            return
        self.logger.info("{}: Found {} stations on instance {}"
            .format(self.plugin_obj.name, len(channels), self.instance_key))
        channels = sorted(channels, key=lambda d: d['name'])
        ch_num = 1
        for ch in channels:
            ch['number'] = ch_num
            ch_num += 1

        # run channel scans if first time
        if is_run_scans:
            # this will run the scan parallel and after this method completes
            scan = threading.Thread(target=self.scan_channels)
            scan.start()
        return channels


    def scan_channels(self):
        self.ch_db_list = {}
        count = 5
        while not self.ch_db_list:
            time.sleep(1)
            self.ch_db_list = self.db.get_channels(self.plugin_obj.name, self.instance_key)
            count -= 1
            if count < 0:
                self.logger.warning('{}: Channel DB empty, aborting scan'.format(self.plugin_obj.name))
                break
            
        for ch_id in self.ch_db_list:
            ch_enabled = self.ch_db_list[ch_id][0]['enabled']
            ch_status = self.ch_db_list[ch_id][0]['json']['status']
            
            # scan channels where status is down
            # status of down means the channel has never worked
            if ch_status == 'down':
                # standard case, rescan
                url = self.get_channel_uri(ch_id)
                self.logger.debug('{}: Completed scan for channel {}'.format(self.plugin_obj.name, ch_id))
        self.logger.notice('{}: Disabled Channel Scan Completed'.format(self.plugin_obj.name))
        time.sleep(1)
        # sleep required to print out last log entry


    @handle_url_except(timeout=10.0)
    @handle_json_except
    def get_channel_uri(self, _channel_id):
        self.logger.debug('{} : Getting video stream for channel {}' \
            .format(self.plugin_obj.name, _channel_id))
        uri = self.plugin_obj.unc_tv123_base + self.plugin_obj.unc_tv123_stream_channel.format(_channel_id)
        json_needs_updating = False
        
        text = self.get_uri_data(_uri=uri).decode()

        # Check if this is a normal m3u8 url in player
        uri = self.get_m3u8_uri(text, uri)
        if uri is not None:
            self.logger.debug('{} : Regular M3U8 URL found {}'.format(self.plugin_obj.name, _channel_id))
            ch_dict = self.db.get_channel(_channel_id, self.plugin_obj.name, self.instance_key)
            ch_json = ch_dict['json']
            if ch_json['status'] == 'down' and ch_dict['enabled']:
                ch_json['status'] = 'up'
                self.db.update_channel_json(ch_json, self.plugin_obj.name, self.instance_key)
            return uri

        # Check if this url is hidden and encrypted
        uri = self.get_enc_uri(text, _channel_id)
        if uri is None:
            self.logger.info('{} : Unable to find encrypted URL stream, aborting {}'.format(self.plugin_obj.name, _channel_id))
            return

        # it takes 2 http pulls to obtain the m3u8 url
        stream_url = self.get_enc_uri2(uri)
        if stream_url is None:
            self.logger.info('{} : Unable to find m3u8 URL from encrypted URL, aborting'.format(self.plugin_obj.name))
            return

        header = {
            'User-agent': utils.DEFAULT_USER_AGENT,
            'Referer': self.plugin_obj.unc_tv123_base }

        ch_dict = self.db.get_channel(_channel_id, self.plugin_obj.name, self.instance_key)
        ch_json = ch_dict['json']
        text = self.get_uri_data(stream_url, _header=header)
        if text is None:
            # for possible PSP channels that are down, set the channel to disabled
            # if channel has never been up
            if ch_json['status'] == 'down' and ch_dict['enabled']:
                ch_dict['enabled'] = False
                ch_json['enabled'] = False
                self.db.update_channel(ch_dict)
                self.db.update_channel_json(ch_json, self.plugin_obj.name, self.instance_key)
            self.logger.info('{}: Unable to open m3u8 enc stream URL, possible P2P issue, aborting {}'
                .format(self.plugin_obj.name, ch_dict['uid']))
            return
        if not (ch_json['status'] == 'up' and ch_dict['enabled']):
            if ch_json['status'] == 'down':
                json_needs_updating = True
                ch_json['status'] = 'up'
            if not ch_dict['enabled']:
                ch_dict['enabled'] = True
                ch_json['enabled'] = True
                json_needs_updating = True
                self.db.update_channel(ch_dict)
                self.logger.info('{} Enabling channel {}'.format(self.plugin_obj.name, ch_dict['uid']))
        
        videoUrlM3u = self.get_m3u8_data(stream_url, _header=header)
        self.logger.debug('Found {} Playlist(s)'.format(str(len(videoUrlM3u.playlists))))
        
        bestStream = None
        bestResolution = -1
        if len(videoUrlM3u.playlists) > 0:
            for videoStream in videoUrlM3u.playlists:
                if bestStream is None:
                    bestStream = videoStream
                elif ((videoStream.stream_info.resolution[0] > bestStream.stream_info.resolution[0]) and
                      (videoStream.stream_info.resolution[1] > bestStream.stream_info.resolution[1])):
                    bestResolution = videoStream.stream_info.resolution[1]
                    bestStream = videoStream
                elif ((videoStream.stream_info.resolution[0] == bestStream.stream_info.resolution[0]) and
                      (videoStream.stream_info.resolution[1] == bestStream.stream_info.resolution[1]) and
                      (videoStream.stream_info.bandwidth > bestStream.stream_info.bandwidth)):
                    bestResolution = videoStream.stream_info.resolution[1]
                    bestStream = videoStream

            if bestStream is not None:
                if bestResolution >= 720 and ch_json['HD'] == 0:
                    ch_json['HD'] = 1
                    json_needs_updating = True
                elif bestResolution < 720 and ch_json['HD'] == 1:
                    ch_json['HD'] = 0
                    json_needs_updating = True
                
                self.logger.info('{} will use {}x{} resolution at {}bps' \
                    .format(_channel_id, str(bestStream.stream_info.resolution[0]), \
                    str(bestStream.stream_info.resolution[1]), str(bestStream.stream_info.bandwidth)))
                m3u8_uri = bestStream.absolute_uri
            else:
                m3u8_uri = None
        else:
            self.logger.debug('No variant streams found for this station.  Assuming single stream only.')
            m3u8_uri = stream_url

        if json_needs_updating:
            self.db.update_channel_json(ch_json, self.plugin_obj.name, self.instance_key)
        return m3u8_uri

    def get_channel_list(self, page_num):

        ch_list = []
        data = { 'action': self.plugin_obj.unc_tv123_wp_more_ch_cmd,
                 'chn_id': '1',
                 'page_num': page_num
               }

        text = self.get_uri_data(_uri=self.plugin_obj.unc_tv123_base+self.plugin_obj.unc_tv123_additional_channels, 
            _data=urllib.parse.urlencode(data).encode()).decode()
        if text == "NO_MORE":
            return None

        match_list = re.findall(self.search_ch, text)
        for m in match_list:
            if len(m) != 3:
                self.logger.warning('get_channel_list - 123TV channel extraction failed.  Updates to extraction procedure needs updating')
                return None

            ch_db_data = self.ch_db_list.get(m[0])
            if ch_db_data is not None:
                enabled = ch_db_data[0]['enabled']
                hd = ch_db_data[0]['json']['HD']
                thumb = ch_db_data[0]['thumbnail']
                thumb_size = ch_db_data[0]['thumbnail_size']
                epg_id = ch_db_data[0]['json']['epg_id']
            else:
                enabled = True
                hd = 1
                thumb = m[1]
                thumb_size = self.get_thumbnail_size(m[1], m[0])
                epg_id = self.get_epg_id(m[0])
            
            name = html.unescape(m[2])
            if name.lower().startswith('the '):
                name = name[4:]
            
            channel = {
                'id': m[0],
                'enabled': enabled,
                'callsign': m[0],
                'number': 0,
                'name': name,
                'HD': hd,
                'group_hdtv': None,
                'group_sdtv': None,
                'groups_other': None,
                'thumbnail': thumb,
                'thumbnail_size': thumb_size,
                'VOD': False,
                'Header': { 'User-agent': utils.DEFAULT_USER_AGENT,
                    'Referer': self.plugin_obj.unc_tv123_referer},
                'status': 'down',
                'epg_id': epg_id
            }
            ch_list.append(channel)
            self.logger.debug('{} Added Channel {}:{}'.format(self.plugin_obj.name, m[0], name))
        return ch_list

    @handle_url_except(timeout=10.0)
    def get_epg_id(self, _ch_id):
        uri = self.plugin_obj.unc_tv123_base + self.plugin_obj.unc_tv123_stream_channel.format(_ch_id)
        html = self.get_uri_data(_uri=uri).decode()
        m = re.search(self.search_epg_id, html)
        if m is None:
            return None
        return m.group(1)

    def get_m3u8_uri(self, html, referer):
        """
        Used when 123tv uses the m3u8 link directly on the player
        """

        m = re.search(self.search_m3u8, html)
        if m is not None:
            m3u8_url = m.group(1)
            header = {
                'User-agent': utils.DEFAULT_USER_AGENT,
                'Referer': referer}
            text = self.get_uri_data(_uri=m3u8_url, _header=header).decode()
            m2 = re.search(self.search2_m3u8, text)
            if m2 is not None:
                m3u8_url2 = m2.group(1)

                referer_url = self.plugin_obj.unc_tv123_referer
                header = {
                    'User-agent': utils.DEFAULT_USER_AGENT,
                    'Referer': referer_url}
                text = self.get_uri_data(m3u8_url2, _header=header)
                if text is None:
                    return
                text = text.decode()
                if text.startswith('#EXTM3U'):
                    return m3u8_url2
            else:
                self.logger.warning('{} : Unable to find m3u8 url. This should not happen...'.format(self.plugin_obj.name))
        return

    @handle_json_except
    def get_enc_uri(self, text, _channel_id):
        """
        Used when 123tv uses encryption strings within javascript.
        resulting in a m3u8 url that produces json data
        """
        m = re.search(self.search_enc, text)
        try:
            enc_text, enc_key, enc_query_str = m.group(1).split('};')
        except ValueError:
            self.logger.debug('{} : VALUE ERROR no encryption keys were found, aborting {}'.format(self.plugin_obj.name, _channel_id))
            return

        m2 = re.search(self.search_split, enc_text)
        if not m2:
            self.logger.debug('{} : Unable to split the encrypted text string, aborting {}'.format(self.plugin_obj.name, _channel_id))
            return
            
        b64_str = ''.join(m2.group().replace("'",'').split(','))
        json_dict = json.loads(base64.b64decode(b64_str))
        
        key = ''
        key_list = ','.join(re.findall(self.search_key, enc_key)).split(',')
        for chr_num in key_list:
            key = chr(int(chr_num)) + key

        json_dict['iterations'] = 999 if json_dict['iterations'] <= 0 else json_dict['iterations']
        key_data = hashlib.pbkdf2_hmac('sha512', key.encode('utf8'), bytes.fromhex(json_dict['salt']),
                                      json_dict['iterations'], dklen=256 // 8)

        cipher = Cipher(algorithms.AES(key_data), modes.CBC(bytes.fromhex(json_dict['iv'])), default_backend())
        decryptor = cipher.decryptor()
        ciphertext = base64.b64decode(json_dict['ciphertext'])
        m3u8_uri = b''
        for i in range(0, len(ciphertext), 16):
            m3u8_uri += decryptor.update(ciphertext[i: i + 16])

        unpadder = padding.PKCS7(128).unpadder()
        new_url = (unpadder.update(m3u8_uri) + unpadder.finalize()).decode('utf8')
        str_query = re.search(self.search_query, enc_query_str)
        if str_query:
            new_url += str_query.group()
        return new_url

    @handle_json_except
    def get_enc_uri2(self, uri):
    
        header = {
            'User-agent': utils.DEFAULT_USER_AGENT,
            'Referer': self.plugin_obj.unc_tv123_base }

        text = self.get_uri_data(uri, _header=header)
        if text is None:
            return
        json_dict = json.loads(text)
        return json_dict[0]['file']
