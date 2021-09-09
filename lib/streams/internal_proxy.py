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
import errno
import http
import re
import urllib.request
import time
from collections import OrderedDict
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

import lib.m3u8 as m3u8
from lib.streams.video import Video
from lib.db.db_config_defn import DBConfigDefn
from lib.db.db_channels import DBChannels
from lib.common.atsc import ATSCMsg
from .stream import Stream
from .pts_validation import PTSValidation


class InternalProxy(Stream):

    def __init__(self, _plugins, _hdhr_queue):
        self.last_refresh = None
        self.channel_dict = None
        self.write_buffer = None
        self.file_filter = None
        self.pts_validation = None
        self.duration = 6
        self.last_ts_index = -1
        super().__init__(_plugins, _hdhr_queue)
        self.config = self.plugins.config_obj.data
        self.db_configdefn = DBConfigDefn(self.config)
        self.db_channels = DBChannels(self.config)
        self.video = Video(self.config)
        self.atsc_msg = ATSCMsg()
        self.initialized_psi = False

    def stream(self, _channel_dict, _write_buffer):
        """
        Processes m3u8 interface without using ffmpeg
        """
        self.config = self.db_configdefn.get_config()
        self.channel_dict = _channel_dict
        self.write_buffer = _write_buffer
        duration = 6
        play_queue_dict = OrderedDict()
        self.last_refresh = time.time()
        stream_uri = self.get_stream_uri(_channel_dict)
        if not stream_uri:
            self.logger.warning('Unknown Channel')
            return
        self.logger.debug('M3U8: {}'.format(stream_uri))
        self.file_filter = None
        if self.config[_channel_dict['namespace'].lower()]['player-enable_url_filter']:
            stream_filter = self.config[_channel_dict['namespace'].lower()]['player-url_filter']
            if stream_filter is not None:
                self.file_filter = re.compile(stream_filter)
            else:
                self.logger.warning('[{}]][player-enable_url_filter]'
                    ' enabled but [player-url_filter] not set'
                    .format(_channel_dict['namespace'].lower()))
        if self.config[_channel_dict['namespace'].lower()]['player-enable_pts_filter']:
            self.pts_validation = PTSValidation(self.config, self.channel_dict)

        while True:
            try:
                added = 0
                removed = 0
                i = 3
                while i > 0:
                    try:
                        playlist = m3u8.load(stream_uri)
                        break
                    except urllib.error.HTTPError as e:
                        self.logger.info('M3U8 Exception caught, retrying: {}'.format(e))
                        time.sleep(1.5)
                        i -= 1
                if i < 1:
                    break
                removed += self.remove_from_stream_queue(playlist, play_queue_dict)
                added += self.add_to_stream_queue(playlist, play_queue_dict)
                if added == 0 and duration > 0:
                    time.sleep(duration * 0.3)
                elif self.plugins.plugins[_channel_dict['namespace']].plugin_obj \
                        .is_time_to_refresh_ext(self.last_refresh, _channel_dict['instance']):
                    stream_uri = self.get_stream_uri(_channel_dict)
                    self.logger.debug('M3U8: {}'.format(stream_uri))
                    self.last_refresh = time.time()
                self.play_queue(play_queue_dict)
            except IOError as e:
                # Check we hit a broken pipe when trying to write back to the client
                if e.errno in [errno.EPIPE, errno.ECONNABORTED, errno.ECONNRESET, errno.ECONNREFUSED]:
                    # Normal process.  Client request end of stream
                    self.logger.info('2. Connection dropped by end device {}'.format(e))
                    break
                else:
                    self.logger.error('{}{}'.format(
                        '3 UNEXPECTED EXCEPTION=', e))
                    raise


    def add_to_stream_queue(self, _playlist, _play_queue_dict):
        total_added = 0
        if _playlist.keys != [None]:
            keys = [{"uri": key.absolute_uri, "method": key.method, "iv": key.iv} \
                for key in _playlist.keys if key]
        else:
            keys = [None for i in range(0, len(_playlist.segments))]
            
        for m3u8_segment, key in zip(_playlist.segments, keys):
            uri = m3u8_segment.absolute_uri
            if uri not in _play_queue_dict.keys():
                played = False
                filtered = False
                if self.file_filter is not None:
                    m = self.file_filter.match(uri)
                    if m:
                        filtered = True
                _play_queue_dict[uri] = {
                    'uid': self.channel_dict['uid'],
                    'played': played,
                    'filtered': filtered,
                    'duration': m3u8_segment.duration,
                    'key': key
                }
                self.logger.debug(f"Added {uri} to play queue")
                total_added += 1
        return total_added

    def remove_from_stream_queue(self, _playlist, _play_queue_dict):
        total_removed = 0
        for segment_key in list(_play_queue_dict.keys()):
            is_found = False
            for segment_m3u8 in _playlist.segments:
                uri = segment_m3u8.absolute_uri
                if segment_key == uri:
                    is_found = True
                    break
            if not is_found:
                del _play_queue_dict[segment_key]
                total_removed += 1
                self.logger.debug(f"Removed {segment_key} from play queue")
                continue
            else:
                break
        return total_removed

    def play_queue(self, _play_queue_dict):
        for uri, data in _play_queue_dict.items():
            if data['filtered'] and not data['played']:
                if self.channel_dict['atsc'] is not None:
                    self.write_buffer.write(
                        self.atsc_msg.format_video_packets(self.channel_dict['atsc']))
                else:
                    self.logger.info(''.join([
                        'No ATSC msg available during filtered content, ',
                        'recommend running this channel again to catch the ATSC msg.']))
                    self.write_buffer.write(
                        self.atsc_msg.format_video_packets())
                time.sleep(0.3 * self.duration)
                data['played'] = True
            elif not data['played']:
                data['played'] = True
                start_download = datetime.datetime.utcnow()
                self.video.data = None
                count = 5
                while count > 0:
                    count -= 1
                    try:
                        req = urllib.request.Request(uri)
                        with urllib.request.urlopen(req) as resp:
                            self.video.data = resp.read()
                            break
                    except http.client.IncompleteRead as e:
                        self.logger.info('Provider gave partial stream, trying again. {}'
                            .format(e, len(e.partial)))
                        self.video.data = e.partial
                        time.sleep(1.5)
                    except urllib.error.URLError as e:
                        self.logger.info('HTTP Error, trying again. {}'.format(e))
                if not self.video.data:
                    self.logger.warning(f"Segment {uri} not available. Skipping..")
                    continue

                if data["key"]:
                    i = 3
                    while i > 0:
                        try:
                            if data["key"]["uri"]:
                                key_data = None
                                req = urllib.request.Request(data["key"]["uri"])
                                with urllib.request.urlopen(req) as resp:
                                    key_data = resp.read()
                                        
                                if data["key"]["iv"].startswith('0x'):
                                    iv = bytearray.fromhex(data["key"]["iv"][2:])
                                else:
                                    iv = bytearray.fromhex(data["key"]["iv"])
                                cipher = Cipher(algorithms.AES(key_data), modes.CBC(iv), default_backend())
                                decryptor = cipher.decryptor()
                                self.video.data = decryptor.update(self.video.data)
                            break
                        except urllib.error.URLError as e:
                            self.logger.info('Key Exception caught, retrying: {}'.format(e))
                            i -= 1
                            time.sleep(1)
                if not self.is_pts_valid():
                    continue
                
                chunk_updated = self.atsc_msg.update_sdt_names(self.video.data[:80], 
                    self.channel_dict['namespace'].encode(),
                    self.set_service_name(self.channel_dict).encode())
                if self.channel_dict['atsc'] is None:
                    self.initialized_psi = True
                    p_list = self.atsc_msg.extract_psip(self.video.data)
                    if len(p_list) != 0:
                        self.channel_dict['atsc'] = p_list
                        self.db_channels.update_channel_atsc(
                            self.channel_dict)
                elif not self.initialized_psi:
                    self.initialized_psi = True
                    p_list = self.atsc_msg.extract_psip(self.video.data)
                    for i in range(len(p_list)):
                        if p_list[i][4:] != self.channel_dict['atsc'][i][4:]:
                            self.channel_dict['atsc'] = p_list
                            self.db_channels.update_channel_atsc(
                                self.channel_dict)
                            break
                
                self.video.data = chunk_updated + self.video.data[80:]
                self.duration = data['duration']
                runtime = (datetime.datetime.utcnow() - start_download).total_seconds()
                target_diff = 0.3 * self.duration
                wait = target_diff - runtime
                self.check_ts_counter(uri)
                self.logger.info(f"Serving {uri} ({self.duration}s) ({len(self.video.data)}B)")
                self.write_buffer.write(self.video.data)
                if wait > 0:
                    time.sleep(wait)
        self.video.terminate()

    def is_pts_valid(self):
        if not self.config[self.channel_dict['namespace'].lower()]['player-enable_pts_filter']:
            return True
        before = len(self.video.data)
        results = self.pts_validation.check_pts(self.video)
        if results['byteoffset'] != 0:
            return False
        if results['refresh_stream']:
            return False
        if results['reread_buffer']:
            return False
        return True

    def get_ts_counter(self, _uri):
        r = re.compile( r'(\d+)\.ts' )
        m = r.findall(_uri)
        if len(m) == 0:
            return 0
        else:
            return int(m[len(m)-1])

    def check_ts_counter(self, _uri):
        ts_counter = self.get_ts_counter(_uri)
        if ts_counter-1 != self.last_ts_index:
            if self.last_ts_index != -1:
                self.logger.info('TC Counter Discontinuity {} vs {} next uri: {}' \
                    .format(self.last_ts_index, ts_counter, _uri))
        self.last_ts_index = ts_counter


